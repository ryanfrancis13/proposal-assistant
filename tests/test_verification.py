from proposal_assistant.models import (
    Claim,
    Evidence,
    ProposalSection,
    SectionStatus,
    VerificationContext,
)
from proposal_assistant.verification import verify_section


def _context(status: str = "current") -> VerificationContext:
    return VerificationContext(
        evidence=(
            Evidence(
                evidence_id="E1",
                chunk_id="product_migration.md::0",
                source_file="product_migration.md",
                section="Overview",
                text="Meridian supports AWS and Azure.",
                status=status,
            ),
        ),
        allowed_amounts=("INR 420,000.00",),
    )


def test_valid_section_passes():
    section = ProposalSection(
        requirement_id="REQ-001",
        status=SectionStatus.ANSWERED,
        claims=[Claim("Meridian supports AWS and Azure.", ("E1",))],
    )

    result = verify_section(section, _context())

    assert result.passed
    assert result.issues == []


def test_stale_evidence_and_unknown_amount_are_rejected():
    section = ProposalSection(
        requirement_id="REQ-001",
        status=SectionStatus.PARTIAL,
        claims=[
            Claim(
                "The previous project cost INR 999,999 and supports AWS.",
                ("E1",),
            )
        ],
        gaps=["Not covered in our documents: current price"],
    )

    result = verify_section(section, _context(status="superseded_pricing"))

    assert not result.passed
    assert {issue.check_id for issue in result.issues} == {"V1", "V4"}


def test_unsupported_capability_and_guarantee_language_are_rejected():
    section = ProposalSection(
        requirement_id="REQ-002",
        status=SectionStatus.ANSWERED,
        claims=[
            Claim(
                "Meridian guarantees it will reduce costs on GCP and is HIPAA compliant.",
                ("E1",),
            )
        ],
    )

    result = verify_section(section, _context())

    assert not result.passed
    assert {"V2", "V3"} <= {issue.check_id for issue in result.issues}


def test_structure_rules_are_rejected():
    section = ProposalSection(
        requirement_id="REQ-003",
        status=SectionStatus.NO_EVIDENCE,
        claims=[Claim("A claim.", ("E1",))],
        gaps=["No evidence found"],
    )

    result = verify_section(section, _context())

    assert not result.passed
    assert {"V5", "V6"} <= {issue.check_id for issue in result.issues}


def test_quote_amounts_are_checked_exactly():
    section = ProposalSection(
        requirement_id="REQ-004",
        status=SectionStatus.PARTIAL,
        claims=[Claim("The migration subtotal is INR 420,001.00.", ("E1",))],
        gaps=["Not covered in our documents: final scope"],
    )
    context = VerificationContext(
        evidence=_context().evidence,
        allowed_amounts=("INR 420,000.00",),
    )

    result = verify_section(section, context)

    assert not result.passed
    assert any(issue.check_id == "V4" for issue in result.issues)


def test_deadline_claim_below_documented_timeline_is_rejected():
    section = ProposalSection(
        requirement_id="REQ-005",
        status=SectionStatus.ANSWERED,
        claims=[Claim("Meridian can complete the migration in four weeks.", ("E1",))],
    )
    context = VerificationContext(
        evidence=_context().evidence,
        deadline_weeks=4,
        minimum_documented_weeks=12,
    )

    result = verify_section(section, context)

    assert not result.passed
    assert any(issue.check_id == "V7" for issue in result.issues)
