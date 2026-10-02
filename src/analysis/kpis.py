import re
import pandas as pd


def _safe_list(value):
    return list(value) if isinstance(value, (list, tuple)) else []


def _valid(values, columns):
    return [v for v in _safe_list(values) if v in columns]


def _field_groups(analytical_fields, columns):
    fields = analytical_fields or {}
    return {
        "ids": _valid(fields.get("ids"), columns),
        "measures": _valid(fields.get("measures"), columns),
        "attributes": _valid(fields.get("numerical_attributes"), columns),
        "rates": _valid(fields.get("rates"), columns),
        "scores": _valid(fields.get("scores"), columns),
        "dimensions": _valid(fields.get("dimensions"), columns),
        "dates": _valid(fields.get("dates"), columns),
        "boolean": _valid(fields.get("boolean"), columns),
        "ordinal": _valid(fields.get("ordinal"), columns),
    }


def _friendly_entity_name(field):
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(field))
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    lowered = text.lower()
    for suffix in (" id", "_id"):
        if lowered.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text.strip().title() or "Records"


def _add(rows, name, category, calculation, fields, rationale, priority="Medium", formula_logic=None):
    rows.append({
        "KPI": name,
        "Category": category,
        "Calculation": calculation,
        "Fields": ", ".join(fields),
        "Formula Logic": formula_logic or calculation,
        "Priority": priority,
        "Rationale": rationale,
    })


def generate_kpi_recommendations(df, analytical_fields):
    """Generate dataset-aware KPI candidates without requiring domain-specific rules."""
    columns = list(df.columns)
    groups = _field_groups(analytical_fields, columns)
    rows = []

    # Distinct identifiers are the safest generic entity-count KPI.
    for field in groups["ids"][:2]:
        series = df[field].dropna()
        unique = int(series.nunique())
        non_null = int(series.shape[0])
        field_lower = str(field).strip().lower().replace("_", " ")
        if unique > 0 and not any(term in field_lower for term in ["row id", "rowid", "record id", "index id", "sequence id"]):
            entity = _friendly_entity_name(field)
            _add(
                rows,
                f"Total {entity}s" if not entity.lower().endswith("s") else f"Total {entity}",
                "Count",
                f"Distinct count of {field}",
                [field],
                "The field behaves like an identifier, so distinct entities are more meaningful than summing the ID.",
                "High",
                f"DISTINCTCOUNT({field})",
            )

    for field in groups["measures"][:5]:
        _add(
            rows,
            f"Total {field}",
            "Measure",
            f"Sum of {field}",
            [field],
            "This is an aggregatable numerical measure and can be summarized as a total.",
            "High",
            f"SUM({field})",
        )
        _add(
            rows,
            f"Average {field}",
            "Measure",
            f"Average of {field}",
            [field],
            "An average provides a typical value and complements the total.",
            "Medium",
            f"AVERAGE({field})",
        )

    for field in groups["rates"][:3]:
        _add(
            rows,
            f"Average {field}",
            "Rate",
            f"Average of {field}",
            [field],
            "Rates and percentages should normally be averaged or otherwise weighted, not summed.",
            "High",
            f"AVERAGE({field})",
        )

    for field in groups["scores"][:3]:
        _add(
            rows,
            f"Average {field}",
            "Score",
            f"Average of {field}",
            [field],
            "Scores and ratings are typically summarized through their central tendency.",
            "Medium",
            f"AVERAGE({field})",
        )

    # Common ratio KPI: profit/revenue, cost/sales, etc. Only create when both
    # fields are clearly named and present; never invent a business formula.
    names = {str(c).lower(): c for c in groups["measures"]}
    sales = next((c for k, c in names.items() if "sales" in k or "revenue" in k), None)
    profit = next((c for k, c in names.items() if "profit" in k or "earnings" in k), None)
    if sales and profit:
        _add(
            rows,
            "Profit Margin",
            "Ratio",
            f"Total {profit} divided by total {sales}",
            [profit, sales],
            "Both fields appear to represent financial measures where a margin is a meaningful derived KPI.",
            "High",
            f"SUM({profit}) / SUM({sales})",
        )

    # Keep recommendations useful rather than overwhelming.
    result = pd.DataFrame(rows, columns=[
        "KPI", "Category", "Calculation", "Fields", "Formula Logic", "Priority", "Rationale"
    ])
    if result.empty:
        return result

    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    result["_priority_order"] = result["Priority"].map(priority_order).fillna(9)
    result = result.sort_values(["_priority_order", "KPI"]).drop(columns="_priority_order")
    return result.reset_index(drop=True).head(20)


def calculate_kpi(df, kpi_recommendation):
    """Calculate one selected KPI deterministically from the dataset.

    The recommendation tells us which fields and aggregation to use; the
    numeric result always comes from the actual dataframe.
    """
    if kpi_recommendation is None:
        raise ValueError("A KPI recommendation is required.")

    kpi_name = str(kpi_recommendation.get("KPI", "")).strip()
    fields_text = str(kpi_recommendation.get("Fields", "")).strip()
    fields = [field.strip() for field in fields_text.split(",") if field.strip()]

    missing = [field for field in fields if field not in df.columns]
    if missing:
        raise ValueError(f"KPI field(s) not found: {', '.join(missing)}")

    if not fields:
        raise ValueError(f"No source fields were defined for KPI '{kpi_name}'.")

    category = str(kpi_recommendation.get("Category", "")).strip()
    calculation = str(kpi_recommendation.get("Calculation", "")).lower()

    if category == "Count":
        value = int(df[fields[0]].dropna().nunique())

    elif category == "Ratio" and "Profit Margin" in kpi_name:
        profit_field, sales_field = fields[0], fields[1]
        profit = pd.to_numeric(df[profit_field], errors="coerce").sum()
        sales = pd.to_numeric(df[sales_field], errors="coerce").sum()
        value = None if sales == 0 else float(profit / sales)

    elif "average" in calculation:
        series = pd.to_numeric(df[fields[0]], errors="coerce")
        value = float(series.mean()) if series.notna().any() else None

    elif "sum" in calculation or "total" in calculation:
        series = pd.to_numeric(df[fields[0]], errors="coerce")
        value = float(series.sum()) if series.notna().any() else None

    else:
        raise ValueError(
            f"Unsupported KPI calculation for '{kpi_name}': "
            f"{kpi_recommendation.get('Calculation', '')}"
        )

    return {
        "KPI": kpi_name,
        "Value": value,
        "Category": kpi_recommendation.get("Category", ""),
        "Calculation": kpi_recommendation.get("Calculation", ""),
        "Fields": kpi_recommendation.get("Fields", ""),
        "Formula Logic": kpi_recommendation.get("Formula Logic", ""),
        "Rationale": kpi_recommendation.get("Rationale", ""),
    }
