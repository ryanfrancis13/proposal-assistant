import re

from proposal_assistant.models import QuoteInputs, Requirement


def _first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _first_percent(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return float(match.group(1)) / 100 if match else None


def extract_quote_inputs(rfp_text: str) -> QuoteInputs:
    """Extract only facts stated in an RFP; absent facts remain None."""
    provider = None
    provider_match = re.search(
        r"\b(AWS|Azure|Microsoft Azure|Google Cloud Platform|GCP)\b",
        rfp_text,
        flags=re.IGNORECASE,
    )
    if provider_match:
        provider = provider_match.group(1)

    cloud_count = 2 if re.search(r"\bmulti[- ]cloud\b", rfp_text, re.I) else None
    if provider:
        cloud_count = 1

    support_requested = None
    if re.search(
        r"\b(ongoing|managed)\s+support\b|\bsupport options?\b"
        r"|\b24/7(?:/365)?\b|\b24x7\b|\brecurring monthly management\b|\bpatch management\b",
        rfp_text,
        re.I,
    ):
        support_requested = True

    return QuoteInputs(
        server_count=_first_int(
            r"(?:about|approximately|around|move|have|with)?\s*(\d+)\s+(?:[\w-]+\s+){0,6}servers?",
            rfp_text,
        ),
        cloud_provider=provider,
        cloud_count=cloud_count,
        support_requested=support_requested,
        support_term_months=_first_int(r"(\d+)[- ]month\s+(?:support\s+)?term", rfp_text),
        negotiated_discount_pct=_first_percent(
            r"(?:(?:at least|minimum of)\s+)?(?:a\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent)\s*discount",
            rfp_text,
        ),
        csps_accounts=_first_int(
            r"(\d+)\s+(?:csps|cloud)\s+accounts?",
            rfp_text,
        ),
    )


def extract_requirements(rfp_text: str) -> list[Requirement]:
    """Create traceable requirement entries from sentences in an RFP."""
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", rfp_text.strip())
        if sentence.strip()
    ]
    return [
        Requirement(
            requirement_id=f"REQ-{index:03d}",
            topic=_topic_for(sentence),
            detail=sentence,
        )
        for index, sentence in enumerate(sentences, start=1)
    ]


def _topic_for(sentence: str) -> str:
    lowered = sentence.lower()
    if (
        "deadline" in lowered
        or "within" in lowered
        or (re.search(r"\b(?:months?|weeks?)\b", lowered) and "term" not in lowered)
    ):
        return "timeline"
    if "security" in lowered or "compliance" in lowered or "hipaa" in lowered or "iso 27001" in lowered or "soc 2" in lowered:
        return "security and compliance"
    if (
        "discount" in lowered
        or "budget" in lowered
        or "pricing" in lowered
        or "cost" in lowered
        or "fee" in lowered
    ):
        return "commercials"
    if (
        "support" in lowered
        or "monitoring" in lowered
        or "patch" in lowered
        or "disaster recovery" in lowered
        or "uptime" in lowered
        or "sla" in lowered
    ):
        return "managed support"
    if "cloud" in lowered or "sap" in lowered:
        return "platform"
    if "server" in lowered or "infrastructure" in lowered:
        return "estate size"
    return "general requirement"
