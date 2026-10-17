from pathlib import Path

from proposal_assistant.ingestion import ingest_documents
from proposal_assistant.retrieval import EvidenceRetriever


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def test_ingestion_marks_case_10_pricing_as_stale():
    chunks = ingest_documents(RAW, chunk_size=1200)

    stale = [chunk for chunk in chunks if chunk.source_file == "case_10_govt.md"]
    current = [chunk for chunk in chunks if chunk.source_file == "case_09_saas.md"]

    assert stale
    assert all(chunk.status == "superseded_pricing" for chunk in stale)
    assert all(chunk.status == "current" for chunk in current)


def test_retrieval_returns_cited_evidence_with_stable_ids():
    retriever = EvidenceRetriever(RAW, chunk_size=1200)

    results = retriever.search("rehost servers per week migration squad", top_k=5)

    assert 1 <= len(results) <= 5
    assert [item.evidence_id for item in results] == [
        f"E{number}" for number in range(1, len(results) + 1)
    ]
    assert any(item.source_file == "product_migration.md" for item in results)
