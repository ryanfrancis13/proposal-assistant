from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv
import yaml


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


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


def nim_base_url() -> str:
    return os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")


def generator_api_key() -> str:
    key = os.getenv("NVIDIA_GENERATOR_KEY")
    if not key:
        raise RuntimeError("NVIDIA_GENERATOR_KEY is not set; add it to .env")
    return key
