import pandas as pd

from src.analysis.recommendations import (
    generate_analysis_questions,
)


def test_recommendations_with_normal_dataset():
    df = pd.DataFrame(
        {
            "Sales": [100, 200, 300],
            "Category": ["A", "B", "A"],
        }
    )

    fields = {
        "measures": ["Sales"],
        "dimensions": ["Category"],
        "dates": [],
        "text": [],
        "ids": [],
        "boolean": [],
        "geographic": [],
        "unclassified": [],
    }

    result = generate_analysis_questions(
        df,
        fields,
    )

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "Question" in result.columns
    assert "Analysis Type" in result.columns


def test_recommendations_without_measures():
    df = pd.DataFrame(
        {
            "Category": ["A", "B", "A"],
            "Description": [
                "First item",
                "Second item",
                "Third item",
            ],
        }
    )

    fields = {
        "measures": [],
        "dimensions": ["Category"],
        "dates": [],
        "text": ["Description"],
        "ids": [],
        "boolean": [],
        "geographic": [],
        "unclassified": [],
    }

    result = generate_analysis_questions(
        df,
        fields,
    )

    assert isinstance(result, pd.DataFrame)
    assert not result.empty


def test_recommendations_with_empty_fields():
    df = pd.DataFrame(
        {
            "A": ["x", "y"],
            "B": ["z", "w"],
        }
    )

    result = generate_analysis_questions(
        df,
        {},
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == [
        "Question",
        "Analysis Type",
        "Measure",
        "Dimension",
        "Date Column",
        "Priority",
        "Rationale",
    ]