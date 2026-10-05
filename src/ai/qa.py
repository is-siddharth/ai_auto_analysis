import json

from src.ai.llm import ask_dataset_question


def ask_question(dataset_context, question):
    """Answer a user question using only the compact dataset context."""
    if not question or not question.strip():
        raise ValueError("Please enter a question about the dataset.")
    return ask_dataset_question(dataset_context, question.strip())
