from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


def split_pages_into_chunks(
    pages: list[dict[str, int | str | None]],
    document_name: str,
    source_id: str | None = None,
) -> list[dict[str, int | str | None]]:
    """Split extracted document text into overlapping chunks with stable metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
    )

    chunks: list[dict[str, int | str | None]] = []
    chunk_number = 1
    chunk_id_prefix = source_id or document_name

    for page in pages:
        text = str(page["text"]).strip()
        if not text:
            continue

        for chunk_text in splitter.split_text(text):
            chunk_id = f"{chunk_id_prefix}:{page['page_number'] or 'document'}:{chunk_number}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "document_name": document_name,
                    "page_number": page["page_number"],
                }
            )
            chunk_number += 1

    return chunks
