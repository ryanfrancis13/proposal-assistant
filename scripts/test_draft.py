from pathlib import Path

from openai import OpenAI

from proposal_assistant.config import base_url, generator_key, load_settings
from proposal_assistant.extract import extract_requirements, gather_evidence
from proposal_assistant.generate import draft_section
from proposal_assistant.retrieval import HybridRetriever

settings = load_settings()
client = OpenAI(api_key=generator_key(), base_url=base_url(), timeout=60.0)

rfp_text = Path("data/eval/sample_rfp_01.txt").read_text(encoding="utf-8")
requirements = extract_requirements(rfp_text)
retriever = HybridRetriever()
enriched = gather_evidence(requirements, retriever)

for r in enriched:
    print(f"\n=== {r['topic']} ===")
    section = draft_section(r, settings["models"]["generator"], client)
    print(section)