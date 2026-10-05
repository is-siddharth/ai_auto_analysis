"""Conservative, approval-based dataset cleaning.

This module never modifies a dataset while generating recommendations. It
produces explicit cleaning actions, explains their risk, and only applies
actions that the user (or the conservative automated decision mode) approves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CleaningAction:
    action_id: str
    issue_type: str
    field: str
    affected_rows: int
    recommendation: str
    reason: str
    confidence: str
    default_selected: bool
    automated_decision: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Action ID": self.action_id,
            "Issue": self.issue_type,
            "Field": self.field,
            "Affected Rows": self.affected_rows,
            "Recommended Action": self.recommendation,
            "Why": self.reason,
            "Confidence": self.confidence,
            "Default": "Approve" if self.default_selected else "Review",
            "Automated Decision": self.automated_decision,
        }


def recommend_cleaning_actions(df: pd.DataFrame) -> pd.DataFrame:
    """Return conservative, executable cleaning recommendations.

    The function is intentionally conservative:
    - exact duplicate rows can be removed;
    - fully blank rows can be removed;
    - surrounding whitespace and blank text values can be standardized;
    - missing-value imputation, outlier removal, range correction, case
      normalization, and row deletion based on a single missing field are
      never recommended for automatic execution because they require context.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("recommend_cleaning_actions expects a pandas DataFrame.")

    actions: list[CleaningAction] = []

    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        actions.append(
            CleaningAction(
                "remove_exact_duplicates",
                "Duplicate Rows",
                "All columns",
                duplicate_count,
                "Remove exact duplicate rows, keeping the first occurrence.",
                "Exact duplicates carry no additional information and can double-count records.",
                "High",
                True,
                "Approve — deterministic and low risk",
            )
        )

    if len(df.columns):
        blank_rows = int(df.isna().all(axis=1).sum())
        if blank_rows:
            actions.append(
                CleaningAction(
                    "remove_blank_rows",
                    "Completely Blank Rows",
                    "All columns",
                    blank_rows,
                    "Remove rows where every field is missing.",
                    "A completely blank record contains no analytical information.",
                    "High",
                    True,
                    "Approve — deterministic and low risk",
                )
            )

    for column in df.columns:
        series = df[column]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue

        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue

        whitespace_mask = non_null.str.strip().ne(non_null)
        whitespace_count = int(whitespace_mask.sum())
        if whitespace_count:
            actions.append(
                CleaningAction(
                    f"trim_whitespace::{column}",
                    "Text Whitespace",
                    str(column),
                    whitespace_count,
                    "Trim leading and trailing whitespace.",
                    "Whitespace around text can create false categories such as 'Retail' and 'Retail '.",
                    "High",
                    True,
                    "Approve — deterministic and low risk",
                )
            )

        blank_text_count = int(non_null.str.strip().eq("").sum())
        if blank_text_count:
            actions.append(
                CleaningAction(
                    f"blank_text_to_missing::{column}",
                    "Blank Text Values",
                    str(column),
                    blank_text_count,
                    "Convert whitespace-only text to missing values.",
                    "A blank text value is clearer and safer when represented as a true missing value.",
                    "High",
                    True,
                    "Approve — deterministic and low risk",
                )
            )

    return pd.DataFrame(
        [action.to_dict() for action in actions],
        columns=[
            "Action ID", "Issue", "Field", "Affected Rows",
            "Recommended Action", "Why", "Confidence", "Default",
            "Automated Decision",
        ],
    )


def automated_cleaning_action_ids(recommendations: pd.DataFrame) -> list[str]:
    """Select only high-confidence, low-risk actions for automated mode."""
    if recommendations is None or recommendations.empty:
        return []
    mask = recommendations["Confidence"].eq("High") & recommendations["Automated Decision"].str.startswith("Approve")
    return recommendations.loc[mask, "Action ID"].astype(str).tolist()


def apply_cleaning_actions(
    df: pd.DataFrame,
    recommendations: pd.DataFrame,
    approved_action_ids: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply only explicitly approved cleaning actions and return an audit log."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("apply_cleaning_actions expects a pandas DataFrame.")

    approved = set(approved_action_ids or [])
    cleaned = df.copy()
    audit: list[dict[str, Any]] = []

    if recommendations is None or recommendations.empty:
        return cleaned, pd.DataFrame(columns=[
            "Action ID", "Issue", "Field", "Rows Before", "Rows After",
            "Cells Changed", "Result",
        ])

    for _, action in recommendations.iterrows():
        action_id = str(action["Action ID"])
        if action_id not in approved:
            continue

        rows_before = len(cleaned)
        cells_changed = 0
        issue = str(action["Issue"])
        field = str(action["Field"])

        if action_id == "remove_exact_duplicates":
            before = len(cleaned)
            cleaned = cleaned.drop_duplicates(keep="first").reset_index(drop=True)
            cells_changed = before - len(cleaned)

        elif action_id == "remove_blank_rows":
            before = len(cleaned)
            cleaned = cleaned.loc[~cleaned.isna().all(axis=1)].reset_index(drop=True)
            cells_changed = before - len(cleaned)

        elif action_id.startswith("trim_whitespace::"):
            column = action_id.split("::", 1)[1]
            if column in cleaned.columns:
                original = cleaned[column].copy()
                cleaned[column] = cleaned[column].map(lambda value: value.strip() if isinstance(value, str) else value)
                cells_changed = int((original.fillna("<NA>").astype(str) != cleaned[column].fillna("<NA>").astype(str)).sum())

        elif action_id.startswith("blank_text_to_missing::"):
            column = action_id.split("::", 1)[1]
            if column in cleaned.columns:
                original = cleaned[column].copy()
                cleaned[column] = cleaned[column].map(
                    lambda value: pd.NA if isinstance(value, str) and not value.strip() else value
                )
                cells_changed = int((original.fillna("<NA>").astype(str) != cleaned[column].fillna("<NA>").astype(str)).sum())

        else:
            continue

        audit.append({
            "Action ID": action_id,
            "Issue": issue,
            "Field": field,
            "Rows Before": rows_before,
            "Rows After": len(cleaned),
            "Cells Changed": cells_changed,
            "Result": "Applied",
        })

    return cleaned, pd.DataFrame(audit)
