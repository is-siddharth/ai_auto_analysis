import re

import numpy as np
import pandas as pd


def normalize_column_name(column):
    text = str(column).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = text.lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_range_type(column):
    normalized = normalize_column_name(column)
    tokens = set(normalized.split())

    if tokens.intersection(
        {
            "discount",
            "probability",
            "prob",
            "rate",
            "ratio",
            "proportion",
            "utilization",
            "conversion",
        }
    ):
        return "0-1"

    if (
        "percent" in tokens
        or "percentage" in tokens
        or normalized.endswith("%")
    ):
        return "0-100"

    if "age" in tokens:
        return "age"

    return None


def _empty(columns):
    return pd.DataFrame(columns=columns)


def _duplicate_column_names(df):
    counts = pd.Series(df.columns).value_counts()
    rows = [
        {"Column": column, "Occurrences": int(count)}
        for column, count in counts.items()
        if count > 1
    ]
    return pd.DataFrame(rows, columns=["Column", "Occurrences"])


def _blank_column_names(df):
    rows = []
    for position, column in enumerate(df.columns):
        text = str(column).strip()
        if not text or text.lower().startswith("unnamed"):
            rows.append(
                {
                    "Position": position,
                    "Column": column,
                    "Issue": "Blank or auto-generated column name",
                }
            )
    return pd.DataFrame(
        rows,
        columns=["Position", "Column", "Issue"],
    )


def _missing_severity(missing_percentage):
    if missing_percentage == 0:
        return "None"
    if missing_percentage <= 5:
        return "Low"
    if missing_percentage <= 20:
        return "Moderate"
    if missing_percentage <= 50:
        return "High"
    if missing_percentage < 100:
        return "Very High"
    return "Complete"


def _missing_profile(df):
    rows = []
    for column in df.columns:
        count = int(df[column].isna().sum())
        percentage = (
            round(count / len(df) * 100, 2)
            if len(df) else 0.0
        )
        rows.append(
            {
                "Column": column,
                "Missing Values": count,
                "Missing %": percentage,
                "Severity": _missing_severity(percentage),
            }
        )
    return pd.DataFrame(rows)


def _whitespace_profile(df):
    rows = []
    for column in df.columns:
        series = df[column]
        if not (
            pd.api.types.is_string_dtype(series)
            or pd.api.types.is_object_dtype(series)
        ):
            continue

        values = series.dropna().astype(str)
        leading = int(values.str.startswith(" ").sum())
        trailing = int(values.str.endswith(" ").sum())

        if leading or trailing:
            rows.append(
                {
                    "Column": column,
                    "Leading Spaces": leading,
                    "Trailing Spaces": trailing,
                    "Affected Values": max(leading, trailing),
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "Column",
            "Leading Spaces",
            "Trailing Spaces",
            "Affected Values",
        ],
    )


def _cardinality_profile(df):
    rows = []
    for column in df.columns:
        unique = int(df[column].nunique(dropna=True))
        percentage = round(
            unique / len(df) * 100,
            2,
        ) if len(df) else 0.0
        rows.append(
            {
                "Column": column,
                "Unique Values": unique,
                "Unique %": percentage,
            }
        )
    return pd.DataFrame(rows)


def _numeric_profile(df):
    rows = []
    numeric_columns = df.select_dtypes(include=np.number).columns

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue

        rows.append(
            {
                "Column": column,
                "Minimum": valid.min(),
                "Maximum": valid.max(),
                "Mean": round(float(valid.mean()), 4),
                "Median": round(float(valid.median()), 4),
                "Standard Deviation": round(float(valid.std()), 4),
                "Zero Values": int((valid == 0).sum()),
                "Negative Values": int((valid < 0).sum()),
                "Missing Values": int(df[column].isna().sum()),
            }
        )

    return pd.DataFrame(rows)


def _range_profile(df):
    rows = []
    numeric_columns = df.select_dtypes(include=np.number).columns

    for column in numeric_columns:
        range_type = detect_range_type(column)
        if range_type is None:
            continue

        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue

        if range_type == "0-1":
            lower, upper = 0, 1
            expected = "0 to 1"
        elif range_type == "0-100":
            lower, upper = 0, 100
            expected = "0 to 100"
        else:
            lower, upper = 0, 120
            expected = "0 to 120 (heuristic age range)"

        below = int((series < lower).sum())
        above = int((series > upper).sum())
        invalid = below + above

        rows.append(
            {
                "Column": column,
                "Rule Type": range_type,
                "Expected Range": expected,
                "Minimum": series.min(),
                "Maximum": series.max(),
                "Values Below Range": below,
                "Values Above Range": above,
                "Invalid Values": invalid,
                "Invalid %": round(invalid / len(series) * 100, 2),
            }
        )

    return pd.DataFrame(rows)


def _object_type_anomalies(df):
    rows = []

    for column in df.columns:
        series = df[column]
        if not (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
        ):
            continue

        values = series.dropna()
        if values.empty:
            continue

        strings = values.astype(str).str.strip()
        numeric_parse = pd.to_numeric(strings, errors="coerce")
        numeric_ratio = float(numeric_parse.notna().mean())

        date_parse = pd.to_datetime(
            strings,
            errors="coerce",
            format="mixed",
        )
        date_ratio = float(date_parse.notna().mean())

        if numeric_ratio >= 0.90 and not pd.api.types.is_numeric_dtype(series):
            rows.append(
                {
                    "Column": column,
                    "Detected Pattern": "Mostly numeric values stored as text",
                    "Evidence %": round(numeric_ratio * 100, 2),
                }
            )
        elif date_ratio >= 0.90 and not pd.api.types.is_datetime64_any_dtype(series):
            rows.append(
                {
                    "Column": column,
                    "Detected Pattern": "Mostly date-like values stored as text",
                    "Evidence %": round(date_ratio * 100, 2),
                }
            )

    return pd.DataFrame(
        rows,
        columns=["Column", "Detected Pattern", "Evidence %"],
    )


