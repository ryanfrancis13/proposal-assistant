import json
from pathlib import Path

from proposal_assistant.experiments import aggregate_records, run_experiment, write_results
from proposal_assistant.generation import CountingGenerator
from proposal_assistant.models import ExperimentRecord, RepairCondition


ROOT = Path(__file__).resolve().parents[1]


def _generator():
    response = json.dumps(
        {
            "status": "partial",
            "claims": [{"text": "AWS is supported.", "evidence": ["E1"]}],
            "gaps": ["Not covered in our documents: customer scope"],
        }
    )
    return CountingGenerator([response] * 20)


def test_aggregate_reports_counts_confidence_intervals_and_calls():
    records = [
        ExperimentRecord("a", RepairCondition.NONE, 1, True, 1.0, {}, 3),
        ExperimentRecord("b", RepairCondition.NONE, 1, False, 0.5, {"V2": 1}, 4),
    ]

    summary = aggregate_records(records)[0]

    assert summary["n"] == 2
    assert summary["strict_compliance"] == 0.5
    assert 0 <= summary["strict_ci95_low"] <= summary["strict_ci95_high"] <= 1
    assert summary["mean_llm_calls"] == 3.5
    assert summary["violations_by_type"] == {"V2": 1}


def test_experiment_runner_records_each_condition(tmp_path):
    rfp = tmp_path / "case.txt"
    rfp.write_text("We have approximately 40 servers.", encoding="utf-8")

    records = run_experiment(
        [rfp],
        ROOT / "data" / "raw",
        settings=__import__("proposal_assistant.config", fromlist=["load_settings"]).load_settings(),
        generator_factory=_generator,
        repeats=1,
    )

    assert len(records) == 3
    assert {record.condition for record in records} == set(RepairCondition)
    assert all(record.llm_calls >= 1 for record in records)


def test_write_results_creates_json_and_csv(tmp_path):
    records = [
        ExperimentRecord("a", RepairCondition.NONE, 1, True, 1.0, {}, 2)
    ]

    write_results(records, tmp_path)

    assert (tmp_path / "records.json").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.csv").exists()
