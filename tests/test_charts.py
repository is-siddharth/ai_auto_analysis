import pandas as pd

from src.analysis.charts import recommend_charts


def test_chart_recommendation_matches_analysis_type():
    df = pd.DataFrame([
        {"Question": "How did sales change?", "Analysis Type": "Time Trend"}
    ])
    result = recommend_charts(df)
    assert result.iloc[0]["Recommended Chart"] == "Line Chart"
    assert "time" in result.iloc[0]["Why This Chart"].lower()


def test_chart_recommendation_exposes_learning_choices():
    df = pd.DataFrame([
        {"Question": "How much does Category contribute?", "Analysis Type": "Contribution"}
    ])
    result = recommend_charts(df)
    assert "Donut Chart" in result.iloc[0]["Available Chart Choices"]
    assert result.iloc[0]["Recommended Chart"] == "Donut Chart"