def _categorical_consistency(df):
    rows = []

    for column in df.columns:
        series = df[column]
        if not (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            continue

        values = series.dropna().astype(str)
        if values.empty:
            continue

        stripped = values.str.strip()
        case_normalized = stripped.str.lower()

        raw_unique = values.nunique()
        stripped_unique = stripped.nunique()
        normalized_unique = case_normalized.nunique()

        whitespace_variants = raw_unique - stripped_unique
        case_variants = stripped_unique - normalized_unique

        if whitespace_variants or case_variants:
            rows.append(
                {
                    "Column": column,
                    "Raw Unique": raw_unique,
                    "After Whitespace Normalization": stripped_unique,
                    "After Case Normalization": normalized_unique,
                    "Whitespace Variants": whitespace_variants,
                    "Case Variants": case_variants,
                }
            )

    return pd.DataFrame(rows)


def _identifier_integrity(df):
    rows = []

    for column in df.columns:
        normalized = normalize_column_name(column)
        tokens = set(normalized.split())

        if not tokens.intersection({"id", "identifier", "uuid", "guid", "key"}):
            continue

        series = df[column]
        missing = int(series.isna().sum())
        duplicates = int(series.dropna().duplicated().sum())
        non_null = series.dropna()
        unique_ratio = (
            non_null.nunique() / len(non_null)
            if len(non_null)
            else 0
        )

        rows.append(
            {
                "Column": column,
                "Missing IDs": missing,
                "Duplicate Non-null IDs": duplicates,
                "Unique Ratio": round(unique_ratio, 4),
            }
        )

    return pd.DataFrame(rows)


def _constant_columns(cardinality_profile):
    if cardinality_profile.empty:
        return cardinality_profile.copy()
    return cardinality_profile[
        cardinality_profile["Unique Values"] <= 1
    ].copy()


def _outlier_profile(df):
    rows = []
    numeric_columns = df.select_dtypes(include=np.number).columns

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 4:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            outlier_count = 0
            lower = q1
            upper = q3
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_count = int(
                ((series < lower) | (series > upper)).sum()
            )

        rows.append(
            {
                "Column": column,
                "Q1": round(float(q1), 4),
                "Q3": round(float(q3), 4),
                "IQR": round(float(iqr), 4),
                "Lower Bound": round(float(lower), 4),
                "Upper Bound": round(float(upper), 4),
                "Potential Outliers": outlier_count,
                "Outlier %": round(
                    outlier_count / len(series) * 100,
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


def _date_logic_profile(df):
    date_columns = [
        column
        for column in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[column])
    ]

    rows = []

    for start in date_columns:
        start_name = normalize_column_name(start)
        start_tokens = set(start_name.split())

        if not start_tokens.intersection(
            {
                "start", "begin", "admit", "admission", "order",
                "hire", "created", "open", "arrival", "checkin",
            }
        ):
            continue

        for end in date_columns:
            if start == end:
                continue

            end_tokens = set(normalize_column_name(end).split())
            if not end_tokens.intersection(
                {
                    "end", "finish", "discharge", "departure", "ship",
                    "delivery", "complete", "completion", "termination",
                    "close", "checkout", "exit",
                }
            ):
                continue

            comparison = df[[start, end]].dropna()
            if comparison.empty:
                continue

            violations = int((comparison[end] < comparison[start]).sum())

            rows.append(
                {
                    "Start Column": start,
                    "End Column": end,
                    "Rule": f"{end} >= {start}",
                    "Compared Rows": len(comparison),
                    "Violations": violations,
                    "Violation %": round(
                        violations / len(comparison) * 100,
                        2,
                    ),
                }
            )

    return pd.DataFrame(rows)


def profile_data_quality(df):
    """Profile quality and flag anomalies without modifying the dataset."""

    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("profile_data_quality expects a pandas DataFrame.")

    duplicate_columns = _duplicate_column_names(df)
    blank_columns = _blank_column_names(df)
    missing_profile = _missing_profile(df)
    whitespace_profile = _whitespace_profile(df)
    cardinality_profile = _cardinality_profile(df)
    constant_columns = _constant_columns(cardinality_profile)
    numeric_profile = _numeric_profile(df)
    range_profile = _range_profile(df)
    type_anomalies = _object_type_anomalies(df)
    categorical_consistency = _categorical_consistency(df)
    identifier_integrity = _identifier_integrity(df)
    date_logic_profile = _date_logic_profile(df)
    outlier_profile = _outlier_profile(df)

    report = {
        "Rows": int(len(df)),
        "Columns": int(len(df.columns)),
        "Duplicate Rows": int(df.duplicated().sum()),
        "Total Missing Values": int(df.isna().sum().sum()),
        "Duplicate Column Names": int(len(duplicate_columns)),
        "Blank / Unnamed Columns": int(len(blank_columns)),
        "Constant Columns": int(len(constant_columns)),
    }

    return {
        "summary": report,
        "missing": missing_profile,
        "whitespace": whitespace_profile,
        "cardinality": cardinality_profile,
        "constant_columns": constant_columns,
        "duplicate_columns": duplicate_columns,
        "blank_columns": blank_columns,
        "numeric": numeric_profile,
        "discount": range_profile,
        "range_validation": range_profile,
        "type_anomalies": type_anomalies,
        "categorical_consistency": categorical_consistency,
        "identifier_integrity": identifier_integrity,
        "date_logic": date_logic_profile,
        "outliers": outlier_profile,
    }
