from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import settings


class ChromaStorageError(RuntimeError):
    """Raised when ChromaDB cannot persist embeddings."""


class ChromaStoreEmptyError(RuntimeError):
    """Raised when the configured ChromaDB collection has no indexed chunks."""


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]
    distance: float | None
    similarity_score: float | None

    @property
    def source(self) -> str:
        for key in ("source", "filename", "file_name", "document", "path"):
            value = self.metadata.get(key)
            if value:
                return Path(str(value)).name
        return "unknown"


class ChromaVectorStore:
    """Persistent ChromaDB storage for document chunks and embeddings."""

    def __init__(self, persist_directory: Path, collection_name: str) -> None:
        self.persist_directory = persist_directory.expanduser().resolve()
        self.collection_name = collection_name
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection: Collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    def count(self) -> int:
        """Return the number of indexed vectors in the configured collection."""
        return self.collection.count()

    def verify_ready(self) -> int:
        """Ensure at least one vector exists before answering questions."""
        indexed_count = self.count()
        if indexed_count == 0:
            raise ChromaStoreEmptyError(
                "The vector database is empty. Please upload and index documents."
            )
        return indexed_count

    def add_chunks(
        self,
        chunks: list[dict[str, int | str | None]],
        embeddings: list[list[float]],
    ) -> None:
        """Store chunk text, embeddings, and source metadata in ChromaDB."""
        if len(chunks) != len(embeddings):
            raise ChromaStorageError("Chunk count and embedding count do not match.")

        try:
            metadatas = []
            for chunk in chunks:
                metadata: dict[str, int | str] = {
                    "filename": str(chunk["document_name"]),
                    "chunk_id": str(chunk["chunk_id"]),
                    "chunk_text": str(chunk["text"]),
                }
                if chunk["page_number"] is not None:
                    metadata["page_number"] = int(chunk["page_number"])
                metadatas.append(metadata)

            self.collection.add(
                ids=[str(chunk["chunk_id"]) for chunk in chunks],
                documents=[str(chunk["text"]) for chunk in chunks],
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise ChromaStorageError("Failed to store embeddings in ChromaDB.") from exc

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        max_distance: float | None = None,
    ) -> list[RetrievedChunk]:
        """Search the indexed chunks using a query embedding."""
        indexed_count = self.count()
        if indexed_count == 0:
            raise ChromaStoreEmptyError(
                "The vector database is empty. Please upload and index documents."
            )

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, indexed_count),
            include=["documents", "metadatas", "distances"],
        )

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            if not document:
                continue
            if max_distance is not None and distance is not None and float(distance) > max_distance:
                continue

            similarity_score = None
            if distance is not None:
                clamped_distance = max(0.0, min(float(distance), 2.0))
                similarity_score = 1.0 - (clamped_distance / 2.0)

            chunks.append(
                RetrievedChunk(
                    text=str(document),
                    metadata=metadata or {},
                    distance=float(distance) if distance is not None else None,
                    similarity_score=similarity_score,
                )
            )

        return chunks


vector_store = ChromaVectorStore(
    persist_directory=settings.chroma_db_dir,
    collection_name=settings.chroma_collection_name,
)
