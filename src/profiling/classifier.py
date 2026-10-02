import re

import pandas as pd


ID_TERMS = {
    "id",
    "identifier",
    "key",
    "uuid",
    "guid",
    "code",
    "number",
    "no",
}

GEOGRAPHIC_TERMS = {
    "country",
    "state",
    "province",
    "region",
    "city",
    "town",
    "district",
    "county",
    "postal",
    "zip",
    "zipcode",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "location",
}

TEXT_TERMS = {
    "name",
    "description",
    "comment",
    "comments",
    "note",
    "notes",
    "address",
    "title",
    "question",
    "answer",
    "feedback",
    "review",
    "remark",
    "details",
    "text",
}

DIMENSION_TERMS = {
    "category",
    "subcategory",
    "sub_category",
    "segment",
    "type",
    "class",
    "group",
    "department",
    "division",
    "status",
    "mode",
    "channel",
    "source",
    "level",
    "tier",
    "gender",
    "customer",
    "product",
}

NUMERICAL_ATTRIBUTE_TERMS = {
    "age",
    "height",
    "weight",
    "distance",
    "duration",
    "temperature",
    "years",
    "months",
    "days",
    "experience",
    "tenure",
    "household",
    "population",
}

RATE_TERMS = {
    "percent",
    "percentage",
    "rate",
    "ratio",
    "proportion",
    "share",
    "utilization",
    "conversion",
    "margin",
    "completion",
    "discount",
    "growth",
    "change",
}

SCORE_TERMS = {
    "score",
    "rating",
    "satisfaction",
    "likelihood",
    "index",
    "grade",
    "rating_score",
}

ORDINAL_TERMS = {
    "level",
    "tier",
    "rank",
    "severity",
    "priority",
    "stage",
    "grade",
}

BOOLEAN_VALUES = {
    "true",
    "false",
    "yes",
    "no",
    "y",
    "n",
}

ORDINAL_VALUE_GROUPS = [
    {"low", "medium", "high"},
    {"poor", "fair", "good", "excellent"},
    {"very low", "low", "medium", "high", "very high"},
    {"beginner", "intermediate", "advanced"},
    {"junior", "mid", "senior"},
    {"small", "medium", "large"},
]


