from proposal_assistant.models import (
    Claim,
    ProposalSection,
    SectionStatus,
    as_jsonable,
)


def test_section_serializes_without_losing_status_or_citations():
    section = ProposalSection(
        requirement_id="REQ-001",
        status=SectionStatus.PARTIAL,
        claims=[Claim("AWS is supported.", ("E1",))],
        gaps=["Not covered in our documents: delivery date"],
    )

    assert as_jsonable(section) == {
        "requirement_id": "REQ-001",
        "status": "partial",
        "claims": [{"text": "AWS is supported.", "evidence_ids": ["E1"]}],
        "gaps": ["Not covered in our documents: delivery date"],
    }


def test_settings_load_from_repository_config():
    from proposal_assistant.config import load_settings

    settings = load_settings()

    assert settings.generator_model
    assert settings.embedding_model
    assert settings.chunk_size > 0
    assert settings.top_k == 5
