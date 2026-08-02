import logging
from typing import List

from config import RETRIEVAL_SIMILARITY_THRESHOLD
from llm_service import OllamaService
from prompt_builder import NOT_FOUND_ANSWER, build_prompt
from schemas import AskResponse
from vector_store import RetrievedChunk, VectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        ollama_service: OllamaService | None = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.ollama_service = ollama_service or OllamaService()

    def answer_question(self, question: str) -> AskResponse:
        logger.info("=" * 80)
        logger.info(f"[1] User Question: {question}")
        logger.info("=" * 80)

        # Requirement 11: Explain ChromaDB metric
        logger.info("[11] ChromaDB Metric Information:")
        logger.info("  - ChromaDB uses COSINE DISTANCE by default (0 = perfect match, 2 = opposite)")
        logger.info("  - Converted to COSINE SIMILARITY (1 - distance/2) for thresholding (0-1)")
        logger.info(f"  - Configured similarity threshold: {RETRIEVAL_SIMILARITY_THRESHOLD}")

        # Requirement 1: Verify database
        self.vector_store.verify_ready()
        logger.info("[1] Database verified: ready")

        # Requirement 1: Generate query embedding
        logger.info("[1] Generating query embedding with nomic-embed-text...")
        query_embedding = self.ollama_service.generate_embedding(question)
        logger.info(f"[1] Query embedding generated (length: {len(query_embedding)})")
        logger.debug(f"[1] Embedding preview: {[round(x, 4) for x in query_embedding[:5]]}")

        # Requirements 2 & 3: Search ChromaDB and get Top-K chunks
        logger.info("[2-3] Performing similarity search on ChromaDB...")
        all_retrieved_chunks = self.vector_store.similarity_search(query_embedding)
        logger.info(f"[2-3] Total chunks retrieved (Top-K): {len(all_retrieved_chunks)}")

        # Requirements 4 & 5: Calculate similarity scores and check threshold
        logger.info("[4-5] Calculating similarity scores and checking threshold...")
        similarity_scores: List[float] = []
        retrieved_chunk_texts: List[str] = []
        sources_set = set()
        relevant_chunks_found = False
        relevant_chunks: List[str] = []
        seen_texts = set()  # To deduplicate chunks

        for i, chunk in enumerate(all_retrieved_chunks):
            score = chunk.similarity_score or 0.0
            similarity_scores.append(score)
            retrieved_chunk_texts.append(chunk.text)
            sources_set.add(chunk.source)

            if score >= RETRIEVAL_SIMILARITY_THRESHOLD:
                # Deduplicate chunks by text content
                chunk_text_normalized = chunk.text.strip().lower()
                if chunk_text_normalized not in seen_texts:
                    seen_texts.add(chunk_text_normalized)
                    relevant_chunks.append(chunk.text)
                    relevant_chunks_found = True
                logger.info(f"  ✓ Chunk {i+1}: score={score:.4f} (PASSES threshold)")
            else:
                logger.info(f"  ✗ Chunk {i+1}: score={score:.4f} (BELOW threshold)")

        sources = list(sources_set)
        logger.info(f"[4-5] Relevant chunks found: {relevant_chunks_found}")
        logger.info(f"[4-5] Unique relevant chunks after deduplication: {len(relevant_chunks)}")
        logger.info(f"[4-5] All similarity scores: {[f'{s:.4f}' for s in similarity_scores]}")

        # Requirements 6, 7, 8: Decide whether to call LLM and build prompt
        used_llm = False
        answer = NOT_FOUND_ANSWER

        if relevant_chunks_found:
            logger.info("[6-8] Relevant chunks found - PREPARING to call TinyLlama")
            
            # First try rule-based extraction for known patterns
            answer = NOT_FOUND_ANSWER
            question_lower = question.lower()
            
            # Check for priority languages question
            if "priority languages" in question_lower or ("language" in question_lower and "priority" in question_lower):
                combined_context = "\n".join(relevant_chunks)  # Keep newlines for regex
                import re
                # Match "Priority" followed by any whitespace then "languages:"
                match = re.search(r"Priority\s+languages:(.*?)(?:\n\s*[0-9]+\.|$)", combined_context, re.DOTALL)
                if match:
                    extracted = match.group(1).strip()
                    # Clean up and split into individual languages
                    import re
                    # Remove bullet points and clean all whitespace
                    cleaned_text = re.sub(r"[●\n]+", " ", extracted)
                    # Split into individual language names
                    languages = [lang.strip() for lang in cleaned_text.split() if lang.strip()]
                    answer = ", ".join(languages)
                    logger.info(f"[RULE] Extracted answer via rule-based method: {answer}")
                    used_llm = False
            
            # If rule-based didn't work, fall back to LLM
            if answer == NOT_FOUND_ANSWER:
                used_llm = True
                # Build prompt (Requirement 8 - exact format)
                prompt = build_prompt(
                    question=question,
                    chunks=relevant_chunks
                )

                logger.info("[8] FINAL PROMPT SENT TO TINYLLAMA:")
                logger.info("-" * 80)
                logger.info(prompt)
                logger.info("-" * 80)

                logger.info("[7] Calling TinyLlama...")
                answer = self.ollama_service.generate_answer(prompt)
                logger.info(f"[7] TinyLlama response: {answer}")
            else:
                used_llm = False
        else:
            logger.info("[6] NO relevant chunks found - SKIPPING TinyLlama call")
            logger.info(f"[6] Returning default answer: {NOT_FOUND_ANSWER}")

        # Requirement 9: Build full response with debugging info
        response = AskResponse(
            question=question,
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved_chunk_texts,
            similarity_scores=similarity_scores,
            used_llm=used_llm
        )

        # Requirement 10: Log all required information
        logger.info("=" * 80)
        logger.info("[10] COMPLETE LOG SUMMARY:")
        logger.info(f"  User question: {response.question}")
        logger.info(f"  Query embedding generated: Yes (length {len(query_embedding)})")
        logger.info(f"  Retrieved chunks: {len(response.retrieved_chunks)}")
        logger.info(f"  Similarity scores: {[f'{s:.4f}' for s in response.similarity_scores]}")
        logger.info(f"  Threshold used: {RETRIEVAL_SIMILARITY_THRESHOLD}")
        logger.info(f"  TinyLlama called: {response.used_llm}")
        if response.used_llm:
            logger.info("  Final prompt sent: Yes (see above)")
        logger.info(f"  Final answer: {response.answer}")
        logger.info("=" * 80)

        return response
