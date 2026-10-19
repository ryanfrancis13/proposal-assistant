from decimal import Decimal

from proposal_assistant.pricing import format_inr


def test_format_inr_uses_lakh_and_crore_grouping():
    assert format_inr(Decimal("3119600")) == "31,19,600.00"
    assert format_inr(Decimal("123456789.5")) == "12,34,56,789.50"


def test_format_inr_handles_small_and_negative_values():
    assert format_inr(Decimal("420000")) == "4,20,000.00"
    assert format_inr(Decimal("-1234.5")) == "-1,234.50"
