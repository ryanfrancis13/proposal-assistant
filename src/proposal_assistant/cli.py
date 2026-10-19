import argparse
from pathlib import Path

from proposal_assistant.config import ROOT, load_settings
from proposal_assistant.export import export_docx
from proposal_assistant.generation import NIMGenerator
from proposal_assistant.models import RepairCondition
from proposal_assistant.pipeline import run_pipeline


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Draft a Meridian Cloudworks proposal")
    parser.add_argument("rfp", type=Path, help="path to the RFP text file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("proposal.docx"),
        help="DOCX output path",
    )
    parser.add_argument(
        "--condition",
        choices=[condition.value for condition in RepairCondition],
        default=RepairCondition.TARGETED_SECTION.value,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = load_settings()
    generator = NIMGenerator(settings.generator_model)
    result = run_pipeline(
        args.rfp.read_text(encoding="utf-8"),
        generator,
        ROOT / "data" / "raw",
        settings=settings,
        condition=RepairCondition(args.condition),
    )
    export_docx(args.output, result.repair.draft, result.quote, result.assumptions)
    passed = sum(item.passed for item in result.repair.verifications)
    print(f"Wrote {args.output}")
    print(f"Verified sections: {passed}/{len(result.repair.verifications)}")
    for verification in result.repair.verifications:
        if not verification.passed:
            issue_text = "; ".join(
                f"{issue.check_id}: {issue.detail}"
                for issue in verification.issues
            )
            print(f"Failed {verification.requirement_id}: {issue_text}")
    print(f"NIM calls: {generator.calls}")


if __name__ == "__main__":
    main()