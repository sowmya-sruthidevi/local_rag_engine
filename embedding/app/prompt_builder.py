from collections.abc import Sequence


NOT_FOUND_ANSWER = "I could not find this information in the uploaded documents."


def build_prompt(question: str, chunks: Sequence[str]) -> str:
    """Build a grounded prompt that forces answers to come from retrieved context."""
    context = "\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())

    return f"""### System Prompt
You are a fact extractor. Your only job is to answer the QUESTION using only the CONTEXT. Do not add explanations or extra words. If the answer is not in the context, say "{NOT_FOUND_ANSWER}".

### Context
{context}

### Question
{question}

### Answer:
"""