from typing import List

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Question to answer using the uploaded document chunks.",
    )


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    retrieved_chunks: List[str]
    similarity_scores: List[float]
    used_llm: bool


class ErrorResponse(BaseModel):
    detail: str
