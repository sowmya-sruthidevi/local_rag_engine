import logging

from fastapi import APIRouter, HTTPException, status

from llm_service import LLMGenerationError, OllamaUnavailableError
from prompt_builder import NOT_FOUND_ANSWER
from retrieval_service import RetrievalService
from schemas import AskRequest, AskResponse
from vector_store import ChromaCollectionNotFoundError, ChromaStoreEmptyError

logger = logging.getLogger(__name__)

router = APIRouter()
retrieval_service = RetrievalService()


@router.post(
    "/ask",
    response_model=AskResponse,
    responses={
        422: {"description": "Invalid request"},
        500: {"description": "TinyLlama generation failed"},
        503: {"description": "Ollama server or Chroma collection unavailable"},
    },
)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must not be empty.",
        )

    try:
        return retrieval_service.answer_question(question)
    except ChromaStoreEmptyError:
        logger.warning("ChromaDB is empty")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The vector database is empty. Please upload and index documents.",
        )
    except ChromaCollectionNotFoundError as exc:
        logger.exception("Configured ChromaDB collection was not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OllamaUnavailableError as exc:
        logger.exception("Ollama server is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama server is unavailable. Make sure Ollama is running.",
        ) from exc
    except LLMGenerationError as exc:
        logger.exception("TinyLlama or embedding generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
