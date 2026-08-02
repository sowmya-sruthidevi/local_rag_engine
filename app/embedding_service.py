import httpx

from app.config import settings


class OllamaUnavailableError(ConnectionError):
    """Raised when the Ollama server cannot be reached."""


class EmbeddingGenerationError(RuntimeError):
    """Raised when Ollama fails to generate embeddings."""


class OllamaEmbeddingService:
    """Client for generating embeddings with Ollama's embedding API."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate one embedding vector for each text chunk."""
        if not texts:
            return []

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
        except httpx.RequestError as exc:
            raise OllamaUnavailableError(
                f"Ollama server is unavailable at {self.base_url}."
            ) from exc

        if response.status_code >= 500:
            raise OllamaUnavailableError(
                f"Ollama server returned status {response.status_code}."
            )

        if response.status_code >= 400:
            raise EmbeddingGenerationError(
                f"Ollama embedding request failed with status {response.status_code}: {response.text}"
            )

        payload = response.json()
        embeddings = payload.get("embeddings")

        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingGenerationError("Ollama returned an invalid embeddings response.")

        return embeddings


embedding_service = OllamaEmbeddingService(
    base_url=settings.ollama_base_url,
    model=settings.ollama_embedding_model,
)
