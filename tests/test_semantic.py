import pandas as pd

from src.profiling.classifier import classify_columns
from src.profiling.quality import profile_data_quality
from src.interpretation.dictionary import (
    build_data_dictionary,
    identify_analytical_fields,
)
from src.analysis.recommendations import (
    generate_analysis_questions,
)
from src.interpretation.context import (
    build_dataset_context,
)


def test_dataset_context_builder():

    df = pd.DataFrame(
        {
            "Customer ID": [
                "C001",
                "C002",
                "C003",
            ],
            "Revenue": [
                100.0,
                200.0,
                150.0,
            ],
            "Region": [
                "North",
                "South",
                "North",
            ],
            "Order Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                ]
            ),
        }
    )

    classification = classify_columns(df)

    quality = profile_data_quality(df)

    dictionary = build_data_dictionary(
        df,
        classification,
    )

    fields = identify_analytical_fields(
        classification,
    )

    questions = generate_analysis_questions(
        df,
        fields,
    )

    context = build_dataset_context(
        df=df,
        classification=classification,
        quality=quality,
        data_dictionary=dictionary,
        analytical_fields=fields,
        analysis_questions=questions,
    )

    assert context["dataset"]["rows"] == 3
    assert context["dataset"]["columns"] == 4

    assert len(context["columns"]) == 4

    assert "Revenue" in context["dataset"]["column_names"]

    revenue_context = next(
        item
        for item in context["columns"]
        if item["name"] == "Revenue"
    )

    assert revenue_context["classification"] == (
        "Numerical Measure"
    )

    assert "numeric_summary" in revenue_context

    assert (
        revenue_context["numeric_summary"]["mean"]
        == 150.0
    )


def test_context_does_not_include_full_dataset():

    df = pd.DataFrame(
        {
            "Revenue": [100, 200, 300],
            "Region": ["A", "B", "C"],
        }
    )

    classification = classify_columns(df)

    fields = identify_analytical_fields(
        classification
    )

    context = build_dataset_context(
        df=df,
        classification=classification,
        analytical_fields=fields,
    )

    assert "data" not in context

    assert context["dataset"]["rows"] == 3