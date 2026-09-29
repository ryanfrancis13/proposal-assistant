import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    chunk_id: str
    source_file: str
    text: str


def load_documents(raw_dir: Path) -> list[tuple[str, str]]:
    docs = []
    for path in sorted(raw_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append((path.name, text))
    return docs


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{tail}\n\n{chunks[i]}")
        chunks = overlapped

    return chunks


def build_chunks(raw_dir: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks = []
    for filename, text in load_documents(raw_dir):
        pieces = split_into_chunks(text, chunk_size, overlap)
        for i, piece in enumerate(pieces):
            chunks.append(Chunk(
                chunk_id=f"{filename}::{i}",
                source_file=filename,
                text=piece,
            ))
    return chunks