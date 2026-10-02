import pandas as pd

from src.interpretation.dictionary import (
    build_data_dictionary,
    identify_analytical_fields,
)


def test_dictionary_handles_valid_classification():
    df = pd.DataFrame(
        {
            "Customer ID": ["C1", "C2"],
            "Sales": [100, 200],
        }
    )

    classification = pd.DataFrame(
        {
            "Column": [
                "Customer ID",
                "Sales",
            ],
            "Classification": [
                "Potential ID",
                "Numerical Measure",
            ],
        }
    )

    result = build_data_dictionary(
        df,
        classification,
    )

    assert len(result) == 2
    assert "Column" in result.columns
    assert "Description" in result.columns


def test_dictionary_does_not_crash_when_classification_is_empty():
    df = pd.DataFrame(
        {
            "A": [1, 2, 3],
            "B": ["x", "y", "z"],
        }
    )

    classification = pd.DataFrame()

    result = build_data_dictionary(
        df,
        classification,
    )

    assert len(result) == 2
    assert set(result["Classification"]) == {
        "Unclassified"
    }


def test_dictionary_handles_missing_column_field():
    df = pd.DataFrame(
        {
            "A": [1, 2, 3],
        }
    )

    classification = pd.DataFrame(
        {
            "WrongColumn": ["A"],
            "Classification": ["Numerical Measure"],
        }
    )

    result = build_data_dictionary(
        df,
        classification,
    )

    assert len(result) == 1
    assert result.iloc[0]["Column"] == "A"
    assert result.iloc[0]["Classification"] == "Unclassified"


def test_analytical_fields_are_safe():
    classification = pd.DataFrame()

    result = identify_analytical_fields(
        classification
    )

    assert result["ids"] == []
    assert result["dates"] == []
    assert result["measures"] == []
    assert result["dimensions"] == []
    assert result["unclassified"] == []