import json
from pathlib import Path

from proposal_assistant.export import export_docx
from proposal_assistant.generation import CountingGenerator
from proposal_assistant.models import RepairCondition
from proposal_assistant.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def _response(text: str) -> str:
    return json.dumps(
        {
            "status": "partial",
            "claims": [{"text": text, "evidence": ["E1"]}],
            "gaps": ["Not covered in our documents: customer-specific scope"],
        }
    )


def test_pipeline_connects_extraction_retrieval_quote_and_repair(tmp_path):
    rfp = (
        "We have approximately 40 servers. We need this done within 4 months. "
        "We would also like ongoing support options."
    )
    generator = CountingGenerator([_response("AWS is supported.")] * 3)

    result = run_pipeline(
        rfp,
        generator,
        ROOT / "data" / "raw",
        condition=RepairCondition.TARGETED_SECTION,
    )

    assert result.quote_inputs.server_count == 40
    assert result.quote.migration is not None
    assert result.requirements
    assert all(result.evidence_by_requirement.values())
    assert len(result.repair.draft.sections) == len(result.requirements)
    assert generator.calls == len(result.requirements)


def test_docx_export_creates_readable_file(tmp_path):
    generator = CountingGenerator([_response("AWS is supported.")])
    result = run_pipeline(
        "We have 40 servers.",
        generator,
        ROOT / "data" / "raw",
        condition=RepairCondition.NONE,
    )
    output = export_docx(tmp_path / "proposal.docx", result.repair.draft, result.quote)

    assert output.exists()
    assert output.stat().st_size > 0
