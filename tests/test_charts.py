import pandas as pd

from src.analysis.charts import recommend_charts


def test_chart_recommendation_matches_analysis_type():
    df = pd.DataFrame([
        {"Question": "How did sales change?", "Analysis Type": "Time Trend"}
    ])
    result = recommend_charts(df)
    assert result.iloc[0]["Recommended Chart"] == "Line Chart"
    assert "time" in result.iloc[0]["Why This Chart"].lower()
