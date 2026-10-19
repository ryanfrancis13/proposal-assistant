from dataclasses import dataclass

from proposal_assistant.generation import TextGenerator, draft_section
from proposal_assistant.models import (
    Evidence,
    ProposalDraft,
    ProposalSection,
    RepairCondition,
    Requirement,
    SectionVerification,
    VerificationContext,
)
from proposal_assistant.verification import verify_section


@dataclass
class RepairResult:
    draft: ProposalDraft
    verifications: list[SectionVerification]
    initial_verifications: list[SectionVerification]


def _draft_and_verify(
    requirements: list[Requirement],
    evidence_by_requirement: dict[str, list[Evidence]],
    contexts: dict[str, VerificationContext],
    generator: TextGenerator,
    feedback_by_requirement: dict[str, list[str]] | None = None,
) -> tuple[list[ProposalSection], list[SectionVerification]]:
    sections: list[ProposalSection] = []
    verifications: list[SectionVerification] = []
    for requirement in requirements:
        section = draft_section(
            requirement,
            evidence_by_requirement.get(requirement.requirement_id, []),
            generator,
            repair_feedback=(feedback_by_requirement or {}).get(
                requirement.requirement_id
            ),
        )
        sections.append(section)
        verifications.append(
            verify_section(section, contexts.get(requirement.requirement_id, VerificationContext()))
        )
    return sections, verifications


def run_repair(
    requirements: list[Requirement],
    evidence_by_requirement: dict[str, list[Evidence]],
    contexts: dict[str, VerificationContext],
    generator: TextGenerator,
    condition: RepairCondition,
) -> RepairResult:
    """Draft once, then apply exactly one documented repair condition."""
    sections, initial_verifications = _draft_and_verify(
        requirements, evidence_by_requirement, contexts, generator
    )
    final_verifications = initial_verifications

    failed = {
        result.requirement_id: result
        for result in initial_verifications
        if not result.passed
    }
    if failed and condition is not RepairCondition.NONE:
        if condition is RepairCondition.WHOLE_DOCUMENT:
            repair_ids = {requirement.requirement_id for requirement in requirements}
        else:
            repair_ids = set(failed)

        repair_requirements = [
            requirement
            for requirement in requirements
            if requirement.requirement_id in repair_ids
        ]
        feedback = {
            requirement_id: [
                issue.detail for issue in failed[requirement_id].issues
            ]
            for requirement_id in repair_ids
            if requirement_id in failed
        }
        repaired_sections, repaired_verifications = _draft_and_verify(
            repair_requirements,
            evidence_by_requirement,
            contexts,
            generator,
            feedback,
        )
        repaired_by_id = {
            section.requirement_id: section for section in repaired_sections
        }
        verification_by_id = {
            result.requirement_id: result for result in repaired_verifications
        }
        sections = [repaired_by_id.get(section.requirement_id, section) for section in sections]
        final_verifications = [
            verification_by_id.get(result.requirement_id, result)
            for result in final_verifications
        ]

    return RepairResult(
        draft=ProposalDraft(sections=sections),
        verifications=final_verifications,
        initial_verifications=initial_verifications,
    )
