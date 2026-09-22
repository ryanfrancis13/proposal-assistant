import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def load_settings():
    with open(ROOT / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def generator_key():
    key = os.getenv("NVIDIA_GENERATOR_KEY")
    if not key:
        raise RuntimeError("NVIDIA_GENERATOR_KEY is not set. Check your .env file.")
    return key


def embedding_key():
    key = os.getenv("NVIDIA_EMBEDDING_KEY")
    if not key:
        raise RuntimeError("NVIDIA_EMBEDDING_KEY is not set. Check your .env file.")
    return key


def base_url():
    return os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")