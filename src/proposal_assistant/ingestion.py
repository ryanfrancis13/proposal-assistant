import re
from dataclasses import dataclass
from pathlib import Path


STALE_PRICING_SOURCES = {"case_10_govt.md"}


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_file: str
    section: str
    text: str
    status: str


def _sections(markdown: str) -> list[tuple[str, str]]:
    current_heading = "Overview"
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        elif not line.startswith("# "):
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return [(heading, body) for heading, body in sections if body]


def _split_body(body: str, chunk_size: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > chunk_size:
            chunks.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def ingest_documents(raw_dir: Path, chunk_size: int) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(raw_dir.glob("*.md")):
        status = "superseded_pricing" if path.name in STALE_PRICING_SOURCES else "current"
        for section, body in _sections(path.read_text(encoding="utf-8")):
            for piece in _split_body(body, chunk_size):
                chunk_number = sum(
                    1 for chunk in chunks if chunk.source_file == path.name
                )
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{path.name}::{chunk_number}",
                        source_file=path.name,
                        section=section,
                        text=piece,
                        status=status,
                    )
                )
    return chunks
