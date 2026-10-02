"""Dataset-aware recommendations for Excel filters and dashboard slicers."""

from __future__ import annotations

from typing import Any

import pandas as pd


def recommend_filters(df: pd.DataFrame, analytical_fields: dict[str, list[str]] | None) -> pd.DataFrame:
    """Recommend low/medium-cardinality fields that make useful dashboard filters."""
    fields = analytical_fields or {}
    columns = list(df.columns)
    candidates: list[dict[str, Any]] = []

    def add(field: str, role: str, priority: str, reason: str, filter_type: str = "Slicer") -> None:
        if field not in columns:
            return
        series = df[field].dropna()
        unique = int(series.nunique())
        if unique <= 1:
            return
        # High-cardinality text (customer/product names, IDs) is usually a poor dashboard slicer.
        if unique > 50 and role not in {"Date", "Geographic"}:
            return
        field_name = str(field).lower()
        if role == "Dimension" and any(token in field_name for token in ["customer", "product", "name", "email", "phone", "address"]):
            return
        if role == "Dimension" and len(df) > 0 and unique / len(df) > 0.8:
            return
        candidates.append({
            "Field": field,
            "Filter Type": filter_type,
            "Unique Values": unique,
            "Priority": priority,
            "Why Use It": reason,
            "What It Does": "Lets the viewer narrow the dashboard to selected values without changing the underlying calculations.",
        })

    for field in fields.get("dimensions", []) or []:
        name = str(field).lower()
        unique = int(df[field].nunique(dropna=True)) if field in df.columns else 0
        if unique <= 12:
            priority = "High" if unique <= 8 else "Medium"
            reason = "A compact categorical field can split the dashboard into meaningful groups."
            if any(token in name for token in ["region", "segment", "category", "type", "mode", "status"]):
                reason = "This field naturally separates the data into a small number of interpretable groups."
            add(field, "Dimension", priority, reason)

    for field in fields.get("geographic", []) or []:
        add(field, "Geographic", "High", "Geographic filters let viewers focus the dashboard on a region or location.")

    for field in fields.get("dates", []) or []:
        add(field, "Date", "High", "A date filter lets viewers focus the dashboard on a selected time period.", "Date Filter")

    for field in fields.get("boolean", []) or []:
        add(field, "Boolean", "Medium", "A yes/no filter is useful for isolating two meaningful groups.")

    if not candidates:
        return pd.DataFrame(columns=["Field", "Filter Type", "Unique Values", "Priority", "Why Use It", "What It Does"])

    result = pd.DataFrame(candidates)
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    result["_sort"] = result["Priority"].map(priority_order).fillna(9)
    result = result.sort_values(["_sort", "Unique Values", "Field"]).drop(columns="_sort")
    return result.drop_duplicates(subset=["Field"]).head(8).reset_index(drop=True)
