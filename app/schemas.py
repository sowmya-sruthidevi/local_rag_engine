from typing import Literal

from pydantic import BaseModel, Field


class FileIndexingResult(BaseModel):
    """Indexing outcome for one uploaded file."""

    filename: str = Field(..., description="Original uploaded filename")
    status: Literal["success", "failed"]
    chunks_created: int = Field(default=0, ge=0)
    error: str | None = Field(default=None, description="Failure reason when status is failed")


class AskRequest(BaseModel):
    """Question request used by the RAG answer endpoint."""

    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    """Grounded answer returned by the RAG endpoint."""

    question: str
    answer: str
    sources: list[str]
    retrieved_chunks: list[str]
    similarity_scores: list[float]
    used_llm: bool


class EmbedResponse(BaseModel):
    """Detailed response returned by POST /embed."""

    status: Literal["success", "partial_success", "failed"]
    message: str
    total_files: int = Field(..., ge=0)
    processed_files: int = Field(..., ge=0)
    failed_files: int = Field(..., ge=0)
    total_chunks: int = Field(..., ge=0)
    total_embeddings: int = Field(..., ge=0)
    files: list[FileIndexingResult]


class ErrorResponse(BaseModel):
    """Standard error response shape for request-level failures."""

    detail: str
