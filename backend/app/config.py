"""Central configuration loaded from environment / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    groq_api_key: str = ""
    model_name: str = "qwen/qwen3.8-27b"
    embed_model: str = "BAAI/bge-small-en-v1.5"   # runs locally via FastEmbed (ONNX, no GPU/API key)

    max_revisions: int = 2          # Architect <-> Critic loops
    word_tolerance: float = 0.10    # +/-10% of requested length is accepted
    min_critic_score: int = 8       # out of 10

    data_file: Path = BASE_DIR / "data" / "Legal_Problem_Statement.txt"
    faiss_dir: Path = BASE_DIR / "data" / "faiss_index"

    cors_origins: str = "http://localhost:8501"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
