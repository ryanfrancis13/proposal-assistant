from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SectionStatus(str, Enum):
    ANSWERED = "answered"
    PARTIAL = "partial"
    CANNOT_FULFIL = "cannot_fulfil"
    NO_EVIDENCE = "no_evidence"


class RepairCondition(str, Enum):
    NONE = "none"
    WHOLE_DOCUMENT = "whole_document"
    TARGETED_SECTION = "targeted_section"


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    topic: str
    detail: str


@dataclass(frozen=True)
class QuoteInputs:
    server_count: int | None = None
    rehost_servers: int | None = None
    replatform_workloads: int | None = None
    cloud_provider: str | None = None
    cloud_count: int | None = None
    support_requested: bool | None = None
    support_term_months: int | None = None
    negotiated_discount_pct: float | None = None
    csps_accounts: int | None = None


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    chunk_id: str
    source_file: str
    section: str
    text: str
    status: str = "current"
    score: float = 0.0


@dataclass(frozen=True)
class Claim:
    text: str
    evidence_ids: tuple[str, ...] = ()


@dataclass
class ProposalSection:
    requirement_id: str
    status: SectionStatus
    claims: list[Claim] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationIssue:
    check_id: str
    detail: str


@dataclass
class SectionVerification:
    requirement_id: str
    passed: bool
    issues: list[VerificationIssue] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationContext:
    evidence: tuple[Evidence, ...] = ()
    allowed_amounts: tuple[str, ...] = ()
    documented_terms: tuple[str, ...] = ()
    deadline_weeks: int | None = None
    minimum_documented_weeks: int | None = None


@dataclass
class ProposalDraft:
    sections: list[ProposalSection] = field(default_factory=list)
    pricing_text: str = ""


@dataclass(frozen=True)
class ExperimentRecord:
    rfp_id: str
    condition: RepairCondition
    run_index: int
    strict_compliance: bool
    loose_compliance: float
    violation_counts: dict[str, int]
    llm_calls: int
    error: str | None = None


def as_jsonable(value: Any) -> Any:
    """Convert the small model layer into JSON-compatible values."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [as_jsonable(item) for item in value]
    if isinstance(value, list):
        return [as_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: as_jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: as_jsonable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    return value
