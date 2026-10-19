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
    generator = CountingGenerator(["not json"])

    with pytest.raises(ValueError, match="valid JSON"):
        draft_section(
            Requirement("REQ-001", "platform", "Which cloud platforms are supported?"),
            _evidence(),
            generator,
        )
