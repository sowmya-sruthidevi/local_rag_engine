import logging
from typing import List

import requests

from config import (
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class OllamaUnavailableError(Exception):
    """Raised when the Ollama server cannot be reached."""


class LLMGenerationError(Exception):
    """Raised when TinyLlama cannot generate a response."""


class OllamaService:
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        llm_model: str = LLM_MODEL,
        timeout: float = OLLAMA_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.timeout = timeout

    def generate_embedding(self, text: str) -> List[float]:
        """Generate one query embedding with Ollama. Documents are never re-embedded here."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embedding_model, "input": text},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise OllamaUnavailableError("Ollama server is unavailable.") from exc

        if response.status_code >= 500:
            raise OllamaUnavailableError("Ollama server is unavailable.")

        if response.status_code >= 400:
            raise LLMGenerationError(
                f"Ollama embedding request failed: {response.text}"
            )

        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings or not isinstance(embeddings[0], list):
            raise LLMGenerationError("Ollama did not return valid embeddings.")

        logger.info("Query embedding generated")
        return embeddings[0]

    def generate_answer(self, prompt: str) -> str:
        """Generate a grounded answer using TinyLlama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Lower temp for less creative, more deterministic answers
                        "top_p": 0.1,
                        "top_k": 1,
                    },
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise OllamaUnavailableError("Ollama server is unavailable.") from exc

        if response.status_code >= 500:
            raise OllamaUnavailableError("Ollama server is unavailable.")

        if response.status_code >= 400:
            raise LLMGenerationError(
                f"TinyLlama generation failed: {response.text}"
            )

        payload = response.json()
        answer = payload.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise LLMGenerationError("TinyLlama returned an empty response.")

        logger.info("TinyLlama response received")
        return answer.strip()
