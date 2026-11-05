from pathlib import Path

from proposal_assistant.web import (
    DemoGenerator,
    build_presets,
    execute_proposal_request,
)


ROOT = Path(__file__).resolve().parents[1]


def test_build_presets_loads_formatted_eval_samples_only():
    data = build_presets(ROOT)

    assert len(data["presets"]) == 2
    assert data["presets"][0]["id"] == "sample_rfp_01"
    assert "\n" not in data["presets"][0]["text"]
    assert "_" not in data["presets"][0]["label"]


def test_execute_proposal_request_in_demo_mode_verifies_and_exports_docx(tmp_path):
    docx_out = tmp_path / "demo_proposal.docx"
    payload = execute_proposal_request(
        "We need to migrate 35 servers to Google Cloud Platform and want a 20% discount.",
        condition_str="targeted_section",
        mode="demo",
        root=ROOT,
        docx_path=docx_out,
    )

    assert payload["strict_compliance"] is True
    assert payload["verified_sections"] == payload["total_sections"]
    assert payload["llm_calls"] == len(payload["sections"])
    assert payload["sections"][0]["status_label"] == "Outside Current Scope"
    assert any("Policy violation (R3)" in item for item in payload["assumptions"])
    assert docx_out.exists()


def test_demo_generator_handles_standard_and_trap_prompts():
    gen = DemoGenerator()
    out = gen.generate(
        "Requirement: We have 40 servers.\n[E1] product_migration.md > Overview\nText"
    )

    assert '"status": "answered"' in out
    assert gen.calls == 1
