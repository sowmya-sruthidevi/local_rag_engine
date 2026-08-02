import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routes import router
from vector_store import (
    ChromaCollectionNotFoundError,
    ChromaStoreEmptyError,
    VectorStore,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store = VectorStore()
    try:
        vector_store.startup_report()
    except ChromaCollectionNotFoundError as exc:
        logger.warning("%s", exc)
        logger.warning("ChromaDB path: %s", vector_store.persist_directory)
        logger.warning("Collection: %s", vector_store.collection_name)
        logger.warning("Indexed vectors: unavailable")
    except ChromaStoreEmptyError as exc:
        logger.warning("%s", exc)
        logger.warning("ChromaDB path: %s", vector_store.persist_directory)
        logger.warning("Collection: %s", vector_store.collection_name)
        logger.warning("Indexed vectors: 0")
    yield


app = FastAPI(
    title="RAG Retrieval Service",
    description="Answers questions using chunks already indexed in ChromaDB.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
