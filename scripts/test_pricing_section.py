from pathlib import Path

from openai import OpenAI

from proposal_assistant.config import base_url, generator_key, load_settings
from proposal_assistant.extract import extract_quote_inputs
from proposal_assistant.generate import draft_pricing_section
from proposal_assistant.pricing import build_quote_from_inputs

settings = load_settings()
client = OpenAI(api_key=generator_key(), base_url=base_url(), timeout=60.0)

rfp_text = Path("data/eval/sample_rfp_01.txt").read_text(encoding="utf-8")
inputs = extract_quote_inputs(rfp_text, client, settings["models"]["generator"])
print("Extracted quote inputs:", inputs)

quote, assumptions = build_quote_from_inputs(inputs)
print("\nAssumptions made:")
for a in assumptions:
    print(f"  - {a}")

print("\nViolations:", quote.violations or "none")

section = draft_pricing_section(quote, assumptions, client, settings["models"]["generator"])
print("\n=== Drafted pricing section ===")
print(section)