import pandas as pd


EXPECTED_CLASSIFICATION_COLUMNS = [
    "Column",
    "Classification",
    "Data Type",
    "Unique Values",
    "Missing Values",
    "Unique Ratio",
]


CLASSIFICATION_DESCRIPTIONS = {
    "Potential ID": (
        "Identifier used to distinguish records, entities, transactions, "
        "or other unique items."
    ),
    "Date / Time": (
        "Date or time field that can support time-based analysis, trends, "
        "durations, or period comparisons."
    ),
    "Numerical Measure": (
        "Numerical field whose values can usually be aggregated or compared, "
        "such as totals, averages, rankings, or trends."
    ),
    "Numerical Attribute": (
        "Numeric attribute describing an entity or observation, such as age, "
        "height, duration, or tenure. It is usually analyzed through "
        "distribution or relationships rather than summed."
    ),
    "Rate / Percentage": (
        "Rate, ratio, percentage, or proportion. It is generally analyzed "
        "using averages, distributions, comparisons, or trends rather than sums."
    ),
    "Score / Rating": (
        "Score or rating representing an assessment, index, satisfaction level, "
        "or similar bounded measurement."
    ),
    "Ordinal": (
        "Ordered category whose relative level matters, such as Low, Medium, "
        "and High."
    ),
    "Categorical Dimension": (
        "Categorical field suitable for grouping, segmentation, filtering, "
        "or comparison."
    ),
    "Geographic Code": (
        "Geographic field that may support location-based grouping, mapping, "
        "or geographic comparison."
    ),
    "Text": (
        "Descriptive text field that may support search, qualitative analysis, "
        "or semantic interpretation."
    ),
    "Boolean": (
        "Binary field representing two possible states."
    ),
    "Unclassified": (
        "Field whose analytical role could not be determined confidently from "
        "its structure alone."
    ),
}


def _safe_classification_map(classification_df):
    if classification_df is None:
        return {}

    if not isinstance(classification_df, pd.DataFrame):
        return {}

    if "Column" not in classification_df.columns:
        return {}

    if "Classification" not in classification_df.columns:
        return {}

    mapping = {}

    for _, row in classification_df.iterrows():
        column = row.get("Column")

        if pd.isna(column):
            continue

        classification = row.get("Classification", "Unclassified")

        if pd.isna(classification):
            classification = "Unclassified"

        mapping[column] = classification

    return mapping


def _description_for_classification(classification):
    return CLASSIFICATION_DESCRIPTIONS.get(
        classification,
        "Column requiring further interpretation.",
    )


def build_data_dictionary(df, classification_df):
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError(
            "build_data_dictionary expects a pandas DataFrame."
        )

    classification_map = _safe_classification_map(classification_df)

    rows = []

    for column in df.columns:
        classification = classification_map.get(
            column,
            "Unclassified",
        )

        rows.append(
            {
                "Column": column,
                "Classification": classification,
                "Description": _description_for_classification(
                    classification
                ),
                "Data Type": str(df[column].dtype),
                "Unique Values": int(df[column].nunique(dropna=True)),
                "Missing Values": int(df[column].isna().sum()),
            }
        )

    return pd.DataFrame(rows)


def identify_analytical_fields(classification_df):
    """Map analytical classifications into safe field groups."""

    result = {
        "ids": [],
        "dates": [],
        "measures": [],
        "numerical_attributes": [],
        "rates": [],
        "scores": [],
        "ordinal": [],
        "dimensions": [],
        "geographic": [],
        "text": [],
        "boolean": [],
        "unclassified": [],
    }

    if not isinstance(classification_df, pd.DataFrame):
        return result

    if "Column" not in classification_df.columns:
        return result

    if "Classification" not in classification_df.columns:
        return result

    mapping = {
        "Potential ID": "ids",
        "Date / Time": "dates",
        "Numerical Measure": "measures",
        "Numerical Attribute": "numerical_attributes",
        "Rate / Percentage": "rates",
        "Score / Rating": "scores",
        "Ordinal": "ordinal",
        "Categorical Dimension": "dimensions",
        "Geographic Code": "geographic",
        "Text": "text",
        "Boolean": "boolean",
        "Unclassified": "unclassified",
    }

    for _, row in classification_df.iterrows():
        column = row.get("Column")
        classification = row.get("Classification", "Unclassified")

        if pd.isna(column):
            continue

        if pd.isna(classification):
            classification = "Unclassified"

        target_group = mapping.get(
            classification,
            "unclassified",
        )

        result[target_group].append(column)

    return result
