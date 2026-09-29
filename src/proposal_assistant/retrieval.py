import json
from pathlib import Path

import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi

from proposal_assistant.config import base_url, embedding_key, load_settings
from proposal_assistant.ingest import Chunk, build_chunks

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def embed_texts(client: OpenAI, model: str, texts: list[str], input_type: str) -> np.ndarray:
    response = client.embeddings.create(
        model=model,
        input=texts,
        extra_body={"input_type": input_type, "truncate": "END"},
    )
    return np.array([d.embedding for d in response.data])


def build_index():
    settings = load_settings()
    raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"

    chunks = build_chunks(
        raw_dir,
        chunk_size=settings["retrieval"]["chunk_size"],
        overlap=settings["retrieval"]["chunk_overlap"],
    )
    print(f"built {len(chunks)} chunks from {raw_dir}")

    client = OpenAI(api_key=embedding_key(), base_url=base_url(), timeout=60.0)
    texts = [c.text for c in chunks]

    # NIM embedding endpoints cap batch size; chunk the requests to be safe
    batch_size = 20
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors = embed_texts(client, settings["models"]["embedding"], batch, input_type="passage")
        all_vectors.append(vectors)
        print(f"  embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    embeddings = np.vstack(all_vectors)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    np.save(PROCESSED_DIR / "embeddings.npy", embeddings)

    metadata = [{"chunk_id": c.chunk_id, "source_file": c.source_file, "text": c.text} for c in chunks]
    with open(PROCESSED_DIR / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"saved index: {embeddings.shape[0]} vectors of dim {embeddings.shape[1]}")


class HybridRetriever:
    def __init__(self):
        settings = load_settings()
        self.model = settings["models"]["embedding"]
        self.client = OpenAI(api_key=embedding_key(), base_url=base_url(), timeout=30.0)

        with open(PROCESSED_DIR / "chunks.json", encoding="utf-8") as f:
            self.metadata = json.load(f)
        self.embeddings = np.load(PROCESSED_DIR / "embeddings.npy")

        tokenized = [_tokenize(m["text"]) for m in self.metadata]
        self.bm25 = BM25Okapi(tokenized)

    def _semantic_scores(self, query: str) -> np.ndarray:
        q_vec = embed_texts(self.client, self.model, [query], input_type="query")[0]
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(q_vec)
        norms[norms == 0] = 1e-9
        return (self.embeddings @ q_vec) / norms

    def search(self, query: str, top_k: int = 5, alpha: float = 0.5) -> list[dict]:
        bm25_raw = np.array(self.bm25.get_scores(_tokenize(query)))
        bm25_norm = bm25_raw / (bm25_raw.max() + 1e-9)

        sem_scores = self._semantic_scores(query)
        sem_norm = (sem_scores - sem_scores.min()) / (sem_scores.max() - sem_scores.min() + 1e-9)

        combined = alpha * sem_norm + (1 - alpha) * bm25_norm
        ranked_idx = np.argsort(-combined)[:top_k]

        return [
            {
                "chunk_id": self.metadata[i]["chunk_id"],
                "source_file": self.metadata[i]["source_file"],
                "text": self.metadata[i]["text"],
                "score": float(combined[i]),
            }
            for i in ranked_idx
        ]