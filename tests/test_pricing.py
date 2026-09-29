import pytest

from proposal_assistant.pricing import (
    CspsLine,
    MigrationLine,
    Quote,
    SupportLine,
    SupportTier,
    has_hard_violation,
    validate,
)


def test_migration_subtotal_basic():
    q = Quote(migration=MigrationLine(server_count=40, rehost_servers=30, replatform_workloads=6, clouds=1))
    # discovery flat (under 50) + landing zone single cloud + rehost + replatform + 12% pm
    expected_discovery = 420_000
    expected_landing_zone = 650_000
    expected_rehost = 30 * 38_000
    expected_replatform = 6 * 115_000
    expected_fees = expected_rehost + expected_replatform
    expected_pm = expected_fees * 0.12
    expected = expected_discovery + expected_landing_zone + expected_fees + expected_pm

    assert q.migration_subtotal() == pytest.approx(expected)


def test_migration_discovery_scales_above_50_servers():
    q = Quote(migration=MigrationLine(server_count=60, rehost_servers=60, replatform_workloads=0, clouds=1))
    expected_discovery = 420_000 + 10 * 6_500
    assert q.migration_subtotal() >= expected_discovery  # sanity: discovery portion scaled up


def test_multi_cloud_adds_landing_zone_fee():
    single = Quote(migration=MigrationLine(server_count=20, rehost_servers=20, clouds=1))
    multi = Quote(migration=MigrationLine(server_count=20, rehost_servers=20, clouds=2))
    assert multi.migration_subtotal() == pytest.approx(single.migration_subtotal() + 400_000)


def test_support_24_month_discount_applied():
    q12 = Quote(support=SupportLine(tier=SupportTier.STANDARD, server_count=30, term_months=12))
    q24 = Quote(support=SupportLine(tier=SupportTier.STANDARD, server_count=30, term_months=24))
    monthly = 30 * 3_900
    assert q12.support_subtotal() == pytest.approx(monthly * 12)
    assert q24.support_subtotal() == pytest.approx(monthly * 0.95 * 24)


def test_r1_violated_below_minimum_servers():
    q = validate(Quote(support=SupportLine(tier=SupportTier.ESSENTIAL, server_count=10, term_months=12)))
    ids = [v[0] for v in q.violations]
    assert "R1" in ids
    assert has_hard_violation(q)


def test_r2_violated_below_minimum_term():
    q = validate(Quote(support=SupportLine(tier=SupportTier.ESSENTIAL, server_count=25, term_months=6)))
    ids = [v[0] for v in q.violations]
    assert "R2" in ids
    assert has_hard_violation(q)


def test_r4_violated_bundle_discount_on_essential_tier():
    q = validate(
        Quote(
            support=SupportLine(tier=SupportTier.ESSENTIAL, server_count=25, term_months=12),
            csps=CspsLine(account_count=3, term_months=12, bundled_with_support=True),
        )
    )
    ids = [v[0] for v in q.violations]
    assert "R4" in ids
    assert has_hard_violation(q)


def test_compliant_quote_has_no_violations():
    q = validate(
        Quote(
            migration=MigrationLine(server_count=42, rehost_servers=36, replatform_workloads=6, clouds=1),
            support=SupportLine(tier=SupportTier.STANDARD, server_count=36, term_months=24),
        )
    )
    assert q.violations == []
    assert not has_hard_violation(q)


def test_csps_extra_accounts_beyond_five():
    q = Quote(csps=CspsLine(account_count=7, term_months=12, bundled_with_support=False))
    expected_monthly = 5 * 28_000 + 2 * 22_000
    assert q.csps_subtotal() == pytest.approx(expected_monthly * 12)