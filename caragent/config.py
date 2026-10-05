from dataclasses import dataclass
from pathlib import Path
import os
import secrets

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def configure() -> Path:
    """Generate a local secret once. Never overwrite an existing configuration."""
    path = ROOT / ".env"
    if not path.exists():
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        with path.open("x", encoding="utf-8") as target:
            target.write(template.replace("replace-with-a-long-local-password", secrets.token_hex(20)))
    return path


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    database: str
    ollama_url: str
    ollama_model: str
    answer_mode: str

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password or password == "replace-with-a-long-local-password":
            raise ValueError("Önce python main.py configure çalıştırın veya .env dosyasını doldurun.")
        mode = os.getenv("ANSWER_MODE", "ollama")
        if mode not in {"sources", "ollama"}:
            raise ValueError("ANSWER_MODE sources veya ollama olmalı.")
        return cls(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
                   os.getenv("NEO4J_USER", "neo4j"), password,
                   os.getenv("NEO4J_DATABASE", "neo4j"),
                   os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
                   os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), mode)
