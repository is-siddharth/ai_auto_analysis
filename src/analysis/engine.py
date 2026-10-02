import pandas as pd


AGGREGATABLE_TYPES = {
    "Overall Profile",
    "Dimension Comparison",
    "Ranking",
    "Contribution",
}


def _validate_column(df, column, label="Column"):
    if column not in df.columns:
        raise ValueError(f"{label} '{column}' was not found.")


def _validate_numeric(df, column, label="Field"):
    _validate_column(df, column, label)

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"'{column}' is not numeric.")


def _validate_measure(df, measure):
    _validate_numeric(df, measure, "Measure")


def _validate_dimension(df, dimension):
    _validate_column(df, dimension, "Dimension")


def _validate_date(df, date_column):
    _validate_column(df, date_column, "Date field")

    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        raise ValueError(f"'{date_column}' is not a datetime field.")


def _empty_result(columns=None):
    return {
        "table": pd.DataFrame(columns=columns or []),
        "chart_type": None,
    }


def _measure_overview(df, measure):
    _validate_measure(df, measure)

    series = pd.to_numeric(df[measure], errors="coerce").dropna()

    if series.empty:
        return _empty_result(["Metric", "Value"])

    result = pd.DataFrame(
        {
            "Metric": [
                "Total",
                "Average",
                "Minimum",
                "Maximum",
                "Median",
                "Standard Deviation",
                "Records",
            ],
            "Value": [
                series.sum(),
                series.mean(),
                series.min(),
                series.max(),
                series.median(),
                series.std(),
                series.count(),
            ],
        }
    )

    return {
        "table": result,
        "chart_type": None,
    }


def _attribute_distribution(df, field):
    _validate_numeric(df, field, "Attribute")

    series = pd.to_numeric(df[field], errors="coerce").dropna()

    if series.empty:
        return _empty_result(["Metric", "Value"])

    result = pd.DataFrame(
        {
            "Metric": [
                "Records",
                "Average",
                "Median",
                "Minimum",
                "Maximum",
                "Standard Deviation",
                "25th Percentile",
                "75th Percentile",
            ],
            "Value": [
                series.count(),
                series.mean(),
                series.median(),
                series.min(),
                series.max(),
                series.std(),
                series.quantile(0.25),
                series.quantile(0.75),
            ],
        }
    )

    return {
        "table": result,
        "chart_type": None,
    }


def _rate_profile(df, field):
    _validate_numeric(df, field, "Rate")

    series = pd.to_numeric(df[field], errors="coerce").dropna()

    if series.empty:
        return _empty_result(["Metric", "Value"])

    result = pd.DataFrame(
        {
            "Metric": [
                "Records",
                "Average",
                "Median",
                "Minimum",
                "Maximum",
                "Standard Deviation",
            ],
            "Value": [
                series.count(),
                series.mean(),
                series.median(),
                series.min(),
                series.max(),
                series.std(),
            ],
        }
    )

    return {
        "table": result,
        "chart_type": None,
    }


def _score_profile(df, field):
    return _rate_profile(df, field)


def _grouped_numeric(df, measure, dimension, aggregation="sum"):
    _validate_numeric(df, measure, "Measure")
    _validate_dimension(df, dimension)

    result = (
        df.groupby(dimension, dropna=False)[measure]
        .agg(
            Total="sum",
            Average="mean",
            Minimum="min",
            Maximum="max",
            Records="count",
        )
        .reset_index()
    )

    if aggregation == "mean":
        result = result.sort_values(
            "Average", ascending=False
        )
    else:
        result = result.sort_values(
            "Total", ascending=False
        )

    return result.reset_index(drop=True)


def _dimension_comparison(df, measure, dimension):
    result = _grouped_numeric(df, measure, dimension)

    return {
        "table": result,
        "chart_type": "bar",
        "x": dimension,
        "y": "Total",
    }


def _attribute_comparison(df, measure, dimension):
    _validate_numeric(df, measure, "Measure")
    _validate_numeric(df, dimension, "Attribute")

    source = df[[dimension, measure]].dropna().copy()

    if source.empty:
        return _empty_result([dimension, "Total", "Average", "Records"])

    # Exact numeric values are often too granular for an attribute such as
    # age. Bin the attribute into quantile-based groups when possible.
    unique_count = source[dimension].nunique()

    if unique_count >= 5:
        try:
            source["Attribute Group"] = pd.qcut(
                source[dimension],
                q=min(5, unique_count),
                duplicates="drop",
            )
            grouped = (
                source.groupby("Attribute Group", observed=False)[measure]
                .agg(
                    Total="sum",
                    Average="mean",
                    Minimum="min",
                    Maximum="max",
                    Records="count",
                )
                .reset_index()
            )
            grouped["Attribute Group"] = grouped["Attribute Group"].astype(str)
            return {
                "table": grouped,
                "chart_type": "bar",
                "x": "Attribute Group",
                "y": "Average",
            }
        except (ValueError, TypeError):
            pass

    result = _grouped_numeric(
        df,
        measure,
        dimension,
        aggregation="mean",
    )

    return {
        "table": result,
        "chart_type": "bar",
        "x": dimension,
        "y": "Average",
    }


def _ordinal_comparison(df, measure, dimension):
    result = _grouped_numeric(
        df,
        measure,
        dimension,
        aggregation="mean",
    )

    return {
        "table": result,
        "chart_type": "bar",
        "x": dimension,
        "y": "Average",
    }


def _boolean_comparison(df, measure, dimension):
    return _attribute_comparison(df, measure, dimension)


