import pandas as pd


CHART_RULES = {
    "Dimension Comparison": ("Bar Chart", "Compare groups across a categorical dimension; bars make differences easy to read."),
    "Ranking": ("Horizontal Bar Chart", "Ranking is easiest to scan when categories are ordered from largest to smallest."),
    "Contribution": ("Column Chart", "Shows the relative contribution of groups while keeping exact comparisons possible."),
    "Time Trend": ("Line Chart", "A line chart makes movement and direction across time visible."),
    "Rate Trend": ("Line Chart", "A line chart shows how a rate changes over time without treating it as additive."),
    "Score Trend": ("Line Chart", "A line chart makes changes in an average score over time easy to follow."),
    "Attribute Comparison": ("Column Chart", "Grouped numeric ranges allow comparison of an outcome across attribute bands."),
    "Ordinal Comparison": ("Column Chart", "Ordered categories can be compared while preserving their natural sequence."),
    "Boolean Comparison": ("Column Chart", "Two-state categories are naturally compared with simple bars."),
    "Geographic Comparison": ("Bar Chart", "A bar chart gives a clear comparison when a geographic field is represented as categories."),
    "Attribute Distribution": ("Histogram", "A histogram shows the shape and spread of a numerical attribute."),
    "Rate Profile": ("Histogram", "A histogram shows the distribution of rates without implying that rates should be summed."),
    "Score Profile": ("Column Chart", "A score-frequency view helps reveal concentration across rating values."),
}


def recommend_charts(analysis_questions):
    """Attach chart recommendations to the existing analysis recommendations."""
    if analysis_questions is None or not isinstance(analysis_questions, pd.DataFrame):
        return pd.DataFrame(columns=[
            "Analysis Index", "Question", "Analysis Type", "Recommended Chart", "Why This Chart", "Placement Role"
        ])

    rows = []
    for index, row in analysis_questions.reset_index(drop=True).iterrows():
        analysis_type = row.get("Analysis Type")
        chart, reason = CHART_RULES.get(
            analysis_type,
            ("Table", "A table is safer than forcing a chart when the analysis is primarily descriptive."),
        )
        if analysis_type in {"Overall Profile", "Semantic Interpretation", "Dataset Structure", "Time Coverage", "Text Exploration"}:
            chart = "Table / KPI"
            reason = "This output is primarily a summary or explanation; a KPI or table communicates it more directly than a chart."
        placement = "Main analysis area" if chart not in {"Table / KPI", "Table"} else "Supporting area"
        rows.append({
            "Analysis Index": index,
            "Question": row.get("Question"),
            "Analysis Type": analysis_type,
            "Recommended Chart": chart,
            "Why This Chart": reason,
            "Placement Role": placement,
        })

    return pd.DataFrame(rows)
