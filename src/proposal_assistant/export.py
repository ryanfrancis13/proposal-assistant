from pathlib import Path

from docx import Document

from proposal_assistant.models import ProposalDraft
from proposal_assistant.pricing import Quote, format_inr


def _quote_lines(quote: Quote) -> list[str]:
    return [
        f"Migration subtotal: INR {format_inr(quote.migration_subtotal())}",
        f"Managed support subtotal: INR {format_inr(quote.support_subtotal())}",
        f"CSPS subtotal: INR {format_inr(quote.csps_subtotal())}",
        f"Subtotal after contractual discounts: INR {format_inr(quote.subtotal())}",
        f"Negotiated discount: INR {format_inr(quote.negotiated_discount_amount())}",
        f"Total: INR {format_inr(quote.total())}",
    ]


def export_docx(
    path: Path,
    draft: ProposalDraft,
    quote: Quote,
    assumptions: list[str] | None = None,
) -> Path:
    document = Document()
    document.add_heading("Meridian Cloudworks Proposal", level=0)
    document.add_heading("Pricing", level=1)
    for line in _quote_lines(quote):
        document.add_paragraph(line)

    if assumptions:
        document.add_heading("Assumptions", level=1)
        for assumption in assumptions:
            document.add_paragraph(assumption, style="List Bullet")

    document.add_heading("Requirements and proposed response", level=1)
    for section in draft.sections:
        document.add_heading(section.requirement_id, level=2)
        document.add_paragraph(f"Status: {section.status.value}")
        for claim in section.claims:
            citations = ", ".join(claim.evidence_ids) or "no citation"
            document.add_paragraph(f"{claim.text} [{citations}]")
        for gap in section.gaps:
            document.add_paragraph(f"Gap: {gap}", style="List Bullet")

    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    return path
