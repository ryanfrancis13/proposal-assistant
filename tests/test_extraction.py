from proposal_assistant.extraction import extract_quote_inputs, extract_requirements


def test_extraction_preserves_missing_quote_facts_as_none():
    inputs = extract_quote_inputs(
        "We have approximately 40 servers and need ongoing support after migration."
    )

    assert inputs.server_count == 40
    assert inputs.support_requested is True
    assert inputs.cloud_provider is None
    assert inputs.rehost_servers is None
    assert inputs.replatform_workloads is None
    assert inputs.negotiated_discount_pct is None


def test_extraction_reads_explicit_platform_and_discount():
    inputs = extract_quote_inputs(
        "We need to move 35 servers to Google Cloud Platform and want at least a 20% discount."
    )

    assert inputs.server_count == 35
    assert inputs.cloud_provider == "Google Cloud Platform"
    assert inputs.cloud_count == 1
    assert inputs.negotiated_discount_pct == 0.20


def test_requirements_are_traceable_to_original_sentences():
    requirements = extract_requirements(
        "We have 40 servers. We need this done within 4 months."
    )

    assert [item.requirement_id for item in requirements] == ["REQ-001", "REQ-002"]
    assert requirements[0].detail == "We have 40 servers."
    assert requirements[1].topic == "timeline"
