from dataclasses import dataclass, replace
from pathlib import Path
import re

from proposal_assistant.config import Settings, load_settings
from proposal_assistant.extraction import extract_quote_inputs, extract_requirements
from proposal_assistant.models import (
    Evidence,
    ProposalDraft,
    QuoteInputs,
    RepairCondition,
    Requirement,
    SectionVerification,
    VerificationContext,
)
from proposal_assistant.quote_builder import build_quote
from proposal_assistant.repair import RepairResult, run_repair
from proposal_assistant.retrieval import EvidenceRetriever
from proposal_assistant.pricing import Quote, format_inr, has_hard_violation


@dataclass
class PipelineResult:
    rfp_text: str
    requirements: list[Requirement]
    quote_inputs: QuoteInputs
    quote: Quote
    assumptions: list[str]
    evidence_by_requirement: dict[str, list[Evidence]]
    repair: RepairResult


def _deadline_weeks(rfp_text: str) -> int | None:
    match = re.search(r"(?:within|in)\s+(\d+)\s+months?", rfp_text, re.IGNORECASE)
    return int(match.group(1)) * 4 if match else None


def _minimum_timeline_weeks(server_count: int | None) -> int | None:
    if server_count is None:
        return None
    if server_count <= 40:
        return 12
    if server_count <= 150:
        return 24
    return None


def _quote_amounts(quote: Quote) -> tuple[str, ...]:
    amounts = [
        quote.migration_subtotal(),
        quote.support_subtotal(),
        quote.csps_subtotal(),
        quote.subtotal(),
    ]
    if not has_hard_violation(quote):
        amounts.extend(
            [
                quote.negotiated_discount_amount(),
                quote.total(),
            ]
        )
    return tuple(f"INR {format_inr(amount)}" for amount in amounts)


def build_contexts(
    requirements: list[Requirement],
    evidence_by_requirement: dict[str, list[Evidence]],
    quote: Quote,
    rfp_text: str,
    quote_inputs: QuoteInputs,
) -> dict[str, VerificationContext]:
    context = VerificationContext(
        allowed_amounts=_quote_amounts(quote),
        deadline_weeks=_deadline_weeks(rfp_text),
        minimum_documented_weeks=_minimum_timeline_weeks(quote_inputs.server_count),
    )
    return {
        requirement.requirement_id: VerificationContext(
            evidence=tuple(evidence_by_requirement.get(requirement.requirement_id, [])),
            allowed_amounts=context.allowed_amounts,
            documented_terms=context.documented_terms,
            deadline_weeks=context.deadline_weeks,
            minimum_documented_weeks=context.minimum_documented_weeks,
        )
        for requirement in requirements
    }


def _Expanded_query(requirement: Requirement) -> str:
    lowered = requirement.detail.lower()
    extras: list[str] = [requirement.topic, requirement.detail]
    if any(
        w in lowered
        for w in ("pricing", "cost", "fee", "rate", "upfront", "monthly", "discount")
    ):
        extras.append(
            "Standard rate card Discovery Landing Zone Rehost Replatform Support tiers Price INR Negotiated discount approval cap"
        )
    if any(w in lowered for w in ("security", "compliance", "certification", "audit")):
        extras.append(
            "Security and compliance ISO 27001 SOC 2 CIS Foundations Certifications and audit"
        )
    if any(w in lowered for w in ("uptime", "sla", "downtime", "methodology", "24/7", "disaster")):
        extras.append(
            "Phases and timeline Guarantees and service levels Availability commitment Support tiers"
        )
    return " ".join(extras)


def run_pipeline(
    rfp_text: str,
    generator,
    raw_dir: Path,
    settings: Settings | None = None,
    condition: RepairCondition = RepairCondition.TARGETED_SECTION,
) -> PipelineResult:
    settings = settings or load_settings()
    requirements = extract_requirements(rfp_text)
    quote_inputs = extract_quote_inputs(rfp_text)
    effective_inputs = quote_inputs
    extra_assumptions: list[str] = []
    if (
        quote_inputs.server_count is None
        and (
            quote_inputs.support_requested
            or re.search(r"\bmigrat(?:e|ion)\b|\binfrastructure\b", rfp_text, re.I)
        )
    ):
        effective_inputs = replace(quote_inputs, server_count=20)
        extra_assumptions.append(
            "Server count not stated in RFP; priced an illustrative 20-server baseline estate (minimum managed support subscription)."
        )
    quote, assumptions = build_quote(effective_inputs)
    assumptions = extra_assumptions + assumptions
    for violation in quote.violations:
        kind = "Policy violation" if violation.hard else "Approval note"
        assumptions.append(f"{kind} ({violation.rule_id}): {violation.detail}")
    retriever = EvidenceRetriever(raw_dir, settings.chunk_size)
    evidence_by_requirement = {
        requirement.requirement_id: retriever.search(
            _Expanded_query(requirement),
            top_k=settings.top_k,
        )
        for requirement in requirements
    }
    contexts = build_contexts(
        requirements,
        evidence_by_requirement,
        quote,
        rfp_text,
        quote_inputs,
    )
    repair = run_repair(
        requirements,
        evidence_by_requirement,
        contexts,
        generator,
        condition,
    )
    return PipelineResult(
        rfp_text=rfp_text,
        requirements=requirements,
        quote_inputs=quote_inputs,
        quote=quote,
        assumptions=assumptions,
        evidence_by_requirement=evidence_by_requirement,
        repair=repair,
    )
