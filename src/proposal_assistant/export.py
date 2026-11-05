from pathlib import Path

from docx import Document

from proposal_assistant.models import ProposalDraft, Requirement
from proposal_assistant.pricing import Quote, format_inr


_STATUS_TEXT = {
    "answered": "Fully Supported",
    "partial": "Partially Supported",
    "cannot_fulfil": "Outside Current Scope",
    "no_evidence": "Requires Custom Scoping",
}

_TOPIC_TEXT = {
    "estate size": "Infrastructure Scope",
    "timeline": "Delivery Timeline",
    "managed support": "Managed Support & SLAs",
    "security and compliance": "Security & Compliance",
    "commercials": "Commercials & Pricing",
    "platform": "Target Cloud Platform",
    "general requirement": "General Requirement",
}


def _quote_lines(quote: Quote) -> list[str]:
    return [
        f"Migration subtotal: INR {format_inr(quote.migration_subtotal())}",
        f"Managed support subtotal: INR {format_inr(quote.support_subtotal())}",
        f"CSPS subtotal: INR {format_inr(quote.csps_subtotal())}",
        f"Subtotal after contractual discounts: INR {format_inr(quote.subtotal())}",
        f"Negotiated discount: INR {format_inr(quote.negotiated_discount_amount())}",
        f"Total (excluding GST): INR {format_inr(quote.total())}",
    ]


def export_docx(
    path: Path,
    draft: ProposalDraft,
    quote: Quote,
    assumptions: list[str] | None = None,
    requirements: list[Requirement] | None = None,
) -> Path:
    req_by_id = {req.requirement_id: req for req in (requirements or [])}
    document = Document()
    document.add_heading("Meridian Cloudworks — Commercial & Technical Proposal", level=0)
    document.add_heading("Commercial Quote Summary", level=1)
    for line in _quote_lines(quote):
        document.add_paragraph(line)

    if assumptions:
        document.add_heading("Assumptions & Policy Notes", level=1)
        for assumption in assumptions:
            document.add_paragraph(assumption, style="List Bullet")

    document.add_heading("Requirement-by-Requirement Response", level=1)
    for index, section in enumerate(draft.sections, start=1):
        req = req_by_id.get(section.requirement_id)
        if req:
            topic_label = _TOPIC_TEXT.get(req.topic, req.topic.title())
            heading = f"Requirement {index}: {topic_label}"
        else:
            heading = section.requirement_id
        document.add_heading(heading, level=2)
        if req:
            req_para = document.add_paragraph()
            run = req_para.add_run(f"Customer Requirement: \"{req.detail}\"")
            run.italic = True
        status_label = _STATUS_TEXT.get(section.status.value, section.status.value)
        document.add_paragraph(f"Compliance Status: {status_label}")
        for claim in section.claims:
            citations = ", ".join(claim.evidence_ids) or "no citation"
            document.add_paragraph(f"{claim.text} [{citations}]")
        for gap in section.gaps:
            document.add_paragraph(gap, style="List Bullet")

    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    return path
