from pathlib import Path

from proposal_assistant.extract import extract_requirements

rfp_text = Path("data/eval/sample_rfp_02.txt").read_text(encoding="utf-8")
requirements = extract_requirements(rfp_text)

for r in requirements:
    print(f"- {r['topic']}: {r['detail']}")