import csv
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Iterable

from proposal_assistant.models import ExperimentRecord, RepairCondition
from proposal_assistant.pipeline import run_pipeline


CHECK_IDS = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")
GENERATION_FAILURE_ID = "V0"


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _mean_interval(values: list[float], z: float = 1.96) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, mean
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    margin = z * math.sqrt(variance / len(values))
    return mean - margin, mean + margin


def _is_v0_record(record: ExperimentRecord) -> bool:
    return (
        record.error is not None
        or GENERATION_FAILURE_ID in record.violation_counts
    )


def aggregate_records(records: Iterable[ExperimentRecord]) -> list[dict]:
    grouped: dict[RepairCondition, list[ExperimentRecord]] = {}
    for record in records:
        grouped.setdefault(record.condition, []).append(record)

    summaries = []
    for condition, items in grouped.items():
        valid_items = [item for item in items if not _is_v0_record(item)]
        v0_failures = len(items) - len(valid_items)
        strict_count = sum(item.strict_compliance for item in valid_items)
        loose_values = [item.loose_compliance for item in valid_items]
        call_values = [float(item.llm_calls) for item in valid_items]
        violations: dict[str, int] = {}
        for item in valid_items:
            for rule_id, count in item.violation_counts.items():
                violations[rule_id] = violations.get(rule_id, 0) + count
        strict_ci = _wilson_interval(strict_count, len(valid_items))
        loose_ci = _mean_interval(loose_values)
        call_ci = _mean_interval(call_values)
        summaries.append(
            {
                "condition": condition.value,
                "n": len(valid_items),
                "v0_failures": v0_failures,
                "strict_compliance": (
                    strict_count / len(valid_items) if valid_items else 0.0
                ),
                "strict_ci95_low": strict_ci[0],
                "strict_ci95_high": strict_ci[1],
                "loose_compliance": sum(loose_values) / len(loose_values)
                if loose_values
                else 0.0,
                "loose_ci95_low": loose_ci[0],
                "loose_ci95_high": loose_ci[1],
                "mean_llm_calls": sum(call_values) / len(call_values)
                if call_values
                else 0.0,
                "mean_llm_calls_ci95_low": call_ci[0],
                "mean_llm_calls_ci95_high": call_ci[1],
                "violations_by_type": violations,
            }
        )
    return summaries


def run_experiment(
    rfp_paths: list[Path],
    raw_dir: Path,
    settings,
    generator_factory: Callable[[], object],
    repeats: int = 1,
    conditions: tuple[RepairCondition, ...] = tuple(RepairCondition),
    progress: Callable[[str], None] | None = print,
    checkpoint_dir: Path | None = None,
) -> list[ExperimentRecord]:
    cases = [
        (rfp_path.stem, rfp_path.read_text(encoding="utf-8"))
        for rfp_path in rfp_paths
    ]
    return run_experiment_cases(
        cases,
        raw_dir,
        settings,
        generator_factory,
        repeats,
        conditions,
        progress=progress,
        checkpoint_dir=checkpoint_dir,
    )


def run_experiment_cases(
    cases: list[tuple[str, str]],
    raw_dir: Path,
    settings,
    generator_factory: Callable[[], object],
    repeats: int = 1,
    conditions: tuple[RepairCondition, ...] = tuple(RepairCondition),
    progress: Callable[[str], None] | None = print,
    checkpoint_dir: Path | None = None,
) -> list[ExperimentRecord]:
    records: list[ExperimentRecord] = []
    total_trials = len(cases) * len(conditions) * repeats
    completed_trials = 0
    for rfp_id, rfp_text in cases:
        for condition in conditions:
            for run_index in range(1, repeats + 1):
                if progress:
                    progress(
                        f"Starting trial {completed_trials + 1}/{total_trials}: "
                        f"{rfp_id} / {condition.value} / repeat {run_index}"
                    )
                generator = generator_factory()
                try:
                    result = run_pipeline(
                        rfp_text,
                        generator,
                        raw_dir,
                        settings=settings,
                        condition=condition,
                    )
                except Exception as exc:
                    # One malformed/API-failed trial must not discard the rest
                    # of a long experiment. Record it as a failed V0 trial.
                    records.append(
                        ExperimentRecord(
                            rfp_id=rfp_id,
                            condition=condition,
                            run_index=run_index,
                            strict_compliance=False,
                            loose_compliance=0.0,
                            violation_counts={GENERATION_FAILURE_ID: 1},
                            llm_calls=int(getattr(generator, "calls", 0)),
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )
                    completed_trials += 1
                    if checkpoint_dir:
                        write_results(records, checkpoint_dir)
                    if progress:
                        progress(f"Finished trial {completed_trials}/{total_trials}: V0")
                    continue
                verifications = result.repair.verifications
                total_checks = len(verifications) * len(CHECK_IDS)
                failed_checks = sum(
                    len({issue.check_id for issue in item.issues})
                    for item in verifications
                )
                passed_checks = total_checks - failed_checks
                violation_counts: dict[str, int] = {}
                for verification in verifications:
                    for issue in verification.issues:
                        violation_counts[issue.check_id] = (
                            violation_counts.get(issue.check_id, 0) + 1
                        )
                records.append(
                    ExperimentRecord(
                        rfp_id=rfp_id,
                        condition=condition,
                        run_index=run_index,
                        strict_compliance=all(
                            item.passed for item in verifications
                        ),
                        loose_compliance=(
                            passed_checks / total_checks if total_checks else 1.0
                        ),
                        violation_counts=violation_counts,
                        llm_calls=int(getattr(generator, "calls", 0)),
                    )
                )
                completed_trials += 1
                if checkpoint_dir:
                    write_results(records, checkpoint_dir)
                if progress:
                    progress(
                        f"Finished trial {completed_trials}/{total_trials}: "
                        f"strict={records[-1].strict_compliance}, "
                        f"calls={records[-1].llm_calls}"
                    )
    return records


def write_results(records: list[ExperimentRecord], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "records.json").open("w", encoding="utf-8") as handle:
        json.dump([asdict(record) for record in records], handle, indent=2, default=str)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(aggregate_records(records), handle, indent=2)
    with (output_dir / "summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        summaries = aggregate_records(records)
        fields = [
            "condition",
            "n",
            "v0_failures",
            "strict_compliance",
            "strict_ci95_low",
            "strict_ci95_high",
            "loose_compliance",
            "loose_ci95_low",
            "loose_ci95_high",
            "mean_llm_calls",
            "mean_llm_calls_ci95_low",
            "mean_llm_calls_ci95_high",
            "violations_by_type",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
