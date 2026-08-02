# RAG Retrieval Service

This service adds a retrieval-only `/ask` endpoint for an existing ChromaDB index.
It does not rebuild the indexing pipeline and does not create document embeddings.

## Run

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

Set these environment variables if your existing index uses different names:

```powershell
$env:CHROMA_DB_PATH="C:\path\to\your\chroma_db"
$env:COLLECTION_NAME="documents"
$env:OLLAMA_BASE_URL="http://localhost:11434"
```

Both the Embedding Service and Retrieval Service must use the same values:

```env
CHROMA_DB_PATH=C:\Users\SRUTHI\Desktop\embedding\chroma_db
COLLECTION_NAME=document_embeddings
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

On startup the app prints the resolved ChromaDB path, collection name, and indexed
vector count so you can verify both services are pointing at the same database.

## Request

```json
{
  "question": "What is Docker?"
}
```

## Retrieval Pipeline

1. `routes.py` receives `POST /ask` and validates the JSON body with `AskRequest`.
2. `retrieval_service.py` logs the question and asks `llm_service.py` to embed only the user question with Ollama `nomic-embed-text`.
3. `vector_store.py` verifies the existing persistent ChromaDB collection exists and contains vectors before generating the query embedding.
4. `vector_store.py` performs a top 4 similarity search with the query embedding.
5. `prompt_builder.py` builds a grounded prompt from the retrieved chunks.
6. `llm_service.py` sends the prompt to Ollama using `tinyllama`.
7. The API returns the original question, TinyLlama answer, and unique source filenames from the retrieved chunk metadata.

## Error Handling

- Empty ChromaDB collection: returns `{"detail":"The vector database is empty. Please upload and index documents."}`.
- No relevant chunks after optional filtering: returns the standard not-found answer with no sources.
- Missing Chroma collection: returns `{"detail":"No indexed documents found. Please index documents first."}`.
- Ollama unavailable: returns HTTP 503.
- TinyLlama or embedding failure: returns HTTP 500.
- Invalid request body: FastAPI returns HTTP 422.

## Why Collection Errors Happen

ChromaDB stores vectors under a persistent path and collection name. If indexing
writes to one path or collection while retrieval reads another, retrieval opens a
different database and cannot see the indexed vectors.

In this setup the Embedding Service is using:

```text
C:\Users\SRUTHI\Desktop\embedding\chroma_db
```

with collection:

```text
document_embeddings
```

The Retrieval Service must use those exact same values. It verifies the
collection before searching and never creates a retrieval collection.
