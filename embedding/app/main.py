from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import router
from app.schemas import ErrorResponse
from app.utils import configure_logging, get_logger
from app.vector_store import vector_store

configure_logging()
logger = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Using ChromaDB:")
    logger.info("%s", settings.chroma_db_dir)
    logger.info("Collection:")
    logger.info("%s", settings.chroma_collection_name)
    logger.info("Connected to ChromaDB")
    logger.info("Collection: %s", settings.chroma_collection_name)
    logger.info("Indexed vectors: %s", vector_store.count())
    yield

app = FastAPI(
    title="Embedding and RAG Service",
    description=(
        "FastAPI service for uploading PDF, DOCX, and TXT documents, creating "
        "embeddings with Ollama, storing vectors in ChromaDB, and answering "
        "questions with retrieval-augmented generation."
    ),
    version="1.0.0",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    lifespan=lifespan,
)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint used to verify the API is running."""
    return {"status": "ok", "service": "embedding-rag-service"}


app.include_router(router)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Simple health endpoint for container and uptime checks."""
    return {"status": "ok"}


@app.get("/app", tags=["UI"])
async def ui_app() -> FileResponse:
    """Serve the interactive web frontend."""
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
