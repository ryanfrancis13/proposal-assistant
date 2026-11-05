import argparse
from pathlib import Path

from proposal_assistant.config import ROOT, load_settings
from proposal_assistant.experiments import (
    run_experiment_cases,
    write_results,
)
from proposal_assistant.generation import NIMGenerator
from proposal_assistant.synthetic import generate_synthetic_cases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run proposal repair experiments")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="per NIM request timeout in seconds",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = load_settings()
    cases = generate_synthetic_cases(args.count, args.seed)

    def generator_factory() -> NIMGenerator:
        return NIMGenerator(settings.generator_model, timeout=args.timeout)

    records = run_experiment_cases(
        [(case.case_id, case.text) for case in cases],
        ROOT / "data" / "raw",
        settings,
        generator_factory,
        repeats=args.repeats,
        checkpoint_dir=args.output,
    )
    write_results(records, args.output)
    print(f"Wrote {len(records)} trial records to {args.output}")


if __name__ == "__main__":
    main()
