import json
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from proposal_assistant.config import generator_api_key, nim_base_url
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
class NIMGenerator:
    """OpenAI-compatible client for a configured NVIDIA NIM generator."""

    model: str
    timeout: float = 60.0
    calls: int = 0

    def __post_init__(self) -> None:
        self._client = OpenAI(
            api_key=generator_api_key(),
            base_url=nim_base_url(),
            timeout=self.timeout,
        )

    def generate(self, prompt: str) -> str:
        self.calls += 1
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("NVIDIA NIM returned an empty generation")
        return content


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
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        value = _extract_json_object(raw)

    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    if "status" not in value and "text" in value and (
        "evidence" in value or "citations" in value
    ):
        value = {
            "status": "answered",
            "claims": [
                {
                    "text": value["text"],
                    "evidence": value.get("evidence", value.get("citations", [])),
                }
            ],
            "gaps": [],
        }
    try:
        status = SectionStatus(value["status"])
        raw_claims = value["claims"]
        gaps = value["gaps"]
    except (KeyError, ValueError, TypeError) as exc:
        keys = ", ".join(sorted(str(key) for key in value))
        raise ValueError(
            f"section JSON has invalid fields; expected status, claims, gaps; "
            f"received keys: [{keys}]"
        ) from exc
    if not isinstance(raw_claims, list) or not isinstance(gaps, list):
        raise ValueError("claims and gaps must be arrays")

    claims: list[Claim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            raise ValueError("each claim must be an object with text and evidence")
        claim_text = raw_claim.get("text", raw_claim.get("claim"))
        if not isinstance(claim_text, str) or not claim_text.strip():
            preview = " ".join(str(raw_claim).split())[:160]
            raise ValueError(f"each claim must contain non-empty text: {preview}")
        cited = raw_claim.get("evidence", raw_claim.get("citations", []))
        if not isinstance(cited, list) or not all(
            isinstance(item, str) and item in valid_evidence_ids for item in cited
        ):
            raise ValueError("claim cites evidence that was not supplied")
        claims.append(Claim(claim_text, tuple(cited)))

    if not all(isinstance(gap, str) for gap in gaps):
        raise ValueError("gaps must contain strings")
    return ProposalSection(
        requirement_id=requirement_id,
        status=status,
        claims=claims,
        gaps=gaps,
    )


def _extract_json_object(raw: str) -> dict:
    """Extract one JSON object from a fenced or prose-wrapped model response."""
    decoder = json.JSONDecoder()
    for start, character in enumerate(raw):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    preview = " ".join(raw.strip().split())[:200]
    raise ValueError(f"model response contained no JSON object: {preview!r}")


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
Return only this JSON shape, with no Markdown or commentary:
{{"status":"answered|partial|cannot_fulfil|no_evidence",
  "claims":[{{"text":"one sentence","evidence":["E1"]}}],
  "gaps":["Not covered in our documents: ..."]}}
Every claim object must have non-empty text and an evidence array.

Evidence:
{_evidence_prompt(evidence)}
{feedback}
"""
    valid_evidence_ids = {item.evidence_id for item in evidence}
    raw = generator.generate(prompt)
    try:
        return _parse_section(
            raw,
            requirement_id=requirement.requirement_id,
            valid_evidence_ids=valid_evidence_ids,
        )
    except ValueError as first_error:
        if "evidence" in str(first_error).lower():
            raise
        repair_prompt = f"""Your previous response did not match the required JSON schema.
Return ONLY one JSON object with exactly these top-level keys:
status, claims, gaps.
Each claims item must be {{"text":"...", "evidence":["E1"]}}.
Use only these evidence IDs: {sorted(valid_evidence_ids)}.
Do not add commentary or Markdown.

Previous response:
{raw[:2000]}

Original drafting instruction:
{prompt}
"""
        repaired_raw = generator.generate(repair_prompt)
        try:
            return _parse_section(
                repaired_raw,
                requirement_id=requirement.requirement_id,
                valid_evidence_ids=valid_evidence_ids,
            )
        except ValueError as second_error:
            raise ValueError(
                f"model failed section schema after one retry; "
                f"first error: {first_error}; second error: {second_error}"
            ) from second_error
