import pandas as pd

from src.ai import llm
from src.ai.qa import ask_question


def test_ask_question_rejects_empty_question():
    try:
        ask_question({"dataset": {"rows": 1}}, "")
    except ValueError as exc:
        assert "question" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for an empty question")


def test_ask_dataset_question_uses_llm_response(monkeypatch):
    class FakeMessage:
        content = "This dataset contains sales records."

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **kwargs):
            return type("Response", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "get_client", lambda: FakeClient())
    monkeypatch.setattr(llm, "get_model_name", lambda: "test-model")

    result = ask_question(
        {"dataset": {"rows": 3, "columns": 2}, "columns": [{"name": "Sales"}]},
        "What is this dataset about?",
    )

    assert result["success"] is True
    assert result["answer"] == "This dataset contains sales records."
    assert result["model"] == "test-model"


def test_semantic_interpretation_falls_back_without_llm(monkeypatch):
    def fail_client():
        raise RuntimeError("HF unavailable")

    monkeypatch.setattr(llm, "get_client", fail_client)
    result = llm.interpret_dataset({
        "dataset": {"rows": 10, "columns": 2},
        "columns": [
            {"name": "Sales", "classification": "Numerical Measure", "sample_values": [10, 20]},
            {"name": "Region", "classification": "Categorical Dimension", "sample_values": ["East"]},
        ],
        "deterministic_recommendations": [],
    })

    assert result["success"] is False
    assert result["data"]["dataset_summary"]
    assert len(result["data"]["important_fields"]) == 2


def test_question_answer_falls_back_without_llm(monkeypatch):
    def fail_client():
        raise RuntimeError("HF unavailable")

    monkeypatch.setattr(llm, "get_client", fail_client)
    result = llm.ask_dataset_question({
        "dataset": {"rows": 10, "columns": 2},
        "columns": [
            {"name": "Sales", "classification": "Numerical Measure", "sample_values": [10, 20]},
            {"name": "Region", "classification": "Categorical Dimension", "sample_values": ["East"]},
        ],
        "quality_summary": {"Total Missing Values": 0, "Duplicate Rows": 0},
    }, "What is this dataset about?")

    assert result["success"] is False
    assert "10" in result["answer"]
