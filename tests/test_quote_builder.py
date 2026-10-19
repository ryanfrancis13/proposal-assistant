from decimal import Decimal

from proposal_assistant.models import QuoteInputs
from proposal_assistant.quote_builder import build_quote
from proposal_assistant.pricing import SupportTier


def test_builder_exposes_defaults_as_assumptions():
    quote, assumptions = build_quote(
        QuoteInputs(server_count=40, support_requested=True)
    )

    assert quote.migration is not None
    assert quote.migration.rehost_servers == 40
    assert quote.support is not None
    assert quote.support.tier is SupportTier.STANDARD
    assert quote.support.term_months == 12
    assert any("split not stated" in item for item in assumptions)
    assert any("Support term not stated" in item for item in assumptions)
    assert any("Support tier not stated" in item for item in assumptions)


def test_builder_keeps_explicit_values_and_discount():
    quote, assumptions = build_quote(
        QuoteInputs(
            server_count=35,
            rehost_servers=20,
            replatform_workloads=15,
            cloud_count=2,
            support_requested=True,
            support_term_months=24,
            negotiated_discount_pct=0.08,
        )
    )

    assert quote.migration.rehost_servers == 20
    assert quote.migration.replatform_workloads == 15
    assert quote.migration.clouds == 2
    assert quote.support.term_months == 24
    assert quote.negotiated_discount_pct == Decimal("0.08")
    assert "Support tier not stated; estimated Standard support." in assumptions


def test_builder_does_not_create_services_not_requested():
    quote, assumptions = build_quote(QuoteInputs())

    assert quote.migration is None
    assert quote.support is None
    assert quote.csps is None
    assert quote.total() == Decimal("0.00")
    assert assumptions == []
