from decimal import Decimal

from proposal_assistant.models import QuoteInputs
from proposal_assistant.pricing import (
    CspsLine,
    MigrationLine,
    Quote,
    SupportLine,
    SupportTier,
    validate_quote,
)


def _decimal_percentage(value: float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def build_quote(inputs: QuoteInputs) -> tuple[Quote, list[str]]:
    """Build and validate a quote, returning every applied assumption."""
    assumptions: list[str] = []

    migration = None
    if inputs.server_count is not None:
        rehost_servers = inputs.rehost_servers
        replatform_workloads = inputs.replatform_workloads
        if rehost_servers is None and replatform_workloads is None:
            rehost_servers = inputs.server_count
            replatform_workloads = 0
            assumptions.append(
                f"Migration split not stated; estimated all {inputs.server_count} "
                "items as rehost servers."
            )
        else:
            rehost_servers = rehost_servers or 0
            replatform_workloads = replatform_workloads or 0

        clouds = inputs.cloud_count
        if clouds is None:
            clouds = 1
            assumptions.append("Cloud count not stated; estimated one cloud.")

        migration = MigrationLine(
            server_count=inputs.server_count,
            rehost_servers=rehost_servers,
            replatform_workloads=replatform_workloads,
            clouds=clouds,
        )

    support = None
    if inputs.support_requested is True:
        term_months = inputs.support_term_months
        if term_months is None:
            term_months = 12
            assumptions.append("Support term not stated; estimated the 12-month minimum.")
        support = SupportLine(
            tier=SupportTier.STANDARD,
            server_count=inputs.server_count or 0,
            term_months=term_months,
        )
        assumptions.append("Support tier not stated; estimated Standard support.")

    csps = None
    if inputs.csps_accounts is not None:
        term_months = inputs.support_term_months or 12
        if inputs.support_term_months is None:
            assumptions.append("CSPS term not stated; estimated the 12-month minimum.")
        csps = CspsLine(
            account_count=inputs.csps_accounts,
            term_months=term_months,
            bundled_with_support=support is not None,
        )

    quote = Quote(
        migration=migration,
        support=support,
        csps=csps,
        negotiated_discount_pct=_decimal_percentage(inputs.negotiated_discount_pct),
    )
    return validate_quote(quote), assumptions
