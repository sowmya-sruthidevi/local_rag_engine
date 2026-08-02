from typing import Any

import httpx

from app.config import settings


class OllamaUnavailableError(ConnectionError):
    """Raised when the Ollama server cannot be reached."""


class LLMGenerationError(RuntimeError):
    """Raised when Ollama fails to generate an answer or embedding."""


class OllamaService:
    """Client for Ollama embeddings and answer generation."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.embedding_model = settings.ollama_embedding_model
        self.llm_model = settings.ollama_llm_model
        self.timeout = 60.0

    async def generate_embedding(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.embedding_model, "input": text},
                )
        except httpx.RequestError as exc:
            raise OllamaUnavailableError("Ollama server is unavailable.") from exc

        if response.status_code >= 500:
            raise OllamaUnavailableError("Ollama server is unavailable.")
        if response.status_code >= 400:
            raise LLMGenerationError(f"Ollama embedding request failed: {response.text}")

        payload: dict[str, Any] = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise LLMGenerationError("Ollama did not return valid embeddings.")

        first_embedding = embeddings[0]
        if not isinstance(first_embedding, list):
            raise LLMGenerationError("Ollama did not return valid embeddings.")

        return [float(value) for value in first_embedding]

    async def generate_answer(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.0,
                            "top_p": 0.1,
                            "top_k": 1,
                        },
                    },
                )
        except httpx.RequestError as exc:
            raise OllamaUnavailableError("Ollama server is unavailable.") from exc

        if response.status_code >= 500:
            raise OllamaUnavailableError("Ollama server is unavailable.")
        if response.status_code >= 400:
            raise LLMGenerationError(f"Ollama answer request failed: {response.text}")

        payload: dict[str, Any] = response.json()
        answer = payload.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise LLMGenerationError("Ollama returned an empty response.")

        return answer.strip()
