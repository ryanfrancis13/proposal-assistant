import json

from proposal_assistant.generation import CountingGenerator
from proposal_assistant.models import (
    Evidence,
    RepairCondition,
    Requirement,
    SectionStatus,
    VerificationContext,
)
from proposal_assistant.repair import run_repair


REQS = [
    Requirement("REQ-001", "platform", "Which platform is supported?"),
    Requirement("REQ-002", "timeline", "What is the timeline?"),
]
EVIDENCE = {
    requirement.requirement_id: [
        Evidence(
            "E1",
            "product_migration.md::0",
            "product_migration.md",
            "Overview",
            "Meridian supports AWS and Azure.",
        )
    ]
    for requirement in REQS
}
CONTEXTS = {
    requirement.requirement_id: VerificationContext(evidence=tuple(EVIDENCE[requirement.requirement_id]))
    for requirement in REQS
}


def response(text: str, evidence: list[str] | None = None) -> str:
    return json.dumps(
        {
            "status": "answered",
            "claims": [{"text": text, "evidence": evidence or ["E1"]}],
            "gaps": [],
        }
    )


def test_no_repair_keeps_failed_sections_and_call_count():
    generator = CountingGenerator([response("GCP is supported."), response("AWS is supported.")])

    result = run_repair(
        REQS, EVIDENCE, CONTEXTS, generator, RepairCondition.NONE
    )

    assert generator.calls == 2
    assert result.initial_verifications[0].passed is False
    assert result.verifications[0].passed is False
    assert result.draft.sections[0].status is SectionStatus.ANSWERED


def test_targeted_repair_only_calls_failed_section():
    generator = CountingGenerator(
        [
            response("GCP is supported."),
            response("AWS is supported."),
            response("AWS is supported."),
        ]
    )

    result = run_repair(
        REQS, EVIDENCE, CONTEXTS, generator, RepairCondition.TARGETED_SECTION
    )

    assert generator.calls == 3
    assert result.initial_verifications[0].passed is False
    assert result.verifications[0].passed is True
    assert result.verifications[1].passed is True


def test_whole_document_repair_calls_all_sections_again():
    generator = CountingGenerator(
        [
            response("GCP is supported."),
            response("AWS is supported."),
            response("AWS is supported."),
            response("AWS is supported."),
        ]
    )

    result = run_repair(
        REQS, EVIDENCE, CONTEXTS, generator, RepairCondition.WHOLE_DOCUMENT
    )

    assert generator.calls == 4
    assert all(item.passed for item in result.verifications)
