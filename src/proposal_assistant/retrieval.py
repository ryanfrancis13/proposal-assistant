import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from proposal_assistant.ingestion import DocumentChunk, ingest_documents
from proposal_assistant.models import Evidence


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class EvidenceRetriever:
    """Return ranked document evidence while preserving source status metadata."""

    def __init__(self, raw_dir: Path, chunk_size: int):
        self.chunks = ingest_documents(raw_dir, chunk_size)
        self._index = BM25Okapi([_tokens(chunk.text) for chunk in self.chunks])

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        if not query.strip() or not self.chunks:
            return []
        scores = self._index.get_scores(_tokens(query))
        ranked = sorted(
            enumerate(scores),
            key=lambda item: (-float(item[1]), self.chunks[item[0]].chunk_id),
        )[:top_k]
        return [
            Evidence(
                evidence_id=f"E{position}",
                chunk_id=self.chunks[index].chunk_id,
                source_file=self.chunks[index].source_file,
                section=self.chunks[index].section,
                text=self.chunks[index].text,
                status=self.chunks[index].status,
                score=float(score),
            )
            for position, (index, score) in enumerate(ranked, start=1)
        ]
