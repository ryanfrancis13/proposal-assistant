from dataclasses import dataclass
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
from proposal_assistant.pricing import Quote, format_inr


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
        quote.negotiated_discount_amount(),
        quote.total(),
    ]
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
    quote, assumptions = build_quote(quote_inputs)
    retriever = EvidenceRetriever(raw_dir, settings.chunk_size)
    evidence_by_requirement = {
        requirement.requirement_id: retriever.search(
            f"{requirement.topic}: {requirement.detail}",
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
