# Embedding + Indexing + RAG Project

This repository contains a complete document question-answering system built with FastAPI, Ollama, and ChromaDB.

It includes:


- Document ingestion and indexing (PDF, DOCX, TXT)
- Embedding generation and vector storage
- Retrieval-Augmented Generation (RAG) question answering
- A standalone retrieval-only service variant

## Tech Stack

- Python 3.11+
- FastAPI
- Ollama
- ChromaDB
- LangChain text splitters
- pypdf
- python-docx

## Repository Layout

```text
embedding/
├── app/                    # Combined service: indexing + /ask RAG
├── indexing/               # Retrieval-only service (legacy/separate flow)
├── documents/              # Uploaded files saved here
├── chroma_db/              # Main persistent vector database
├── requirements.txt        # Dependencies for app/
├── README.md               # Project-level documentation (this file)
```

## Folder Roles

### app/

Primary service for the whole project.

- `POST /embed`: upload, parse, chunk, embed, and store vectors
- `POST /ask`: retrieve relevant chunks and generate grounded answers

Use this when you want one API that handles the full pipeline end to end.

### indexing/

Retrieval-only service variant.

- Exposes `POST /ask`
- Assumes documents are already indexed in ChromaDB

Use this if indexing and retrieval are run as separate services.

## Recommended Way To Run (Full Project)

This is the common flow for the entire project.

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Pull Ollama models:

```powershell
ollama pull nomic-embed-text
ollama pull tinyllama
```

3. Start Ollama:

```powershell
ollama serve
```

4. Start the combined API:

```powershell
python -m uvicorn app.main:app --reload
```

5. Open docs:

```text
http://127.0.0.1:8000/docs
```

## Currently Running Services

When the application is fully started, the following services are active:

| Service | Port | Default PID | Command |
|---|---|---|---|
| **Ollama Server** | `11434` | 18064 | `ollama serve` |
| **FastAPI App (Uvicorn)** | `8000` | 13492 | `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |

## Complete Setup & Run Commands (PowerShell)

Execute these commands in order from the project root directory.

### Step 1 — Install Dependencies

```powershell
pip install -r embedding\requirements.txt
```

### Step 2 — Download Required Ollama Models (one-time)

```powershell
ollama pull nomic-embed-text
ollama pull tinyllama
```

Optional extra model:
```powershell
ollama pull phi
```

### Step 3 — Start Ollama Server (Terminal #1)

Keep this terminal open and running:

```powershell
ollama serve
```

### Step 4 — Start the FastAPI Application (Terminal #2)

#### Option A: Run from the `embedding\` directory (with PYTHONPATH):

```powershell
cd embedding
$env:PYTHONPATH='C:\Users\SRUTHI\Desktop\project\local_rag_engine\embedding'
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Option B: Run from project root (no PYTHONPATH needed):

```powershell
python -m uvicorn embedding.app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Option C: Bash / cross-platform from `embedding/` folder:

```bash
export PYTHONPATH="$(pwd)"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 5 — Verification Commands

Check if the application is healthy:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```

List available Ollama models:

```powershell
ollama list
```

Check which services are listening on expected ports:

```powershell
netstat -ano | findstr /R "8000 11434"
```

Bash / curl health check:

```bash
curl http://127.0.0.1:8000/health
# expected: {"status":"ok"}
```

## Access Points After Running

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000 | API root status |
| http://127.0.0.1:8000/health | Health check endpoint |
| **http://127.0.0.1:8000/docs** | **Swagger UI — interactive API playground** |
| http://127.0.0.1:8000/redoc | ReDoc styled API documentation |
| http://127.0.0.1:11434 | Ollama raw API endpoint |

## Developer run commands (commands I used)

The following are the exact commands I ran to get the service running locally.

- PowerShell (from repo root):

```powershell
pip install -r embedding/requirements.txt
ollama pull nomic-embed-text
ollama pull tinyllama
ollama serve
# If you see "No module named 'app'", set PYTHONPATH to the embedding folder:
$env:PYTHONPATH='C:\Users\SRUTHI\Desktop\project\local_rag_engine\embedding'
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- From the repository root (cross-platform):

```bash
python -m uvicorn embedding.app.main:app --reload --host 127.0.0.1 --port 8000
```

- If you run from inside the `embedding/` folder (bash):

```bash
# export PYTHONPATH to the current folder, then run the app module
export PYTHONPATH="$(pwd)"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Quick health-check:

```bash
curl http://127.0.0.1:8000/health
# expected: {"status":"ok"}
```

Note: Ollama models (`nomic-embed-text`, `tinyllama`) are required for embedding and LLM calls. If you don't use Ollama, update the app configuration accordingly.

Note: There is no top-level `app.py`; run with `uvicorn app.main:app`.

## End-to-End Workflow

1. Upload documents using `POST /embed`
2. Text is extracted and chunked
3. Embeddings are generated and stored in ChromaDB
4. Ask questions using `POST /ask`
5. The app retrieves top-matching chunks and sends grounded context to the LLM
6. The answer is returned with source metadata

## API Summary (Combined app/ Service)

- `GET /` : service status
- `GET /health` : health check
- `POST /embed` : index uploaded documents
- `POST /ask` : answer questions from indexed content

### Example: Embed

```powershell
curl -X POST "http://127.0.0.1:8000/embed" `
  -F "files=@sample.pdf"
```

### Example: Ask

```powershell
curl -X POST "http://127.0.0.1:8000/ask" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What is this document about?\"}"
```

## Configuration

Main environment variables:

```text
CHROMA_DB_PATH=chroma_db
COLLECTION_NAME=document_embeddings
OLLAMA_LLM_MODEL=tinyllama
RETRIEVAL_TOP_K=4
RETRIEVAL_SIMILARITY_THRESHOLD=0.5
RETRIEVAL_MAX_DISTANCE=
```

App-prefixed settings are also supported:

```text
EMBEDDING_SERVICE_DOCUMENTS_DIR=documents
EMBEDDING_SERVICE_CHROMA_DB_DIR=chroma_db
EMBEDDING_SERVICE_CHROMA_COLLECTION_NAME=document_embeddings
EMBEDDING_SERVICE_OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_SERVICE_OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_SERVICE_CHUNK_SIZE=1000
EMBEDDING_SERVICE_CHUNK_OVERLAP=200
```

## Important For Dual-Folder Setup

If you run `indexing/` and `app/` separately, both must point to the same:

- ChromaDB path
- Collection name
- Embedding model

Otherwise retrieval may not find indexed vectors.

## Error Handling

The services handle:

- Unsupported file types
- Empty/corrupted documents
- Empty vector store
- Ollama unavailable
- Embedding/generation failures
- ChromaDB storage errors
