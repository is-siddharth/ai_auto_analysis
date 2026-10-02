import pandas as pd

from src.profiling.classifier import classify_columns
from src.interpretation.dictionary import (
    build_data_dictionary,
    identify_analytical_fields,
)
from src.analysis.recommendations import (
    generate_analysis_questions,
)


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