import pandas as pd

from src.profiling.quality import profile_data_quality


def test_quality_detects_multiple_anomaly_categories():
    df = pd.DataFrame(
        {
            "Customer ID": ["C1", "C1", None, "C4"],
            "Age": [25, 30, 250, -2],
            "Completion Percentage": [0.2, 0.5, 1.5, 0.8],
            "Segment": ["Retail", "retail", "Retail ", "Retail"],
            "Revenue": [100, 200, 300, 1000000],
        }
    )

    result = profile_data_quality(df)

    assert result["summary"]["Duplicate Rows"] == 0
    assert not result["missing"].empty
    assert not result["range_validation"].empty
    assert not result["categorical_consistency"].empty
    assert not result["identifier_integrity"].empty
    assert not result["outliers"].empty


def test_quality_handles_empty_dataframe():
    result = profile_data_quality(pd.DataFrame())

    assert result["summary"]["Rows"] == 0
    assert result["summary"]["Columns"] == 0
    assert result["missing"].empty
    assert result["numeric"].empty
