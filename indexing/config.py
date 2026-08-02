import os
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    """Load simple KEY=VALUE pairs without overriding real environment variables."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "tinyllama")

# Shared Chroma settings used by both the Embedding Service and Retrieval Service.
# The older variable names are supported only as a migration fallback.
CHROMA_DB_PATH = os.getenv(
    "CHROMA_DB_PATH",
    os.getenv(
    "CHROMA_PERSIST_DIRECTORY",
    "/home/azureuser/local_rag_engine/embedding/chroma_db",
),
)
COLLECTION_NAME = os.getenv(
    "COLLECTION_NAME",
    os.getenv("CHROMA_COLLECTION_NAME", "document_embeddings"),
)
RESOLVED_CHROMA_DB_PATH = str(Path(CHROMA_DB_PATH).expanduser().resolve())

# Backward-compatible aliases for existing indexing code that may already import
# these names. New code should use CHROMA_DB_PATH and COLLECTION_NAME.
CHROMA_PERSIST_DIRECTORY = CHROMA_DB_PATH
CHROMA_COLLECTION_NAME = COLLECTION_NAME

RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "4"))

# Similarity threshold: only chunks with similarity >= this value are considered relevant
# Range: 0.0 (no match) to 1.0 (perfect match)
RETRIEVAL_SIMILARITY_THRESHOLD = float(os.getenv("RETRIEVAL_SIMILARITY_THRESHOLD", "0.5"))

# Leave unset by default because distance scales depend on the embedding/index setup.
# Set RETRIEVAL_MAX_DISTANCE if you want to filter weak matches.
RETRIEVAL_MAX_DISTANCE = os.getenv("RETRIEVAL_MAX_DISTANCE")
RETRIEVAL_MAX_DISTANCE = (
    float(RETRIEVAL_MAX_DISTANCE) if RETRIEVAL_MAX_DISTANCE else None
)

OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))


