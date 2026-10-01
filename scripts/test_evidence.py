from pathlib import Path

from proposal_assistant.extract import extract_requirements, gather_evidence
from proposal_assistant.retrieval import HybridRetriever

rfp_text = Path("data/eval/sample_rfp_01.txt").read_text(encoding="utf-8")
requirements = extract_requirements(rfp_text)
retriever = HybridRetriever()
enriched = gather_evidence(requirements, retriever)

for r in enriched:
    print(f"\n{r['topic']}: {r['detail']}")
    for hit in r["evidence"]:
        preview = hit["text"][:80].replace("\n", " ")
        print(f"  [{hit['score']:.3f}] {hit['source_file']} :: {preview}...")