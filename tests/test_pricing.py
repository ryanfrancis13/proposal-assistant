from decimal import Decimal

from proposal_assistant.pricing import (
    CspsLine,
    MigrationLine,
    Quote,
    SupportLine,
    SupportTier,
    has_hard_violation,
    validate_quote,
)


D = Decimal


def test_migration_price_uses_documented_components():
    quote = Quote(
        migration=MigrationLine(
            server_count=36,
            rehost_servers=30,
            replatform_workloads=6,
        )
    )

    assert quote.migration_subtotal() == D("3119600.00")


def test_24_month_support_gets_five_percent_contractual_discount():
    quote = Quote(support=SupportLine(SupportTier.STANDARD, 30, 24))

    assert quote.support_subtotal() == D("2667600.00")


def test_csps_bundle_discount_is_applied_after_list_price():
    quote = Quote(
        support=SupportLine(SupportTier.STANDARD, 20, 12),
        csps=CspsLine(5, 12, bundled_with_support=True),
    )

    assert quote.csps_subtotal() == D("1512000.00")


def test_rules_report_hard_and_soft_violations():
    quote = validate_quote(
        Quote(
            support=SupportLine(SupportTier.ESSENTIAL, 10, 6),
            negotiated_discount_pct=D("0.08"),
        )
    )

    assert {violation.rule_id for violation in quote.violations} == {"R1", "R2", "R6"}
    assert has_hard_violation(quote)
    assert next(v for v in quote.violations if v.rule_id == "R6").hard is False


def test_bundle_and_csps_term_rules_are_independent():
    quote = validate_quote(
        Quote(
            support=SupportLine(SupportTier.ESSENTIAL, 20, 12),
            csps=CspsLine(2, 6, bundled_with_support=True),
        )
    )

    assert {violation.rule_id for violation in quote.violations} == {"R4", "R7"}


def test_discount_cap_and_price_floor_are_checked():
    quote = validate_quote(
        Quote(
            support=SupportLine(SupportTier.STANDARD, 20, 12),
            csps=CspsLine(10, 12, bundled_with_support=True),
            negotiated_discount_pct=D("0.20"),
        )
    )

    assert "R3" in {violation.rule_id for violation in quote.violations}
    assert "R5" in {violation.rule_id for violation in quote.violations}
