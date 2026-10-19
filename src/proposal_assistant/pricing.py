from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Callable


D = Decimal


class SupportTier(str, Enum):
    ESSENTIAL = "essential"
    STANDARD = "standard"
    PREMIUM = "premium"


RATE_CARD = {
    "discovery_flat": D("420000"),
    "discovery_per_server_above_50": D("6500"),
    "landing_zone_single_cloud": D("650000"),
    "landing_zone_extra_cloud": D("400000"),
    "rehost_per_server": D("38000"),
    "replatform_per_workload": D("115000"),
    "project_management_pct": D("0.12"),
    "support_rate_per_server_month": {
        SupportTier.ESSENTIAL: D("2400"),
        SupportTier.STANDARD: D("3900"),
        SupportTier.PREMIUM: D("6200"),
    },
    "support_min_servers": 20,
    "support_min_term_months": 12,
    "support_24_month_discount_pct": D("0.05"),
    "csps_per_account_month": D("28000"),
    "csps_extra_account_month": D("22000"),
    "csps_bundle_discount_pct": D("0.10"),
    "csps_min_term_months": 12,
}


def money(value: Decimal) -> Decimal:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def format_inr(value: Decimal) -> str:
    """Format a Decimal with Indian lakh/crore digit grouping."""
    amount = money(value)
    whole, fraction = f"{amount:.2f}".split(".")
    sign = ""
    if whole.startswith("-"):
        sign = "-"
        whole = whole[1:]
    if len(whole) <= 3:
        grouped = whole
    else:
        last_three = whole[-3:]
        leading = whole[:-3]
        groups = []
        while leading:
            groups.insert(0, leading[-2:])
            leading = leading[:-2]
        grouped = ",".join(groups + [last_three])
    return f"{sign}{grouped}.{fraction}"


@dataclass(frozen=True)
class MigrationLine:
    server_count: int
    rehost_servers: int = 0
    replatform_workloads: int = 0
    clouds: int = 1


@dataclass(frozen=True)
class SupportLine:
    tier: SupportTier
    server_count: int
    term_months: int


@dataclass(frozen=True)
class CspsLine:
    account_count: int
    term_months: int
    bundled_with_support: bool = False


@dataclass(frozen=True)
class Violation:
    rule_id: str
    hard: bool
    detail: str


@dataclass
class Quote:
    migration: MigrationLine | None = None
    support: SupportLine | None = None
    csps: CspsLine | None = None
    negotiated_discount_pct: Decimal = D("0")
    violations: list[Violation] = field(default_factory=list)

    def migration_subtotal(self) -> Decimal:
        if self.migration is None:
            return D("0")
        line = self.migration
        discovery = RATE_CARD["discovery_flat"] + max(0, line.server_count - 50) * RATE_CARD[
            "discovery_per_server_above_50"
        ]
        landing_zone = RATE_CARD["landing_zone_single_cloud"] + max(
            0, line.clouds - 1
        ) * RATE_CARD["landing_zone_extra_cloud"]
        migration_fees = (
            line.rehost_servers * RATE_CARD["rehost_per_server"]
            + line.replatform_workloads * RATE_CARD["replatform_per_workload"]
        )
        return money(discovery + landing_zone + migration_fees * RATE_CARD["project_management_pct"] + migration_fees)

    def support_list_price(self) -> Decimal:
        if self.support is None:
            return D("0")
        line = self.support
        return money(
            D(line.server_count)
            * RATE_CARD["support_rate_per_server_month"][line.tier]
            * D(line.term_months)
        )

    def support_subtotal(self) -> Decimal:
        total = self.support_list_price()
        if self.support and self.support.term_months >= 24:
            total *= 1 - RATE_CARD["support_24_month_discount_pct"]
        return money(total)

    def csps_list_price(self) -> Decimal:
        if self.csps is None:
            return D("0")
        line = self.csps
        monthly = (
            min(line.account_count, 5) * RATE_CARD["csps_per_account_month"]
            + max(0, line.account_count - 5) * RATE_CARD["csps_extra_account_month"]
        )
        return money(monthly * D(line.term_months))

    def csps_subtotal(self) -> Decimal:
        total = self.csps_list_price()
        if self.csps and self.csps.bundled_with_support:
            total *= 1 - RATE_CARD["csps_bundle_discount_pct"]
        return money(total)

    def list_total(self) -> Decimal:
        return self.migration_subtotal() + self.support_list_price() + self.csps_list_price()

    def subtotal(self) -> Decimal:
        return self.migration_subtotal() + self.support_subtotal() + self.csps_subtotal()

    def negotiated_discount_amount(self) -> Decimal:
        return money(self.subtotal() * self.negotiated_discount_pct)

    def total(self) -> Decimal:
        return money(self.subtotal() - self.negotiated_discount_amount())


def _support_min_servers(quote: Quote) -> tuple[bool, str]:
    if quote.support is None:
        return True, ""
    minimum = RATE_CARD["support_min_servers"]
    return quote.support.server_count >= minimum, f"support covers {quote.support.server_count} servers; minimum is {minimum}"


def _support_min_term(quote: Quote) -> tuple[bool, str]:
    if quote.support is None:
        return True, ""
    minimum = RATE_CARD["support_min_term_months"]
    return quote.support.term_months >= minimum, f"support term is {quote.support.term_months} months; minimum is {minimum}"


def _discount_cap(quote: Quote) -> tuple[bool, str]:
    maximum = D("0.15")
    return quote.negotiated_discount_pct <= maximum, f"negotiated discount {quote.negotiated_discount_pct:.1%} exceeds the 15% cap"


def _bundle_eligibility(quote: Quote) -> tuple[bool, str]:
    if quote.csps is None or not quote.csps.bundled_with_support:
        return True, ""
    eligible = quote.support is not None and quote.support.tier in (
        SupportTier.STANDARD,
        SupportTier.PREMIUM,
    )
    return eligible, "CSPS bundle discount requires Standard or Premium support"


def _price_floor(quote: Quote) -> tuple[bool, str]:
    floor = money(quote.list_total() * D("0.80"))
    return quote.total() >= floor, (
        f"total {format_inr(quote.total())} is below the 80% price floor "
        f"of {format_inr(floor)}"
    )


def _approval_flag(quote: Quote) -> tuple[bool, str]:
    if quote.negotiated_discount_pct <= D("0.05"):
        return True, ""
    return False, f"negotiated discount {quote.negotiated_discount_pct:.1%} requires approval"


def _csps_min_term(quote: Quote) -> tuple[bool, str]:
    if quote.csps is None:
        return True, ""
    minimum = RATE_CARD["csps_min_term_months"]
    return quote.csps.term_months >= minimum, f"CSPS term is {quote.csps.term_months} months; minimum is {minimum}"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    hard: bool
    check: Callable[[Quote], tuple[bool, str]]


RULES = (
    Rule("R1", True, _support_min_servers),
    Rule("R2", True, _support_min_term),
    Rule("R3", True, _discount_cap),
    Rule("R4", True, _bundle_eligibility),
    Rule("R5", True, _price_floor),
    Rule("R6", False, _approval_flag),
    Rule("R7", True, _csps_min_term),
)


def validate_quote(quote: Quote) -> Quote:
    quote.violations = []
    for rule in RULES:
        passed, detail = rule.check(quote)
        if not passed:
            quote.violations.append(Violation(rule.rule_id, rule.hard, detail))
    return quote


def has_hard_violation(quote: Quote) -> bool:
    return any(violation.hard for violation in quote.violations)
