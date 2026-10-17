from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    generator_model: str
    embedding_model: str
    chunk_size: int
    top_k: int = 5


def load_settings(path: Path | None = None) -> Settings:
    settings_path = path or ROOT / "config" / "settings.yaml"
    with settings_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    models = raw.get("models", {})
    retrieval = raw.get("retrieval", {})
    return Settings(
        generator_model=models["generator"],
        embedding_model=models["embedding"],
        chunk_size=int(retrieval["chunk_size"]),
        top_k=int(retrieval.get("top_k", 5)),
    )
