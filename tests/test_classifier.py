import pandas as pd

from src.profiling.classifier import classify_columns


def test_classifier_returns_expected_schema():
    df = pd.DataFrame(
        {
            "Customer ID": ["C1", "C2", "C3"],
            "Sales": [100, 200, 300],
            "City": ["Delhi", "Mumbai", "Delhi"],
            "Order Date": pd.to_datetime(
                [
                    "2025-01-01",
                    "2025-01-02",
                    "2025-01-03",
                ]
            ),
        }
    )

    result = classify_columns(df)

    expected_columns = {
        "Column",
        "Classification",
        "Data Type",
        "Unique Values",
        "Missing Values",
        "Unique Ratio",
    }

    assert expected_columns.issubset(set(result.columns))
    assert len(result) == 4


def test_classifier_handles_empty_dataframe():
    result = classify_columns(pd.DataFrame())

    assert isinstance(result, pd.DataFrame)
    assert "Column" in result.columns
    assert len(result) == 0


def test_classifier_handles_unusual_columns():
    df = pd.DataFrame(
        {
            "cust_segment_cd": ["A", "B", "A"],
            "rev_amt": [100.0, 200.0, 150.0],
            "some_weird_field": ["x", "y", "z"],
        }
    )

    result = classify_columns(df)

    assert len(result) == 3
    assert result["Column"].tolist() == [
        "cust_segment_cd",
        "rev_amt",
        "some_weird_field",
    ]


def test_numeric_id_is_not_measure():
    df = pd.DataFrame(
        {
            "Customer ID": [1001, 1002, 1003],
            "Revenue": [100, 200, 300],
        }
    )

    result = classify_columns(df)
    classifications = dict(
        zip(result["Column"], result["Classification"])
    )

    assert classifications["Customer ID"] == "Potential ID"
    assert classifications["Revenue"] == "Numerical Measure"


def test_special_numeric_roles_are_not_all_measures():
    df = pd.DataFrame(
        {
            "Age": [21, 32, 44],
            "Routine_Task_Percentage": [0.2, 0.5, 0.8],
            "Satisfaction Score": [2, 4, 5],
            "Revenue": [100, 200, 300],
            "Human_Interaction_Level": ["Low", "Medium", "High"],
        }
    )

    result = classify_columns(df)
    classifications = dict(
        zip(result["Column"], result["Classification"])
    )

    assert classifications["Age"] == "Numerical Attribute"
    assert classifications["Routine_Task_Percentage"] == "Rate / Percentage"
    assert classifications["Satisfaction Score"] == "Score / Rating"
    assert classifications["Revenue"] == "Numerical Measure"
    assert classifications["Human_Interaction_Level"] == "Ordinal"
