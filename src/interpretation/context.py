import pandas as pd


def _safe_list(value):
    """Return a list without failing on None or malformed input."""
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return list(value)

    return []


def _sample_values(series, max_values=5):
    """
    Return a few representative non-null values.

    These examples help semantic interpretation without sending
    the entire dataset to the model.
    """
    values = series.dropna()

    if values.empty:
        return []

    unique_values = values.drop_duplicates().head(max_values)

    result = []

    for value in unique_values:
        if pd.isna(value):
            continue

        if isinstance(value, pd.Timestamp):
            result.append(value.isoformat())
        else:
            result.append(str(value))

    return result


def _numeric_summary(series):
    """Return a compact numeric summary."""
    if not pd.api.types.is_numeric_dtype(series):
        return None

    values = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": round(float(values.mean()), 4),
        "median": round(float(values.median()), 4),
    }


def _date_summary(series):
    """Return a compact date range summary."""
    if not pd.api.types.is_datetime64_any_dtype(series):
        return None

    values = series.dropna()

    if values.empty:
        return None

    return {
        "min": values.min().isoformat(),
        "max": values.max().isoformat(),
    }


def build_dataset_context(
    df,
    classification,
    quality=None,
    relationships=None,
    data_dictionary=None,
    analytical_fields=None,
    analysis_questions=None,
    kpi_recommendations=None,
    excel_function_recommendations=None,
    chart_recommendations=None,
):
    """
    Build a compact, model-ready representation of the dataset.

    Important:
        The raw dataset is NOT sent to the LLM.

    The context contains:
        - dataset shape
        - column metadata
        - representative values
        - basic numeric/date summaries
        - quality information
        - detected relationships
        - deterministic recommendations
    """

    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError(
            "build_dataset_context expects a pandas DataFrame."
        )

    analytical_fields = analytical_fields or {}

    classification_map = {}

    if (
        isinstance(classification, pd.DataFrame)
        and "Column" in classification.columns
        and "Classification" in classification.columns
    ):
        for _, row in classification.iterrows():
            column = row.get("Column")

            if pd.isna(column):
                continue

            classification_map[column] = row.get(
                "Classification",
                "Unclassified",
            )

    dictionary_map = {}

    if (
        isinstance(data_dictionary, pd.DataFrame)
        and "Column" in data_dictionary.columns
    ):
        for _, row in data_dictionary.iterrows():
            column = row.get("Column")

            if pd.isna(column):
                continue

            dictionary_map[column] = row.to_dict()

    columns = []

    for column in df.columns:

        series = df[column]

        column_context = {
            "name": str(column),
            "classification": classification_map.get(
                column,
                "Unclassified",
            ),
            "data_type": str(series.dtype),
            "row_count": int(len(series)),
            "missing_count": int(series.isna().sum()),
            "missing_percentage": round(
                float(series.isna().mean() * 100),
                2,
            ),
            "unique_values": int(
                series.nunique(dropna=True)
            ),
            "sample_values": _sample_values(series),
        }

        numeric_summary = _numeric_summary(series)

        if numeric_summary is not None:
            column_context["numeric_summary"] = numeric_summary

        date_summary = _date_summary(series)

        if date_summary is not None:
            column_context["date_summary"] = date_summary

        if column in dictionary_map:
            description = dictionary_map[column].get(
                "Description"
            )

            if description:
                column_context["deterministic_description"] = str(
                    description
                )

        columns.append(column_context)

    context = {
        "dataset": {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "column_names": [
                str(column)
                for column in df.columns
            ],
        },
        "columns": columns,
        "analytical_fields": {
            "ids": _safe_list(
                analytical_fields.get("ids")
            ),
            "dates": _safe_list(
                analytical_fields.get("dates")
            ),
            "measures": _safe_list(
                analytical_fields.get("measures")
            ),
            "dimensions": _safe_list(
                analytical_fields.get("dimensions")
            ),
            "geographic": _safe_list(
                analytical_fields.get("geographic")
            ),
            "text": _safe_list(
                analytical_fields.get("text")
            ),
            "boolean": _safe_list(
                analytical_fields.get("boolean")
            ),
            "unclassified": _safe_list(
                analytical_fields.get("unclassified")
            ),
            "numerical_attributes": _safe_list(
                analytical_fields.get("numerical_attributes")
            ),
            "rates": _safe_list(
                analytical_fields.get("rates")
            ),
            "scores": _safe_list(
                analytical_fields.get("scores")
            ),
            "ordinal": _safe_list(
                analytical_fields.get("ordinal")
            ),
        },
    }

    # ---------------------------------------------------------------
    # Quality summary
    # ---------------------------------------------------------------

    if isinstance(quality, dict):

        summary = quality.get("summary")

        if isinstance(summary, dict):
            context["quality_summary"] = summary

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------

    if isinstance(relationships, pd.DataFrame):

        context["relationships"] = (
            relationships.to_dict(
                orient="records"
            )
        )

    else:
        context["relationships"] = []

    # ---------------------------------------------------------------
    # Existing deterministic recommendations
    # ---------------------------------------------------------------

    if isinstance(
        analysis_questions,
        pd.DataFrame,
    ):

        context["deterministic_recommendations"] = (
            analysis_questions.to_dict(
                orient="records"
            )
        )

    else:
        context["deterministic_recommendations"] = []

    return context