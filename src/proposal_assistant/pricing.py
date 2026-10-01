from dataclasses import dataclass, field
from enum import Enum


class SupportTier(str, Enum):
    ESSENTIAL = "essential"
    STANDARD = "standard"
    PREMIUM = "premium"


RATE_CARD = {
    "discovery_flat": 420_000,          # up to 50 servers
    "discovery_per_server_above_50": 6_500,
    "landing_zone_single_cloud": 650_000,
    "landing_zone_extra_cloud": 400_000,
    "rehost_per_server": 38_000,
    "replatform_per_workload": 115_000,
    "project_mgmt_pct": 0.12,
    "support_rate_per_server_month": {
        SupportTier.ESSENTIAL: 2_400,
        SupportTier.STANDARD: 3_900,
        SupportTier.PREMIUM: 6_200,
    },
    "support_min_servers": 20,
    "support_min_term_months": 12,
    "support_term_discount_months": 24,
    "support_term_discount_pct": 0.05,
    "csps_per_account_month": 28_000,
    "csps_extra_account_month": 22_000,  # beyond 5 accounts
    "csps_bundle_discount_pct": 0.10,
    "csps_min_term_months": 12,
}


@dataclass
class MigrationLine:
    server_count: int = 0
    rehost_servers: int = 0
    replatform_workloads: int = 0
    clouds: int = 1  # 1 = single cloud, 2 = multi-cloud


@dataclass
class SupportLine:
    tier: SupportTier
    server_count: int
    term_months: int


@dataclass
class CspsLine:
    account_count: int
    term_months: int
    bundled_with_support: bool  # True only if support tier is Standard or Premium


@dataclass
class Quote:
    migration: MigrationLine | None = None
    support: SupportLine | None = None
    csps: CspsLine | None = None
    violations: list[tuple[str, bool, str]] = field(default_factory=list)

    def migration_subtotal(self) -> float:
        if not self.migration:
            return 0.0
        m = self.migration
        rc = RATE_CARD

        discovery = rc["discovery_flat"]
        if m.server_count > 50:
            discovery += (m.server_count - 50) * rc["discovery_per_server_above_50"]

        landing_zone = rc["landing_zone_single_cloud"]
        if m.clouds > 1:
            landing_zone += (m.clouds - 1) * rc["landing_zone_extra_cloud"]

        rehost = m.rehost_servers * rc["rehost_per_server"]
        replatform = m.replatform_workloads * rc["replatform_per_workload"]

        migration_fees = rehost + replatform
        project_mgmt = migration_fees * rc["project_mgmt_pct"]

        return discovery + landing_zone + migration_fees + project_mgmt

    def support_subtotal(self) -> float:
        if not self.support:
            return 0.0
        s = self.support
        rc = RATE_CARD
        monthly = s.server_count * rc["support_rate_per_server_month"][s.tier]

        if s.term_months >= rc["support_term_discount_months"]:
            monthly *= 1 - rc["support_term_discount_pct"]

        return monthly * s.term_months

    def csps_subtotal(self) -> float:
        if not self.csps:
            return 0.0
        c = self.csps
        rc = RATE_CARD

        monthly = min(c.account_count, 5) * rc["csps_per_account_month"]
        if c.account_count > 5:
            monthly += (c.account_count - 5) * rc["csps_extra_account_month"]

        if c.bundled_with_support:
            monthly *= 1 - rc["csps_bundle_discount_pct"]

        return monthly * c.term_months

    def subtotal(self) -> float:
        return self.migration_subtotal() + self.support_subtotal() + self.csps_subtotal()

    def undiscounted_subtotal(self) -> float:
        """Same as subtotal() but with term/bundle discounts stripped out,
        used only to check the R5 floor-margin rule."""
        total = self.migration_subtotal()

        if self.support:
            s = self.support
            total += s.server_count * RATE_CARD["support_rate_per_server_month"][s.tier] * s.term_months

        if self.csps:
            c = self.csps
            monthly = min(c.account_count, 5) * RATE_CARD["csps_per_account_month"]
            if c.account_count > 5:
                monthly += (c.account_count - 5) * RATE_CARD["csps_extra_account_month"]
            total += monthly * c.term_months

        return total


Rule = tuple[str, bool, callable]

RULES: list[tuple[str, bool, callable]] = [
    (
        "R1",
        True,
        lambda q: (
            q.support is None or q.support.server_count >= RATE_CARD["support_min_servers"],
            f"support server_count={q.support.server_count if q.support else 'n/a'}",
        ),
    ),
    (
        "R2",
        True,
        lambda q: (
            q.support is None or q.support.term_months >= RATE_CARD["support_min_term_months"],
            f"support term_months={q.support.term_months if q.support else 'n/a'}",
        ),
    ),
    (
        "R4",
        True,
        lambda q: (
            q.csps is None
            or not q.csps.bundled_with_support
            or (q.support is not None and q.support.tier in (SupportTier.STANDARD, SupportTier.PREMIUM)),
            "csps bundle discount claimed without Standard/Premium support",
        ),
    ),
    (
        "R5",
        False,
        lambda q: (
            q.undiscounted_subtotal() == 0 or q.subtotal() >= 0.70 * q.undiscounted_subtotal(),
            f"total={q.subtotal():.2f} vs floor={0.70 * q.undiscounted_subtotal():.2f}",
        ),
    ),
]


def validate(quote: Quote) -> Quote:
    quote.violations = []
    for rule_id, is_hard, check in RULES:
        ok, detail = check(quote)
        if not ok:
            quote.violations.append((rule_id, is_hard, detail))
    return quote


def has_hard_violation(quote: Quote) -> bool:
    return any(is_hard for _, is_hard, _ in quote.violations)


from proposal_assistant.pricing import MigrationLine, Quote, SupportLine, SupportTier, validate


def build_quote_from_inputs(inputs: dict) -> tuple[Quote, list[str]]:
    assumptions = []

    server_count = inputs.get("server_count") or 0
    rehost = inputs.get("rehost_servers")
    replatform = inputs.get("replatform_workloads")

    if rehost is None and replatform is None and server_count:
        rehost = server_count
        replatform = 0
        assumptions.append(
            f"Rehost/replatform split not specified; assumed all {server_count} "
            f"servers as rehost for this estimate."
        )
    else:
        rehost = rehost or 0
        replatform = replatform or 0

    clouds = inputs.get("clouds") or 1
    if inputs.get("clouds") is None:
        assumptions.append("Cloud count not specified; assumed single cloud.")

    migration = MigrationLine(
        server_count=server_count,
        rehost_servers=rehost,
        replatform_workloads=replatform,
        clouds=clouds,
    ) if server_count else None

    support = None
    if inputs.get("wants_support"):
        term = inputs.get("support_term_months") or 12
        if inputs.get("support_term_months") is None:
            assumptions.append("Support term not specified; assumed 12-month minimum term.")
        support = SupportLine(
            tier=SupportTier.STANDARD,
            server_count=server_count,
            term_months=term,
        )
        assumptions.append("Support tier not specified; assumed Standard tier for this estimate.")

    quote = Quote(migration=migration, support=support)
    validate(quote)
    return quote, assumptions