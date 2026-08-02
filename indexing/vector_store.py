import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

from config import (
    COLLECTION_NAME,
    RESOLVED_CHROMA_DB_PATH,
    RETRIEVAL_MAX_DISTANCE,
    RETRIEVAL_TOP_K,
)

logger = logging.getLogger(__name__)


class ChromaStoreEmptyError(Exception):
    """Raised when the configured Chroma collection has no indexed chunks."""


class ChromaCollectionNotFoundError(Exception):
    """Raised when the configured Chroma collection does not exist."""


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: Dict[str, Any]
    distance: Optional[float]
    similarity_score: Optional[float]

    @property
    def source(self) -> str:
        for key in ("source", "filename", "file_name", "document", "path"):
            value = self.metadata.get(key)
            if value:
                return Path(str(value)).name
        return "unknown"


class VectorStore:
    def __init__(
        self,
        persist_directory: str = RESOLVED_CHROMA_DB_PATH,
        collection_name: str = COLLECTION_NAME,
        top_k: int = RETRIEVAL_TOP_K,
        max_distance: Optional[float] = RETRIEVAL_MAX_DISTANCE,
    ) -> None:
        self.persist_directory = str(Path(persist_directory).expanduser().resolve())
        self.collection_name = collection_name
        self.top_k = top_k
        self.max_distance = max_distance
        self.client = None

    def _collection(self):
        chroma_path = Path(self.persist_directory)
        if not chroma_path.exists():
            raise ChromaCollectionNotFoundError(
                "No indexed documents found. Please index documents first."
            )

        if self.client is None:
            self.client = chromadb.PersistentClient(path=self.persist_directory)

        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception as exc:
            raise ChromaCollectionNotFoundError(
                "No indexed documents found. Please index documents first."
            ) from exc

    def indexed_vector_count(self) -> int:
        """Return vector count after verifying the configured collection exists."""
        return self._collection().count()

    def startup_report(self) -> int:
        logger.info("Using ChromaDB:")
        logger.info("%s", self.persist_directory)
        logger.info("Collection:")
        logger.info("%s", self.collection_name)

        count = self.indexed_vector_count()
        logger.info("Connected to ChromaDB")
        logger.info("Collection: %s", self.collection_name)
        logger.info("Indexed vectors: %s", count)
        return count

    def verify_ready(self) -> int:
        """Verify the collection exists and contains indexed vectors before retrieval."""
        indexed_count = self.indexed_vector_count()
        if indexed_count == 0:
            raise ChromaStoreEmptyError(
                "The vector database is empty. Please upload and index documents."
            )
        return indexed_count

    def similarity_search(self, query_embedding: List[float]) -> List[RetrievedChunk]:
        """Search the existing ChromaDB collection using the query embedding only."""
        collection = self._collection()

        indexed_count = collection.count()
        if indexed_count == 0:
            raise ChromaStoreEmptyError(
                "The vector database is empty. Please upload and index documents."
            )

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(self.top_k, indexed_count),
            include=["documents", "metadatas", "distances"],
        )

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks: List[RetrievedChunk] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            if not document:
                continue
            if self.max_distance is not None and distance is not None:
                if float(distance) > self.max_distance:
                    continue
            
            # Convert distance to similarity score (0.0 to 1.0, higher = better match)
            # For cosine distance (0-2), similarity = 1 - (distance / 2)
            # This is a standard conversion and works for most embedding models
            similarity_score = None
            if distance is not None:
                dist = float(distance)
                # Clamp distance between 0 and 2 for safety
                clamped_dist = max(0.0, min(dist, 2.0))
                similarity_score = 1.0 - (clamped_dist / 2.0)
            
            chunks.append(
                RetrievedChunk(
                    text=str(document),
                    metadata=metadata or {},
                    distance=float(distance) if distance is not None else None,
                    similarity_score=similarity_score,
                )
            )

        logger.info("Similarity search completed")
        logger.info("Chunks retrieved: %s", len(chunks))
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i+1}: source={chunk.source}, similarity={chunk.similarity_score:.4f}")
            logger.info(f"  Text preview: {chunk.text[:100]}...")
        return chunks
