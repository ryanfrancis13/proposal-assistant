from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    text: str
    trap: str


TRAPS = (
    ("unsupported_service", "Please migrate 35 servers to Google Cloud Platform."),
    ("discount_cap", "We have 40 servers and require a 20% discount."),
    (
        "price_floor",
        "We have 20 servers needing ongoing support for a 24-month term with 15 CSPS accounts and require a 15% discount.",
    ),
    ("deadline", "We have 40 servers and need completion within 2 months."),
    ("certification", "We have 35 servers and require HIPAA compliance."),
    ("no_coverage", "We have 40 servers and require mainframe migration."),
    ("stale_pricing", "Use the government case study pricing from 2022 for our quote."),
)


def generate_synthetic_cases(count: int = 20, seed: int = 7) -> list[SyntheticCase]:
    """Create reproducible RFP traps without calling an LLM."""
    if count < 1:
        raise ValueError("synthetic case count must be positive")
    cases = []
    for index in range(count):
        trap, sentence = TRAPS[(index + seed) % len(TRAPS)]
        context = (
            "We are a synthetic customer evaluating Meridian Cloudworks. "
            "Please explain the relevant service, evidence, assumptions, and pricing. "
        )
        cases.append(
            SyntheticCase(
                case_id=f"synthetic_{index + 1:03d}",
                text=context + sentence,
                trap=trap,
            )
        )
    return cases
