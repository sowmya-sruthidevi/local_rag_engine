from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.chunking import split_pages_into_chunks
from app.config import settings
from app.document_loader import (
    CorruptedDocumentError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text_by_page,
    validate_supported_file,
)
from app.embedding_service import (
    EmbeddingGenerationError,
    OllamaUnavailableError as EmbeddingOllamaUnavailableError,
    embedding_service,
)
from app.llm_service import LLMGenerationError, OllamaUnavailableError as RagOllamaUnavailableError
from app.retrieval_service import retrieval_service
from app.schemas import AskRequest, AskResponse, EmbedResponse, FileIndexingResult
from app.utils import get_logger, save_upload_file
from app.vector_store import ChromaStorageError, ChromaStoreEmptyError, vector_store

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/embed",
    response_model=EmbedResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Index uploaded documents into ChromaDB",
)
async def embed_documents(files: list[UploadFile] = File(...)) -> EmbedResponse:
    """
    Process uploaded documents end to end:
    save files, load text, split chunks, generate embeddings, and store vectors.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents uploaded.")

    settings.documents_dir.mkdir(parents=True, exist_ok=True)

    file_results: list[FileIndexingResult] = []
    total_chunks = 0
    total_embeddings = 0

    for uploaded_file in files:
        filename = Path(uploaded_file.filename or "").name
        logger.info("Starting indexing for file: %s", filename or "<missing filename>")

        try:
            # Validate and save the uploaded file before loading its content.
            validate_supported_file(filename)
            saved_path = await save_upload_file(uploaded_file, settings.documents_dir)

            # Load text from the saved document. PDF pages retain page numbers.
            pages = extract_text_by_page(saved_path)

            # Split extracted text into overlapping chunks suitable for embedding.
            chunks = split_pages_into_chunks(
                pages=pages,
                document_name=filename,
                source_id=saved_path.stem,
            )
            if not chunks:
                raise EmptyDocumentError(f"Document '{filename}' did not produce any chunks.")

            # Generate one Ollama embedding vector for every chunk.
            embeddings = await embedding_service.embed_texts(
                [str(chunk["text"]) for chunk in chunks]
            )

            # Persist chunk text, vectors, and metadata in local ChromaDB.
            vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

            chunks_created = len(chunks)
            embeddings_created = len(embeddings)
            total_chunks += chunks_created
            total_embeddings += embeddings_created

            file_results.append(
                FileIndexingResult(
                    filename=filename,
                    status="success",
                    chunks_created=chunks_created,
                )
            )
            logger.info(
                "Indexed file successfully: %s chunks=%s embeddings=%s",
                filename,
                chunks_created,
                embeddings_created,
            )
        except (
            UnsupportedFileTypeError,
            EmptyDocumentError,
            CorruptedDocumentError,
            EmbeddingOllamaUnavailableError,
            EmbeddingGenerationError,
            ChromaStorageError,
            HTTPException,
        ) as exc:
            error_message = _error_message(exc)
            logger.warning("Indexing failed for file %s: %s", filename or "<unknown>", error_message)
            file_results.append(
                FileIndexingResult(
                    filename=filename or "unknown",
                    status="failed",
                    chunks_created=0,
                    error=error_message,
                )
            )
        except Exception as exc:
            logger.exception("Unexpected indexing failure for file %s", filename or "<unknown>")
            file_results.append(
                FileIndexingResult(
                    filename=filename or "unknown",
                    status="failed",
                    chunks_created=0,
                    error=f"Unexpected indexing failure: {exc}",
                )
            )

    processed_files = sum(1 for result in file_results if result.status == "success")
    failed_files = len(file_results) - processed_files

    response_status, message = _response_status_and_message(processed_files, failed_files)

    return EmbedResponse(
        status=response_status,
        message=message,
        total_files=len(files),
        processed_files=processed_files,
        failed_files=failed_files,
        total_chunks=total_chunks,
        total_embeddings=total_embeddings,
        files=file_results,
    )


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Answer a question using indexed document chunks",
)
async def ask_question(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must not be empty.",
        )

    try:
        return await retrieval_service.answer_question(question)
    except ChromaStoreEmptyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RagOllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama server is unavailable. Make sure Ollama is running.",
        ) from exc
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


def _error_message(exc: Exception) -> str:
    """Normalize expected exceptions into readable API error messages."""
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    return str(exc)


def _response_status_and_message(
    processed_files: int,
    failed_files: int,
) -> tuple[str, str]:
    """Build the top-level indexing status and message from file outcomes."""
    if processed_files > 0 and failed_files == 0:
        return "success", "Documents indexed successfully."
    if processed_files > 0 and failed_files > 0:
        return "partial_success", "Some documents were indexed successfully, and some failed."
    return "failed", "No documents were indexed successfully."
