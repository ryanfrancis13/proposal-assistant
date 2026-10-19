from proposal_assistant.cli import _parser


def test_cli_defaults_to_targeted_repair_and_docx_output():
    args = _parser().parse_args(["rfp.txt"])

    assert args.output.name == "proposal.docx"
    assert args.condition == "targeted_section"
