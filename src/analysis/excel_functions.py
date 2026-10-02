import re
import pandas as pd


def _safe_list(value):
    return list(value) if isinstance(value, (list, tuple)) else []


def _valid(values, columns):
    return [v for v in _safe_list(values) if v in columns]


def _friendly(field):
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(field))
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _add(rows, task, functions, fields, when_to_use, example, level="Beginner", note=""):
    rows.append({
        "Task": task,
        "Recommended Function": functions,
        "Dataset Fields": ", ".join(fields),
        "When To Use": when_to_use,
        "Example": example,
        "Level": level,
        "Why It Matters": note,
    })


def generate_excel_function_recommendations(df, analytical_fields):
    """Recommend a curated set of Excel functions from dataset structure."""
    columns = list(df.columns)
    fields = analytical_fields or {}
    measures = _valid(fields.get("measures"), columns)
    dimensions = _valid(fields.get("dimensions"), columns)
    ids = _valid(fields.get("ids"), columns)
    dates = _valid(fields.get("dates"), columns)
    rates = _valid(fields.get("rates"), columns)
    text_fields = _valid(fields.get("text"), columns)
    boolean = _valid(fields.get("boolean"), columns)
    dimensions = _valid(fields.get("dimensions"), columns)
    preferred_returns = _valid(fields.get("text"), columns) + _valid(fields.get("dimensions"), columns)
    rows = []

    if measures and dimensions:
        m, d = measures[0], dimensions[0]
        _add(rows, f"Calculate {m} for one category or condition", "SUMIF", [d, m],
             "Use when one condition determines which numerical values should be added.",
             f"=SUMIF({d}_Range, criteria, {m}_Range)", note="Connects a business question to conditional aggregation.")
        _add(rows, f"Calculate {m} using multiple conditions", "SUMIFS", [d, m],
             "Use when two or more conditions determine which values should be added.",
             f"=SUMIFS({m}_Range, {d}_Range, criteria, ...)", note="Useful for questions such as category + region or department + year.")
        _add(rows, f"Count records meeting a condition", "COUNTIF / COUNTIFS", [d],
             "Use COUNTIF for one condition and COUNTIFS for multiple conditions.",
             f"=COUNTIF({d}_Range, criteria)", note="Especially useful for headcount, order counts, status counts, and category counts.")
        _add(rows, f"Calculate average {m} under a condition", "AVERAGEIF / AVERAGEIFS", [d, m],
             "Use when you need an average restricted to one or more conditions.",
             f"=AVERAGEIF({d}_Range, criteria, {m}_Range)", note="Prevents unnecessary manual filtering for common comparisons.")

    if ids and columns:
        usable_ids = [
            c for c in ids
            if not any(term in str(c).strip().lower().replace("_", " ") for term in ["row id", "rowid", "record id", "index id", "sequence id"])
        ]
        lookup_id = usable_ids[0] if usable_ids else ids[0]
        return_candidates = [c for c in preferred_returns if c != lookup_id and c not in ids]
        if not return_candidates:
            return_candidates = [c for c in columns if c != lookup_id and c not in ids and c not in dates and c not in measures]
        if return_candidates:
            ret = return_candidates[0]
            _add(rows, f"Retrieve {ret} using {lookup_id}", "XLOOKUP", [lookup_id, ret],
                 "Use when one field identifies a record and another field needs to be retrieved.",
                 f"=XLOOKUP({lookup_id}_Cell, {lookup_id}_Range, {ret}_Range)", note="Modern Excel lookup pattern; works even when the return field is to the left of the lookup field.")
            _add(rows, f"Retrieve {ret} with older Excel-compatible lookup", "VLOOKUP", [lookup_id, ret],
                 "Use for a traditional vertical lookup when the lookup field is on the left of the return field.",
                 f"=VLOOKUP({lookup_id}_Cell, Table_Range, column_number, FALSE)", level="Beginner", note="Useful when working with older Excel versions or existing workbooks.")
            _add(rows, f"Build a flexible lookup from a position", "INDEX + MATCH / XMATCH", [lookup_id, ret],
                 "Use when you need separate control over finding a position and returning a value.",
                 f"=INDEX({ret}_Range, MATCH({lookup_id}_Cell, {lookup_id}_Range, 0))", level="Intermediate", note="A classic pattern that explains how lookup functions work conceptually.")

    if dimensions:
        d = dimensions[0]
        _add(rows, f"Create a list of unique {d} values", "UNIQUE", [d],
             "Use in modern Excel when you need a dynamic distinct list.",
             f"=UNIQUE({d}_Range)", note="Useful for building validation lists, filters, and supporting analysis tables.")
        if measures:
            _add(rows, f"Extract records matching a condition", "FILTER", [d, measures[0]],
                 "Use when you want a dynamic subset of rows rather than a single lookup value.",
                 f"=FILTER(Data_Range, {d}_Range=criteria)", note="Helpful for drill-down and interactive analysis.")

    if dates:
        date = dates[0]
        _add(rows, f"Extract year or month from {date}", "YEAR / MONTH", [date],
             "Use when you need time components for grouping, filtering, or trend analysis.",
             f"=YEAR({date}_Cell) or =MONTH({date}_Cell)", note="Builds simple time dimensions from a date field.")

    if text_fields:
        text = text_fields[0]
        _add(rows, f"Clean extra spaces in {text}", "TRIM", [text],
             "Use when text contains leading, trailing, or repeated spaces that interfere with matching or grouping.",
             f"=TRIM({text}_Cell)", note="A common cleanup step before lookups and comparisons.")

    if boolean:
        field = boolean[0]
        _add(rows, f"Create a conditional label from {field}", "IF / IFS", [field],
             "Use when records need to be classified into business-friendly labels based on conditions.",
             f'=IF({field}_Cell, "Yes", "No")', note="Useful for creating simple derived categories.")

    # Always provide a small orientation item when there is numerical data.
    if measures:
        _add(rows, "Handle calculation errors cleanly", "IFERROR", [measures[0]],
             "Use when a formula can legitimately produce errors such as division by zero or missing lookup results.",
             f"=IFERROR(formula, \"Not available\")", level="Beginner", note="Makes analytical workbooks easier to read and maintain.")

    result = pd.DataFrame(rows, columns=[
        "Task", "Recommended Function", "Dataset Fields", "When To Use", "Example", "Level", "Why It Matters"
    ])
    return result.drop_duplicates(subset=["Task", "Recommended Function"]).reset_index(drop=True).head(25)
