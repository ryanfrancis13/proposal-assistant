from pathlib import Path

from proposal_assistant.config import load_settings
from proposal_assistant.experiments import run_experiment_cases
from proposal_assistant.generation import CountingGenerator
from proposal_assistant.synthetic import generate_synthetic_cases


ROOT = Path(__file__).resolve().parents[1]


def _generator():
    import json

    response = json.dumps(
        {
            "status": "partial",
            "claims": [{"text": "AWS is supported.", "evidence": ["E1"]}],
            "gaps": ["Not covered in our documents: customer scope"],
        }
    )
    return CountingGenerator([response] * 50)


def test_synthetic_cases_are_reproducible_and_cover_traps():
    first = generate_synthetic_cases(20, seed=11)
    second = generate_synthetic_cases(20, seed=11)

    assert first == second
    assert len(first) == 20
    assert {case.trap for case in first} == {
        "unsupported_service",
        "discount_cap",
        "price_floor",
        "deadline",
        "certification",
        "no_coverage",
        "stale_pricing",
    }


def test_price_floor_synthetic_trap_triggers_r5_violation():
    from proposal_assistant.extraction import extract_quote_inputs
    from proposal_assistant.quote_builder import build_quote

    cases = generate_synthetic_cases(7, seed=0)
    price_floor_case = next(case for case in cases if case.trap == "price_floor")
    quote, _ = build_quote(extract_quote_inputs(price_floor_case.text))

    assert "R5" in {v.rule_id for v in quote.violations}


def test_text_case_runner_uses_stable_ids_and_repeats():
    cases = [(case.case_id, case.text) for case in generate_synthetic_cases(2)]

    records = run_experiment_cases(
        cases,
        ROOT / "data" / "raw",
        load_settings(),
        _generator,
        repeats=2,
    )

    assert len(records) == 2 * 3 * 2
    assert {record.rfp_id for record in records} == {
        "synthetic_001",
        "synthetic_002",
    }