def _geographic_comparison(df, measure, dimension):
    return _dimension_comparison(df, measure, dimension)


def _ranking(df, measure, dimension):
    _validate_numeric(df, measure, "Measure")
    _validate_dimension(df, dimension)

    result = (
        df.groupby(dimension, dropna=False)[measure]
        .sum()
        .reset_index()
        .rename(columns={measure: "Total"})
        .sort_values("Total", ascending=False)
        .reset_index(drop=True)
    )

    result.insert(0, "Rank", range(1, len(result) + 1))

    return {
        "table": result,
        "chart_type": "bar",
        "x": dimension,
        "y": "Total",
        "chart_data": result.head(10),
    }


def _contribution(df, measure, dimension):
    _validate_numeric(df, measure, "Measure")
    _validate_dimension(df, dimension)

    result = (
        df.groupby(dimension, dropna=False)[measure]
        .sum()
        .reset_index()
        .rename(columns={measure: "Total"})
    )

    grand_total = result["Total"].sum()

    if grand_total == 0:
        result["Contribution %"] = 0.0
    else:
        result["Contribution %"] = (
            result["Total"] / grand_total * 100
        )

    result = (
        result.sort_values(
            "Contribution %", ascending=False
        )
        .reset_index(drop=True)
    )

    return {
        "table": result,
        "chart_type": "bar",
        "x": dimension,
        "y": "Contribution %",
    }


def _time_trend(df, measure, date_column, aggregation="sum"):
    _validate_numeric(df, measure, "Measure")
    _validate_date(df, date_column)

    trend_data = (
        df[[date_column, measure]]
        .dropna()
        .sort_values(date_column)
    )

    if trend_data.empty:
        return _empty_result([date_column, measure])

    if aggregation == "mean":
        result = (
            trend_data.set_index(date_column)
            .resample("MS")[measure]
            .agg(["mean", "count"])
            .reset_index()
            .rename(
                columns={
                    "mean": "Average",
                    "count": "Records",
                }
            )
        )
        y_column = "Average"
    else:
        result = (
            trend_data.set_index(date_column)
            .resample("MS")[measure]
            .agg(["sum", "mean", "count"])
            .reset_index()
            .rename(
                columns={
                    "sum": "Total",
                    "mean": "Average",
                    "count": "Records",
                }
            )
        )
        y_column = "Total"

    return {
        "table": result,
        "chart_type": "line",
        "x": date_column,
        "y": y_column,
    }


def _time_coverage(df, date_column):
    _validate_date(df, date_column)

    series = df[date_column].dropna()

    if series.empty:
        return _empty_result(["Metric", "Value"])

    result = pd.DataFrame(
        {
            "Metric": ["Start Date", "End Date", "Records"],
            "Value": [
                series.min(),
                series.max(),
                series.count(),
            ],
        }
    )

    return {
        "table": result,
        "chart_type": None,
    }


def _dataset_structure(df, dimensions=None):
    rows = []

    for column in df.columns:
        unique_count = df[column].nunique(dropna=True)
        rows.append(
            {
                "Column": column,
                "Unique Values": int(unique_count),
                "Missing Values": int(df[column].isna().sum()),
            }
        )

    result = pd.DataFrame(rows)

    return {
        "table": result,
        "chart_type": None,
    }


def run_analysis(df, recommendation):
    """Execute a recommendation using deterministic Python calculations."""

    analysis_type = recommendation["Analysis Type"]
    measure = recommendation.get("Measure")
    dimension = recommendation.get("Dimension")
    date_column = recommendation.get("Date Column")

    if analysis_type in {
        "Overall Profile",
        "Measure Overview",
    }:
        return _measure_overview(df, measure)

    if analysis_type == "Attribute Distribution":
        return _attribute_distribution(df, measure)

    if analysis_type == "Rate Profile":
        return _rate_profile(df, measure)

    if analysis_type == "Score Profile":
        return _score_profile(df, measure)

    if analysis_type == "Dimension Comparison":
        return _dimension_comparison(df, measure, dimension)

    if analysis_type == "Attribute Comparison":
        return _attribute_comparison(df, measure, dimension)

    if analysis_type == "Ordinal Comparison":
        return _ordinal_comparison(df, measure, dimension)

    if analysis_type == "Boolean Comparison":
        return _boolean_comparison(df, measure, dimension)

    if analysis_type == "Geographic Comparison":
        return _geographic_comparison(df, measure, dimension)

    if analysis_type == "Ranking":
        return _ranking(df, measure, dimension)

    if analysis_type == "Contribution":
        return _contribution(df, measure, dimension)

    if analysis_type == "Time Trend":
        return _time_trend(df, measure, date_column, aggregation="sum")

    if analysis_type == "Rate Trend":
        return _time_trend(df, measure, date_column, aggregation="mean")

    if analysis_type == "Score Trend":
        return _time_trend(df, measure, date_column, aggregation="mean")

    if analysis_type == "Time Coverage":
        return _time_coverage(df, date_column)

    if analysis_type == "Dataset Structure":
        return _dataset_structure(df, dimension)

    if analysis_type in {
        "Semantic Interpretation",
        "Text Exploration",
    }:
        return {
            "table": pd.DataFrame(
                {
                    "Message": [
                        "This analysis requires semantic interpretation "
                        "rather than a deterministic numeric calculation."
                    ]
                }
            ),
            "chart_type": None,
        }

    raise ValueError(
        f"Unsupported analysis type: {analysis_type}"
    )
