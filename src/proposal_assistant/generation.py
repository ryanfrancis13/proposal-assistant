import json
from dataclasses import dataclass
from typing import Protocol

from proposal_assistant.models import (
    Claim,
    Evidence,
    ProposalSection,
    Requirement,
    SectionStatus,
)


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str:
        """Return one model response for a prompt."""


@dataclass
class CountingGenerator:
    """Deterministic test double that returns queued JSON responses."""

    responses: list[str]
    calls: int = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("fake generator has no response remaining")
        return self.responses.pop(0)


def _evidence_prompt(evidence: list[Evidence]) -> str:
    return "\n\n".join(
        f"[{item.evidence_id}] {item.source_file} > {item.section}\n{item.text}"
        for item in evidence
    )


def _parse_section(raw: str, requirement_id: str, valid_evidence_ids: set[str]) -> ProposalSection:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("model response was not valid JSON") from exc

    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    try:
        status = SectionStatus(value["status"])
        raw_claims = value["claims"]
        gaps = value["gaps"]
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("section JSON has an invalid status, claims, or gaps field") from exc
    if not isinstance(raw_claims, list) or not isinstance(gaps, list):
        raise ValueError("claims and gaps must be arrays")

    claims: list[Claim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict) or not isinstance(raw_claim.get("text"), str):
            raise ValueError("each claim must contain text")
        cited = raw_claim.get("evidence", [])
        if not isinstance(cited, list) or not all(
            isinstance(item, str) and item in valid_evidence_ids for item in cited
        ):
            raise ValueError("claim cites evidence that was not supplied")
        claims.append(Claim(raw_claim["text"], tuple(cited)))

    if not all(isinstance(gap, str) for gap in gaps):
        raise ValueError("gaps must contain strings")
    return ProposalSection(
        requirement_id=requirement_id,
        status=status,
        claims=claims,
        gaps=gaps,
    )


def draft_section(
    requirement: Requirement,
    evidence: list[Evidence],
    generator: TextGenerator,
    repair_feedback: list[str] | None = None,
) -> ProposalSection:
    feedback = ""
    if repair_feedback:
        feedback = (
            "\nThe previous section failed these deterministic checks. "
            "Repair only these problems:\n"
            + "\n".join(f"- {item}" for item in repair_feedback)
            + "\n"
        )
    prompt = f"""Draft one proposal section for Meridian Cloudworks.

Requirement: {requirement.detail}

Use only the evidence below. Every claim must cite one or more evidence IDs.
Do not invent prices, dates, capabilities, certifications, or guarantees.
Return only JSON with status, claims, and gaps. Status must be one of:
answered, partial, cannot_fulfil, no_evidence.

Evidence:
{_evidence_prompt(evidence)}
{feedback}
"""
    raw = generator.generate(prompt)
    return _parse_section(
        raw,
        requirement_id=requirement.requirement_id,
        valid_evidence_ids={item.evidence_id for item in evidence},
    )
