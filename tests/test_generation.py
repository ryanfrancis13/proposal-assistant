import json

import pytest

from proposal_assistant.generation import CountingGenerator, draft_section
from proposal_assistant.models import Evidence, Requirement, SectionStatus


def _evidence():
    return [
        Evidence(
            evidence_id="E1",
            chunk_id="product_migration.md::0",
            source_file="product_migration.md",
            section="Overview",
            text="Meridian migrates to AWS and Azure.",
        )
    ]


def test_draft_section_parses_structured_claims_and_counts_call():
    generator = CountingGenerator(
        [
            json.dumps(
                {
                    "status": "answered",
                    "claims": [
                        {
                            "text": "Meridian supports AWS and Azure.",
                            "evidence": ["E1"],
                        }
                    ],
                    "gaps": [],
                }
            )
        ]
    )

    section = draft_section(
        Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
        _evidence(),
        generator,
    )

    assert generator.calls == 1
    assert section.status is SectionStatus.ANSWERED
    assert section.claims[0].evidence_ids == ("E1",)


def test_draft_section_rejects_unknown_citations():
    generator = CountingGenerator(
        [
            json.dumps(
                {
                    "status": "answered",
                    "claims": [{"text": "Unsupported claim.", "evidence": ["E9"]}],
                    "gaps": [],
                }
            )
        ]
    )

    with pytest.raises(ValueError, match="evidence"):
        draft_section(
            Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
            _evidence(),
            generator,
        )


def test_draft_section_rejects_non_json_model_output():
    generator = CountingGenerator(["not json", "still not json"])

    with pytest.raises(ValueError, match="no JSON object"):
        draft_section(
            Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
            _evidence(),
            generator,
        )


def test_draft_section_accepts_fenced_json_with_preamble():
    generator = CountingGenerator(
        [
            'Here is the section:\n```json\n'
            '{"status":"answered","claims":[{"text":"AWS is supported.","evidence":["E1"]}],"gaps":[]}'
            "\n```"
        ]
    )

    section = draft_section(
        Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
        _evidence(),
        generator,
    )

    assert section.status is SectionStatus.ANSWERED


def test_draft_section_accepts_common_claim_and_citation_aliases():
    generator = CountingGenerator(
        [
            json.dumps(
                {
                    "status": "answered",
                    "claims": [{"claim": "AWS is supported.", "citations": ["E1"]}],
                    "gaps": [],
                }
            )
        ]
    )

    section = draft_section(
        Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
        _evidence(),
        generator,
    )

    assert section.claims[0].text == "AWS is supported."
    assert section.claims[0].evidence_ids == ("E1",)


def test_draft_section_retries_when_top_level_schema_is_wrong():
    generator = CountingGenerator(
        [
            json.dumps({"answer": "AWS is supported."}),
            json.dumps(
                {
                    "status": "answered",
                    "claims": [{"text": "AWS is supported.", "evidence": ["E1"]}],
                    "gaps": [],
                }
            ),
        ]
    )

    section = draft_section(
        Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
        _evidence(),
        generator,
    )

    assert generator.calls == 2
    assert section.status is SectionStatus.ANSWERED


def test_draft_section_normalizes_single_top_level_claim():
    generator = CountingGenerator(
        [json.dumps({"text": "AWS is supported.", "evidence": ["E1"]})]
    )

    section = draft_section(
        Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
        _evidence(),
        generator,
    )

    assert section.status is SectionStatus.ANSWERED
    assert section.claims[0].text == "AWS is supported."
