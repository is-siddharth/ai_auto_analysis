import re

import pandas as pd


# ============================================================
# SEMANTIC TERMS
# ============================================================

START_TERMS = {
    "start",
    "begin",
    "beginning",
    "in",
    "entry",
    "enter",
    "arrival",
    "arrive",
    "checkin",
    "check",
    "admit",
    "admission",
    "created",
    "creation",
    "open",
    "opened",
    "onset",
    "order",
    "ordered",
    "hire",
    "hired",
    "join",
    "joined",
    "from"
}


END_TERMS = {
    "end",
    "finish",
    "finished",
    "out",
    "exit",
    "departure",
    "depart",
    "checkout",
    "check",
    "discharge",
    "discharged",
    "complete",
    "completed",
    "completion",
    "close",
    "closed",
    "ship",
    "shipped",
    "delivery",
    "delivered",
    "termination",
    "terminated",
    "to"
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_column_name(
    column
):
    """
    Normalize names before semantic matching.

    CamelCase is split BEFORE lowercasing.

    Example:
        AdmitDate -> admit date
        Ship_Date -> ship date
        Order-Date -> order date
    """

    text = str(
        column
    ).strip()

    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        " ",
        text
    )

    text = text.lower()

    text = re.sub(
        r"[_\-]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokenize_column_name(
    column
):
    normalized = normalize_column_name(
        column
    )

    return set(
        normalized.split()
    )


def contains_term(
    column_name,
    terms
):
    tokens = tokenize_column_name(
        column_name
    )

    return bool(
        tokens.intersection(
            terms
        )
    )


# ============================================================
# RELATIONSHIP SCORING
# ============================================================

def relationship_score(
    start_column,
    end_column
):
    start_tokens = tokenize_column_name(
        start_column
    )

    end_tokens = tokenize_column_name(
        end_column
    )

    start_score = len(
        start_tokens.intersection(
            START_TERMS
        )
    )

    end_score = len(
        end_tokens.intersection(
            END_TERMS
        )
    )

    return (
        start_score
        +
        end_score
    )


# ============================================================
# DATE RELATIONSHIP DETECTION
# ============================================================

def detect_date_relationships(
    df
):
    """
    Detect plausible chronological relationships between
    datetime columns.

    Example:

        Order Date -> Ship Date

    can produce:

        Ship Date >= Order Date
    """

    date_columns = [
        column
        for column in df.columns
        if pd.api.types.is_datetime64_any_dtype(
            df[column]
        )
    ]


    relationships = []


    for start_column in date_columns:

        for end_column in date_columns:

            if start_column == end_column:
                continue


            start_has_signal = contains_term(
                start_column,
                START_TERMS
            )

            end_has_signal = contains_term(
                end_column,
                END_TERMS
            )


            if not (
                start_has_signal
                and
                end_has_signal
            ):

                continue


            comparison_rows = (
                df[
                    [
                        start_column,
                        end_column
                    ]
                ]
                .dropna()
            )


            if comparison_rows.empty:
                continue


            invalid_rows = (
                comparison_rows[
                    end_column
                ]
                <
                comparison_rows[
                    start_column
                ]
            )


            invalid_count = int(
                invalid_rows.sum()
            )


            valid_count = (
                len(comparison_rows)
                -
                invalid_count
            )


            violation_percentage = round(
                invalid_count
                /
                len(comparison_rows)
                *
                100,
                2
            )


            valid_percentage = round(
                valid_count
                /
                len(comparison_rows)
                *
                100,
                2
            )


            relationships.append({

                "Start Column": start_column,

                "End Column": end_column,

                "Rule": (
                    f"{end_column} >= "
                    f"{start_column}"
                ),

                "Semantic Score": relationship_score(
                    start_column,
                    end_column
                ),

                "Compared Rows": len(
                    comparison_rows
                ),

                "Valid %": valid_percentage,

                "Violations": invalid_count,

                "Violation %": (
                    violation_percentage
                )
            })


    if not relationships:

        return pd.DataFrame(
            columns=[
                "Start Column",
                "End Column",
                "Rule",
                "Semantic Score",
                "Compared Rows",
                "Valid %",
                "Violations",
                "Violation %"
            ]
        )


    result = pd.DataFrame(
        relationships
    )


    return (
        result
        .sort_values(
            [
                "Semantic Score",
                "Valid %"
            ],
            ascending=[
                False,
                False
            ]
        )
        .drop_duplicates(
            subset=[
                "Start Column",
                "End Column"
            ]
        )
        .reset_index(
            drop=True
        )
    )
