import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables when present."""

    documents_dir: Path = Field(default=Path("documents"))
    chroma_db_dir: Path = Field(default=Path("chroma_db"))
    chroma_collection_name: str = Field(default="document_embeddings")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_embedding_model: str = Field(default="nomic-embed-text")
    ollama_llm_model: str = Field(default="tinyllama")
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    retrieval_top_k: int = Field(default=4)
    retrieval_similarity_threshold: float = Field(default=0.5)
    retrieval_max_distance: float | None = Field(default=None)

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_SERVICE_")


settings = Settings()

settings.chroma_db_dir = Path(
    os.getenv("CHROMA_DB_PATH", settings.chroma_db_dir)
).expanduser().resolve()
settings.chroma_collection_name = os.getenv(
    "COLLECTION_NAME",
    settings.chroma_collection_name,
)
settings.ollama_llm_model = os.getenv("OLLAMA_LLM_MODEL", settings.ollama_llm_model)
settings.retrieval_top_k = int(os.getenv("RETRIEVAL_TOP_K", str(settings.retrieval_top_k)))
settings.retrieval_similarity_threshold = float(
    os.getenv(
        "RETRIEVAL_SIMILARITY_THRESHOLD",
        str(settings.retrieval_similarity_threshold),
    )
)
retrieval_max_distance = os.getenv("RETRIEVAL_MAX_DISTANCE")
settings.retrieval_max_distance = float(retrieval_max_distance) if retrieval_max_distance else None
