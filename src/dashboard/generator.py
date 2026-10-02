"""Dataset-aware dashboard layout recommendations and workbook blueprint helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DashboardLayout:
    key: str
    name: str
    description: str
    suitability: str
    has_slicers: bool
    preview: tuple[tuple[str, str], ...]


def recommend_dashboard_layouts(
    analytical_fields: dict[str, list[str]] | None,
    selected_kpi_count: int = 0,
    selected_analysis_count: int = 0,
) -> list[dict[str, Any]]:
    """Return five visual dashboard blueprints, adapted to the dataset capabilities."""
    fields = analytical_fields or {}
    has_dates = bool(fields.get("dates"))
    has_dimensions = bool(fields.get("dimensions") or fields.get("geographic"))
    has_measures = bool(fields.get("measures"))

    layouts = [
        DashboardLayout(
            "kpi_left_slicer",
            "KPI + Left Slicers",
            "Three to four KPI cards across the top, filters on the left, and a two-column analysis area.",
            "Useful when the dataset has several categorical or geographic fields that naturally support filtering.",
            True,
            (
                ("HEADER", "Dataset / dashboard title"),
                ("KPI_1", "KPI"), ("KPI_2", "KPI"), ("KPI_3", "KPI"), ("KPI_4", "KPI"),
                ("SLICERS", "Filters / slicers"),
                ("CHART_1", "Main analysis"), ("CHART_2", "Main analysis"),
                ("CHART_3", "Supporting analysis"), ("CHART_4", "Supporting analysis"),
            ),
        ),
        DashboardLayout(
            "kpi_top_trend",
            "KPI + Trend Focus",
            "KPI cards at the top, a large trend visual underneath, followed by supporting comparisons.",
            "Particularly suitable when the dataset contains a date field and at least one aggregatable measure.",
            False,
            (
                ("HEADER", "Dataset / dashboard title"),
                ("KPI_1", "KPI"), ("KPI_2", "KPI"), ("KPI_3", "KPI"), ("KPI_4", "KPI"),
                ("HERO_CHART", "Large time trend"),
                ("CHART_1", "Supporting analysis"), ("CHART_2", "Supporting analysis"),
            ),
        ),
        DashboardLayout(
            "hero_chart",
            "Hero Chart + KPI Strip",
            "A compact KPI strip followed by one dominant visual and two smaller supporting analyses.",
            "Useful when one selected analysis should be the main story and the remaining outputs provide context.",
            False,
            (
                ("HEADER", "Dataset / dashboard title"),
                ("KPI_1", "KPI"), ("KPI_2", "KPI"), ("KPI_3", "KPI"),
                ("HERO_CHART", "Primary analysis"),
                ("CHART_1", "Supporting analysis"), ("CHART_2", "Supporting analysis"),
            ),
        ),
        DashboardLayout(
            "comparison_board",
            "Comparison Board",
            "KPI strip followed by evenly sized comparison panels, designed for category or geographic analysis.",
            "Useful when the selected analyses mainly compare dimensions, rankings, or contributions.",
            True,
            (
                ("HEADER", "Dataset / dashboard title"),
                ("KPI_1", "KPI"), ("KPI_2", "KPI"), ("KPI_3", "KPI"),
                ("SLICERS", "Filters / slicers"),
                ("CHART_1", "Comparison"), ("CHART_2", "Comparison"),
                ("CHART_3", "Comparison"), ("CHART_4", "Comparison"),
            ),
        ),
        DashboardLayout(
            "balanced_grid",
            "Balanced Analytics Grid",
            "A general-purpose dashboard with a KPI row, optional filters, and a balanced four-panel analysis grid.",
            "A flexible choice when the dataset supports a mixture of trends, comparisons, rankings, and summaries.",
            has_dimensions,
            (
                ("HEADER", "Dataset / dashboard title"),
                ("KPI_1", "KPI"), ("KPI_2", "KPI"), ("KPI_3", "KPI"), ("KPI_4", "KPI"),
                ("SLICERS", "Optional filters"),
                ("CHART_1", "Analysis"), ("CHART_2", "Analysis"),
                ("CHART_3", "Analysis"), ("CHART_4", "Analysis"),
            ),
        ),
    ]

    for layout in layouts:
        suitability_score = 50
        if has_dates and layout.key == "kpi_top_trend":
            suitability_score += 30
        if has_dimensions and layout.has_slicers:
            suitability_score += 20
        if has_measures and layout.key == "hero_chart":
            suitability_score += 15
        if selected_kpi_count >= 3 and layout.key in {"kpi_left_slicer", "kpi_top_trend", "balanced_grid"}:
            suitability_score += 10
        if selected_analysis_count >= 3 and layout.key in {"comparison_board", "balanced_grid"}:
            suitability_score += 10
        if selected_analysis_count == 1 and layout.key == "hero_chart":
            suitability_score += 20
        if not has_dimensions and layout.has_slicers:
            suitability_score -= 15

        layout_dict = {
            "Key": layout.key,
            "Layout": layout.name,
            "Description": layout.description,
            "Why It Fits": layout.suitability,
            "Has Slicers": layout.has_slicers,
            "Suitability Score": suitability_score,
            "Preview": layout.preview,
        }
        layout_dict["Preview"] = tuple(layout.preview)
        # The score is internal ordering support; the UI can explain fit without exposing a ranking.
        layouts_by_score = None
        # Kept intentionally local to avoid changing the public return structure.
        _ = layouts_by_score
        if "_score" not in layout_dict:
            layout_dict["_score"] = suitability_score
        yield_item = layout_dict
        # Append through a temporary list below.
        if "_dashboard_items" not in locals():
            _dashboard_items = []
        _dashboard_items.append(yield_item)

    _dashboard_items.sort(key=lambda item: item["_score"], reverse=True)
    for item in _dashboard_items:
        item.pop("_score", None)
    return _dashboard_items