def normalize_column_name(column):
    text = str(column).strip()

    # Split camelCase / PascalCase.
    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        " ",
        text,
    )

    text = text.lower()

    text = re.sub(
        r"[_\-]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize_column_name(column):
    normalized = normalize_column_name(column)

    if not normalized:
        return set()

    return set(normalized.split())


def contains_term(column_name, terms):
    tokens = tokenize_column_name(column_name)

    return bool(tokens.intersection(terms))


def is_boolean_series(series):
    if pd.api.types.is_bool_dtype(series):
        return True

    non_null = series.dropna()

    if non_null.empty:
        return False

    normalized = (
        non_null.astype("string")
        .str.strip()
        .str.lower()
    )

    return set(normalized.unique()).issubset(BOOLEAN_VALUES)


def looks_like_identifier(series, column_name):
    if contains_term(column_name, ID_TERMS):
        return True

    non_null = series.dropna()

    if len(non_null) < 10:
        return False

    unique_ratio = non_null.nunique() / len(non_null)

    if unique_ratio < 0.98:
        return False

    if pd.api.types.is_integer_dtype(series):
        return True

    if (
        pd.api.types.is_string_dtype(series)
        or pd.api.types.is_object_dtype(series)
    ):
        average_length = (
            non_null.astype("string")
            .str.len()
            .mean()
        )

        return average_length <= 30

    return False


def looks_like_geographic_code(series, column_name):
    normalized = normalize_column_name(column_name)

    geographic_terms = [
        "postal",
        "zip",
        "zipcode",
        "latitude",
        "longitude",
        "country",
        "state",
        "province",
        "region",
        "city",
        "town",
        "district",
        "county",
        "location",
    ]

    return any(term in normalized for term in geographic_terms)


def looks_like_rate(series, column_name):
    if not pd.api.types.is_numeric_dtype(series):
        return False

    return contains_term(column_name, RATE_TERMS)


def looks_like_score(series, column_name):
    if contains_term(column_name, SCORE_TERMS):
        return True

    return False


def looks_like_numerical_attribute(series, column_name):
    if not pd.api.types.is_numeric_dtype(series):
        return False

    return contains_term(
        column_name,
        NUMERICAL_ATTRIBUTE_TERMS,
    )


def looks_like_ordinal(series, column_name):
    if contains_term(column_name, ORDINAL_TERMS):
        return True

    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return False

    non_null = series.dropna()

    if non_null.empty:
        return False

    values = (
        non_null.astype("string")
        .str.strip()
        .str.lower()
    )

    unique_values = set(values.unique())

    for group in ORDINAL_VALUE_GROUPS:
        if unique_values.issubset(group) and len(unique_values) >= 2:
            return True

    return False


def looks_like_text(series, column_name):
    if contains_term(column_name, TEXT_TERMS):
        return True

    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return False

    non_null = series.dropna()

    if non_null.empty:
        return False

    average_length = (
        non_null.astype("string")
        .str.len()
        .mean()
    )

    unique_ratio = (
        non_null.nunique() / len(non_null)
    )

    if average_length >= 50:
        return True

    if unique_ratio > 0.60 and average_length >= 25:
        return True

    return False


def looks_like_dimension(series, column_name):
    if contains_term(column_name, DIMENSION_TERMS):
        return True

    non_null = series.dropna()

    if non_null.empty:
        return False

    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return False

    unique_ratio = (
        non_null.nunique() / len(non_null)
    )

    average_length = (
        non_null.astype("string")
        .str.len()
        .mean()
    )

    if unique_ratio < 0.30 and average_length < 100:
        return True

    return False


def classify_columns(df):
    expected_columns = [
        "Column",
        "Classification",
        "Data Type",
        "Unique Values",
        "Missing Values",
        "Unique Ratio",
    ]

    if df is None:
        return pd.DataFrame(
            columns=expected_columns
        )

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "classify_columns expects a pandas DataFrame."
        )

    if len(df.columns) == 0:
        return pd.DataFrame(
            columns=expected_columns
        )

    rows = []

    for column in df.columns:
        series = df[column]

        unique_values = int(
            series.nunique(dropna=True)
        )

        missing_values = int(
            series.isna().sum()
        )

        non_null_count = (
            len(series) - missing_values
        )

        if non_null_count > 0:
            unique_ratio = round(
                unique_values / non_null_count,
                4,
            )
        else:
            unique_ratio = 0.0

        classification = "Unclassified"

        # Order matters.
        if pd.api.types.is_datetime64_any_dtype(series):
            classification = "Date / Time"

        elif is_boolean_series(series):
            classification = "Boolean"

        elif looks_like_geographic_code(
            series,
            column,
        ):
            classification = "Geographic Code"

        elif looks_like_identifier(
            series,
            column,
        ):
            classification = "Potential ID"

        elif looks_like_rate(
            series,
            column,
        ):
            classification = "Rate / Percentage"

        elif looks_like_score(
            series,
            column,
        ):
            classification = "Score / Rating"

        elif looks_like_numerical_attribute(
            series,
            column,
        ):
            classification = "Numerical Attribute"

        elif looks_like_ordinal(
            series,
            column,
        ):
            classification = "Ordinal"

        elif pd.api.types.is_numeric_dtype(series):
            classification = "Numerical Measure"

        elif looks_like_text(
            series,
            column,
        ):
            classification = "Text"

        elif looks_like_dimension(
            series,
            column,
        ):
            classification = "Categorical Dimension"

        else:
            classification = "Unclassified"

        rows.append(
            {
                "Column": column,
                "Classification": classification,
                "Data Type": str(series.dtype),
                "Unique Values": unique_values,
                "Missing Values": missing_values,
                "Unique Ratio": unique_ratio,
            }
        )

    return pd.DataFrame(
        rows,
        columns=expected_columns,
    )