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


def test_currency_checker_does_not_treat_punctuation_as_amount():
    section = ProposalSection(
        requirement_id="REQ-006",
        status=SectionStatus.ANSWERED,
        claims=[Claim("The price is Rs, subject to final scope.", ("E1",))],
    )

    result = verify_section(section, _context())

    assert not any(issue.check_id == "V4" for issue in result.issues)


def test_negation_check_uses_word_boundaries_not_substrings():
    false_negation = ProposalSection(
        requirement_id="REQ-007",
        status=SectionStatus.ANSWERED,
        claims=[
            Claim(
                "Please note that Meridian supports GCP and another SAP HANA option.",
                ("E1",),
            )
        ],
    )
    true_negation = ProposalSection(
        requirement_id="REQ-008",
        status=SectionStatus.CANNOT_FULFIL,
        claims=[
            Claim(
                "Meridian does not currently migrate to GCP or SAP HANA.",
                ("E1",),
            )
        ],
    )

    false_result = verify_section(false_negation, _context())
    true_result = verify_section(true_negation, _context())

    assert not false_result.passed
    assert any(issue.check_id == "V2" for issue in false_result.issues)
    assert true_result.passed


def test_discount_above_cap_is_rejected_unless_declined():
    granted = ProposalSection(
        requirement_id="REQ-009",
        status=SectionStatus.ANSWERED,
        claims=[Claim("Meridian will apply a 20% discount to the quote.", ("E1",))],
    )
    declined = ProposalSection(
        requirement_id="REQ-010",
        status=SectionStatus.CANNOT_FULFIL,
        claims=[
            Claim(
                "Meridian cannot offer a 20% discount because the cap is 15%.",
                ("E1",),
            )
        ],
    )

    granted_result = verify_section(granted, _context())
    declined_result = verify_section(declined, _context())

    assert not granted_result.passed
    assert any(issue.check_id == "V4" for issue in granted_result.issues)
    assert declined_result.passed


def test_negated_guarantee_disclaimer_is_allowed():
    disclaimer = ProposalSection(
        requirement_id="REQ-011",
        status=SectionStatus.ANSWERED,
        claims=[
            Claim(
                "Meridian does not guarantee a specific cloud cost reduction.",
                ("E1",),
            )
        ],
    )

    result = verify_section(disclaimer, _context())

    assert result.passed
