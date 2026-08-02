import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


def configure_logging() -> None:
    """Configure application logging once at startup."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-specific logger."""
    return logging.getLogger(name)


async def save_upload_file(uploaded_file: UploadFile, documents_dir: Path) -> Path:
    """Save an uploaded file with a unique local name inside the documents directory."""
    filename = Path(uploaded_file.filename or "").name
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is missing a filename.",
        )

    content = await uploaded_file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document '{filename}' is empty.",
        )

    documents_dir.mkdir(parents=True, exist_ok=True)
    saved_path = documents_dir / f"{uuid4().hex}_{filename}"
    saved_path.write_bytes(content)
    return saved_path
