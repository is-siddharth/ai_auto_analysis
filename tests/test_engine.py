import pandas as pd

from src.analysis.engine import run_analysis


def test_overall_profile_is_supported():
    df = pd.DataFrame({"Revenue": [100, 200, 300]})

    result = run_analysis(
        df,
        {
            "Analysis Type": "Overall Profile",
            "Measure": "Revenue",
            "Dimension": None,
            "Date Column": None,
        },
    )

    assert not result["table"].empty
    assert "Total" in result["table"]["Metric"].tolist()


def test_time_trend_uses_date_column():
    df = pd.DataFrame(
        {
            "Order Date": pd.to_datetime(
                ["2025-01-01", "2025-02-01"]
            ),
            "Revenue": [100, 200],
        }
    )

    result = run_analysis(
        df,
        {
            "Analysis Type": "Time Trend",
            "Measure": "Revenue",
            "Dimension": None,
            "Date Column": "Order Date",
        },
    )

    assert result["x"] == "Order Date"
    assert result["y"] == "Total"
    assert len(result["table"]) == 2


def test_rate_profile_does_not_sum_rate():
    df = pd.DataFrame({"Conversion Rate": [0.1, 0.2, 0.3]})

    result = run_analysis(
        df,
        {
            "Analysis Type": "Rate Profile",
            "Measure": "Conversion Rate",
            "Dimension": None,
            "Date Column": None,
        },
    )

    metrics = result["table"]["Metric"].tolist()
    assert "Average" in metrics
    assert "Total" not in metrics


def test_distribution_and_outliers_uses_iqr():
    from src.analysis.engine import run_analysis

    df = pd.DataFrame({"Sales": [10, 11, 12, 13, 14, 15, 100]})
    result = run_analysis(
        df,
        {
            "Analysis Type": "Distribution & Outliers",
            "Measure": "Sales",
            "Dimension": None,
            "Date Column": None,
        },
    )
    assert result["chart_type"] == "box"
    assert int(result["table"].loc[result["table"]["Metric"] == "Potential Outliers", "Value"].iloc[0]) == 1
