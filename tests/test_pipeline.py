import pandas as pd

from src.profiling.classifier import classify_columns
from src.interpretation.dictionary import (
    build_data_dictionary,
    identify_analytical_fields,
)
from src.analysis.recommendations import (
    generate_analysis_questions,
)
from src.pipeline import analyze_dataframe


def test_pipeline_components_handle_ambiguous_dataset():
    """
    Simulates a dataset whose column meanings are not obvious.
    """

    df = pd.DataFrame(
        {
            "cust_segment_cd": ["A", "B", None, "A"],
            "rev_amt": [100.0, 200.0, None, 150.0],
            "event_dt": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-04",
                ]
            ),
            "response_text": [
                "Good",
                "Average",
                None,
                "Poor",
            ],
        }
    )

    classification = classify_columns(df)

    assert len(classification) == 4
    assert "Column" in classification.columns

    dictionary = build_data_dictionary(
        df,
        classification,
    )

    assert len(dictionary) == 4

    fields = identify_analytical_fields(
        classification
    )

    recommendations = generate_analysis_questions(
        df,
        fields,
    )

    assert isinstance(
        recommendations,
        pd.DataFrame,
    )

def test_pipeline_returns_cleaning_recommendations_without_modifying_data():
    df = pd.DataFrame({
        "Customer ID": ["C1", "C1", "C2"],
        "Segment": ["Retail ", "Retail ", "Corporate"],
        "Sales": [100.0, 100.0, 200.0],
    })
    result = analyze_dataframe(df, include_semantic=False)
    assert "cleaning_recommendations" in result
    assert not result["cleaning_recommendations"].empty
    assert len(result["data"]) == 3
    assert df.loc[0, "Segment"] == "Retail "


def test_pipeline_builds_dataset_context_without_semantic_ai():
    import pandas as pd
    from src.pipeline import analyze_dataframe

    df = pd.DataFrame({"Category": ["A", "B"], "Sales": [10, 20]})
    result = analyze_dataframe(df, include_semantic=False)
    assert result["dataset_context"]["dataset"]["rows"] == 2
    assert result["dataset_context"]["dataset"]["columns"] == 2
