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
    neo4j_connection_timeout: float = 5.0
    neo4j_max_retry_time: float = 15.0
    neo4j_pool_size: int = 50
    neo4j_acquisition_timeout: float = 30.0
    neo4j_connection_lifetime: float = 3600.0

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password or password == "replace-with-a-long-local-password":
            raise ValueError("Önce python main.py configure çalıştırın veya .env dosyasını doldurun.")
        mode = os.getenv("ANSWER_MODE", "ollama")
        if mode not in {"sources", "ollama"}:
            raise ValueError("ANSWER_MODE sources veya ollama olmalı.")
        try:
            connection_timeout = float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "5"))
            retry_time = float(os.getenv("NEO4J_MAX_RETRY_TIME", "15"))
            pool_size = int(os.getenv("NEO4J_POOL_SIZE", "50"))
            acquisition_timeout = float(os.getenv("NEO4J_ACQUISITION_TIMEOUT", "30"))
            connection_lifetime = float(os.getenv("NEO4J_CONNECTION_LIFETIME", "3600"))
        except ValueError as exc:
            raise ValueError("Neo4j timeout ve pool ayarları sayısal olmalı.") from exc
        if (connection_timeout <= 0 or retry_time < 0 or not 1 <= pool_size <= 1000
                or acquisition_timeout <= 0 or connection_lifetime <= 0):
            raise ValueError("Neo4j timeout değerleri pozitif, retry negatif olmayan ve pool 1–1000 olmalı.")
        return cls(os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
                   os.getenv("NEO4J_USER", "neo4j"), password,
                   os.getenv("NEO4J_DATABASE", "neo4j"),
                   os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
                   os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), mode,
                   connection_timeout, retry_time, pool_size, acquisition_timeout,
                   connection_lifetime)
