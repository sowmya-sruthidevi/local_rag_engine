from typing import Sequence


NOT_FOUND_ANSWER = "I could not find this information in the uploaded documents."


def build_prompt(question: str, chunks: Sequence[str]) -> str:
    """Build the grounded QA prompt sent to the language model (exact format per requirements)."""
    context = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())

    return f"""### System Prompt
You are a fact extractor. Your only job is to extract the EXACT answer from the CONTEXT. Do NOT add ANYTHING else, no explanations, no extra words. If the answer is not in CONTEXT, say "{NOT_FOUND_ANSWER}".

### Context
{context}

### Question
{question}

### Answer (only the facts, no extra words):"""
