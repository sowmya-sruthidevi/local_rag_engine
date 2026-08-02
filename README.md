# Embedding and RAG Service

A production-ready FastAPI service for document ingestion and retrieval-augmented generation.

The service now performs both indexing and answering:

- Upload documents.
- Extract text.
- Split text into chunks.
- Generate embeddings with Ollama `nomic-embed-text`.
- Store chunks, vectors, and metadata in persistent ChromaDB.
- Retrieve relevant chunks for a question.
- Build a grounded prompt.
- Generate a final answer with Ollama `tinyllama`.

## Tech Stack

- Python 3.11+
- FastAPI
- Ollama
- `nomic-embed-text`
- ChromaDB
- LangChain `RecursiveCharacterTextSplitter`
- `pypdf`
- `python-docx`

## Project Structure

```text
project/
├── app/
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── config.py
│   ├── document_loader.py
│   ├── chunking.py
│   ├── embedding_service.py
│   ├── llm_service.py
│   ├── prompt_builder.py
│   ├── retrieval_service.py
│   ├── vector_store.py
│   └── utils.py
├── documents/
├── chroma_db/
├── requirements.txt
├── README.md
└── .gitignore
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Ollama and download the embedding and chat models:

```bash
ollama pull nomic-embed-text
ollama pull tinyllama
ollama serve
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

Swagger UI should show:

- `GET /`
- `POST /embed`
- `POST /ask`

## Endpoint

### POST /embed

Accepts multiple files using multipart form data field name `files`.

Supported formats:

- PDF
- DOCX
- TXT

Example:

```bash
curl -X POST "http://127.0.0.1:8000/embed" \
  -F "files=@docker.pdf" \
  -F "files=@python.docx" \
  -F "files=@rag_notes.txt"
```

Successful response:

```json
{
  "status": "success",
  "message": "All documents were indexed successfully.",
  "total_files": 3,
  "processed_files": 3,
  "failed_files": 0,
  "total_chunks": 148,
  "total_embeddings": 148,
  "files": [
    {
      "filename": "docker.pdf",
      "status": "success",
      "chunks_created": 42
    },
    {
      "filename": "python.docx",
      "status": "success",
      "chunks_created": 58
    },
    {
      "filename": "rag_notes.txt",
      "status": "success",
      "chunks_created": 48
    }
  ]
}
```

Partial success response:

```json
{
  "status": "partial_success",
  "message": "Some documents were indexed successfully, and some failed.",
  "total_files": 2,
  "processed_files": 1,
  "failed_files": 1,
  "total_chunks": 42,
  "total_embeddings": 42,
  "files": [
    {
      "filename": "docker.pdf",
      "status": "success",
      "chunks_created": 42
    },
    {
      "filename": "broken.pdf",
      "status": "failed",
      "chunks_created": 0,
      "error": "Could not parse 'broken.pdf'."
    }
  ]
}
```

## Indexing Pipeline

### 1. Document Upload

The `/embed` endpoint accepts one or more uploaded files. Each file is validated by extension and saved in the local `documents/` folder with a unique prefix so repeated filenames do not overwrite each other.

### 2. Document Loading

The service loads each saved document based on its file type:

- PDF files are loaded page by page with `pypdf`.
- DOCX files are loaded with `python-docx`.
- TXT files are loaded as UTF-8 text.

Each file is processed independently. A failed file is reported in the response without preventing other valid files from being indexed.

### 3. Text Extraction

Text is extracted from the loaded document. PDF page numbers are preserved when available. DOCX and TXT files are treated as single logical documents because reliable page numbers are not available without rendering the document.

Empty documents are skipped and reported as failed file entries.

### 4. Chunking

Extracted text is split with `RecursiveCharacterTextSplitter`.

Configuration:

```text
Chunk size: 1000 characters
Chunk overlap: 200 characters
```

Each chunk receives a unique chunk ID built from the saved document identifier, page marker, and chunk number.

### 5. Embedding Generation

The service calls Ollama's embedding API:

```text
http://localhost:11434/api/embed
```

Model:

```text
nomic-embed-text
```

One embedding vector is generated for every chunk.

### 6. Storing Embeddings in ChromaDB

ChromaDB uses a persistent local database at:

```text
chroma_db/
```

For every chunk, the service stores:

- Chunk text
- Embedding vector
- Filename
- Page number, if available
- Chunk ID

### POST /ask

Accepts a question and answers it from the indexed document chunks.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is Docker?\"}"
```

Successful response:

```json
{
  "question": "What is Docker?",
  "answer": "Docker is a platform for packaging and running applications in containers.",
  "sources": ["docker.pdf"],
  "retrieved_chunks": ["..."],
  "similarity_scores": [0.91],
  "used_llm": true
}
```

If the index is empty, the service returns a conflict response telling you to upload and index documents first.

## Retrieval Pipeline

1. `routes.py` receives `POST /ask` and validates the JSON body with `AskRequest`.
2. `retrieval_service.py` embeds the user question with Ollama `nomic-embed-text`.
3. `vector_store.py` performs a similarity search against the existing ChromaDB collection.
4. `prompt_builder.py` turns the retrieved chunks into a grounded prompt.
5. `llm_service.py` sends the prompt to Ollama using `tinyllama`.
6. The API returns the question, answer, sources, retrieved chunks, and similarity scores.

The database persists after server restarts.

## Configuration

Settings can be overridden with environment variables:

```text
EMBEDDING_SERVICE_DOCUMENTS_DIR=documents
EMBEDDING_SERVICE_CHROMA_DB_DIR=chroma_db
EMBEDDING_SERVICE_CHROMA_COLLECTION_NAME=document_embeddings
EMBEDDING_SERVICE_OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_SERVICE_OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_SERVICE_CHUNK_SIZE=1000
EMBEDDING_SERVICE_CHUNK_OVERLAP=200
OLLAMA_LLM_MODEL=tinyllama
RETRIEVAL_TOP_K=4
RETRIEVAL_SIMILARITY_THRESHOLD=0.5
```

## Error Handling

The service handles:

- Unsupported file type
- Empty document
- Corrupted document
- Ollama server unavailable
- Embedding generation failure
- ChromaDB storage failure

For upload-level problems, the API returns a request error. For per-file indexing problems, the API returns `partial_success` or `failed` with file-level error details.
