import re

from proposal_assistant.models import (
    ProposalSection,
    SectionVerification,
    VerificationContext,
    VerificationIssue,
)


_MONEY_PATTERN = re.compile(
    r"(?:INR|Rs\.?|₹)\s*[\d,]+(?:\.\d{1,2})?",
    flags=re.IGNORECASE,
)
_FORBIDDEN_CAPABILITIES = {
    "gcp": "GCP",
    "google cloud": "Google Cloud",
    "sap hana": "SAP HANA",
    "mainframe": "mainframe",
    "hipaa": "HIPAA mappings",
}
_GUARANTEE_WORDS = ("guarantee", "guaranteed", "will achieve", "will reduce")


def _issue(check_id: str, detail: str) -> VerificationIssue:
    return VerificationIssue(check_id=check_id, detail=detail)


def verify_section(
    section: ProposalSection,
    context: VerificationContext,
) -> SectionVerification:
    issues: list[VerificationIssue] = []
    evidence_by_id = {item.evidence_id: item for item in context.evidence}
    valid_amounts = {amount.replace(",", "") for amount in context.allowed_amounts}

    for claim in section.claims:
        for evidence_id in claim.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                issues.append(_issue("V1", f"unknown evidence citation: {evidence_id}"))
            elif evidence.status != "current":
                issues.append(
                    _issue(
                        "V1",
                        f"claim cites non-current source {evidence.source_file}",
                    )
                )

        lowered = claim.text.lower()
        for phrase, label in _FORBIDDEN_CAPABILITIES.items():
            if phrase in lowered and not any(
                marker in lowered for marker in ("not", "do not", "doesn't", "cannot")
            ):
                issues.append(
                    _issue("V2", f"claim presents unsupported capability: {label}")
                )
        if any(word in lowered for word in _GUARANTEE_WORDS):
            issues.append(_issue("V3", "claim uses guarantee or target language"))

        for amount in _MONEY_PATTERN.findall(claim.text):
            normalized = re.sub(r"[^\d.]", "", amount)
            if normalized not in valid_amounts:
                issues.append(_issue("V4", f"unapproved currency amount: {amount}"))

        if (
            context.deadline_weeks is not None
            and context.minimum_documented_weeks is not None
            and context.deadline_weeks < context.minimum_documented_weeks
            and any(
                phrase in lowered
                for phrase in ("can complete", "will complete", "meet the deadline", "achievable")
            )
        ):
            issues.append(
                _issue(
                    "V7",
                    "claim presents a deadline as achievable below the documented minimum timeline",
                )
            )

    for gap in section.gaps:
        if not gap.startswith("Not covered in our documents:"):
            issues.append(_issue("V5", "gap does not use the required wording"))

    if section.status.value == "answered" and section.gaps:
        issues.append(_issue("V6", "answered section cannot contain gaps"))
    if section.status.value == "no_evidence" and section.claims:
        issues.append(_issue("V6", "no_evidence section cannot contain claims"))

    return SectionVerification(
        requirement_id=section.requirement_id,
        passed=not issues,
        issues=issues,
    )
