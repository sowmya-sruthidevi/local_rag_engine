import logging

from app.config import settings
from app.llm_service import OllamaService
from app.prompt_builder import NOT_FOUND_ANSWER, build_prompt
from app.schemas import AskResponse
from app.vector_store import vector_store


logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, llm_service: OllamaService | None = None) -> None:
        self.vector_store = vector_store
        self.llm_service = llm_service or OllamaService()

    async def answer_question(self, question: str) -> AskResponse:
        logger.info("RAG question received: %s", question)

        self.vector_store.verify_ready()
        query_embedding = await self.llm_service.generate_embedding(question)

        retrieved_chunks = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=settings.retrieval_top_k,
            max_distance=settings.retrieval_max_distance,
        )

        similarity_scores: list[float] = []
        retrieved_chunk_texts: list[str] = []
        sources: list[str] = []
        seen_texts: set[str] = set()
        relevant_chunks: list[str] = []

        for chunk in retrieved_chunks:
            score = chunk.similarity_score or 0.0
            similarity_scores.append(score)
            retrieved_chunk_texts.append(chunk.text)
            if chunk.source not in sources:
                sources.append(chunk.source)

            if score >= settings.retrieval_similarity_threshold:
                normalized_text = chunk.text.strip().lower()
                if normalized_text not in seen_texts:
                    seen_texts.add(normalized_text)
                    relevant_chunks.append(chunk.text)

        answer = NOT_FOUND_ANSWER
        used_llm = False

        if relevant_chunks:
            prompt = build_prompt(question=question, chunks=relevant_chunks)
            answer = await self.llm_service.generate_answer(prompt)
            used_llm = True

        logger.info("RAG response prepared: used_llm=%s sources=%s", used_llm, sources)
        return AskResponse(
            question=question,
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved_chunk_texts,
            similarity_scores=similarity_scores,
            used_llm=used_llm,
        )


retrieval_service = RetrievalService()