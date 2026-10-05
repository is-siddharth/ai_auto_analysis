"""Contextual data-quality learning guidance.

The guide is deliberately issue-driven: it returns lessons only for quality
issues actually detected in the current dataset. It does not prescribe a
universal cleaning policy.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _row_value(row: pd.Series, key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    return default if pd.isna(value) else value


def build_quality_guides(quality: dict[str, Any]) -> list[dict[str, str]]:
    """Build dataset-specific quality lessons from an existing quality report."""
    guides: list[dict[str, str]] = []

    summary = quality.get("summary", {})

    # Missing values
    missing = quality.get("missing", pd.DataFrame())
    if isinstance(missing, pd.DataFrame) and not missing.empty:
        affected = missing[missing["Missing Values"] > 0]
        for _, row in affected.iterrows():
            column = str(_row_value(row, "Column"))
            count = int(_row_value(row, "Missing Values", 0))
            pct = float(_row_value(row, "Missing %", 0))
            guides.append({
                "issue": "Missing values",
                "field": column,
                "what": f"{column} has {count:,} missing value(s) ({pct:.2f}% of rows). A missing value means the field has no recorded value for that record.",
                "why": "Missing values can change counts, averages, totals, group comparisons, and model inputs. The impact depends on what the field represents.",
                "example": f"If {column} is used to group records, rows with a missing {column} cannot form a normal category. If it is a measure, an average or total may be based on fewer observations.",
                "method": "Detection: Missing % = missing cells ÷ total rows × 100. No automatic fill formula is applied because the correct replacement depends on the meaning of the field.",
                "fix": "Review the source and decide whether to leave it missing, remove affected records, or impute a value such as median/mode. The assistant does not guess this automatically.",
            })

    # Duplicate rows
    duplicate_rows = int(summary.get("Duplicate Rows", 0) or 0)
    if duplicate_rows:
        guides.append({
            "issue": "Duplicate rows",
            "field": "All columns",
            "what": f"The dataset contains {duplicate_rows:,} exact duplicate row(s).",
            "why": "Duplicates can make the same business event appear more than once and can inflate totals, counts, averages, and rankings.",
            "example": "If one order appears twice and Sales is summed, that order can contribute twice to Total Sales.",
            "method": "Detection: compare complete rows for equality. Cleaning method: keep the first occurrence and remove exact repeats. Excel equivalent: Remove Duplicates.",
            "fix": "Remove only exact duplicates when it is reasonable to assume they are accidental repeats. Near-duplicates require business context and are not automatically removed.",
        })

    # Whitespace
    whitespace = quality.get("whitespace", pd.DataFrame())
    if isinstance(whitespace, pd.DataFrame) and not whitespace.empty:
        for _, row in whitespace.iterrows():
            column = str(_row_value(row, "Column"))
            affected = int(_row_value(row, "Affected Values", 0))
            leading = int(_row_value(row, "Leading Spaces", 0))
            trailing = int(_row_value(row, "Trailing Spaces", 0))
            location_parts = []
            if leading:
                location_parts.append(f"{leading:,} value(s) have an extra space before the text")
            if trailing:
                location_parts.append(f"{trailing:,} value(s) have an extra space after the text")
            location_detail = " and ".join(location_parts)
            guides.append({
                "issue": "Text whitespace",
                "field": column,
                "what": f"{column} contains {affected:,} value(s) with unwanted spaces. Specifically, {location_detail}. For example, `Retail ` has one extra space after `Retail`, even though it can look identical on screen to `Retail`.",
                "why": "Whitespace can create false categories. For example, `Retail` and `Retail ` look the same to a person but can be treated as different text values.",
                "example": "`Retail` and `Retail ` look the same to a person, but the second value has one extra space at the end. A chart, PivotTable, groupby, or lookup can treat them as different values and produce two categories instead of one.",
                "method": "Cleaning method: strip leading/trailing whitespace. Python uses `str.strip()`; the Excel equivalent is `TRIM(text)`.",
                "fix": "Trim the text values, then re-check the category/cardinality profile. This is a deterministic, low-risk transformation.",
            })

    # Blank / unnamed columns
    blank_columns = quality.get("blank_columns", pd.DataFrame())
    if isinstance(blank_columns, pd.DataFrame) and not blank_columns.empty:
        guides.append({
            "issue": "Blank or unnamed columns",
            "field": "Column structure",
            "what": f"{len(blank_columns):,} column(s) have a blank or auto-generated name.",
            "why": "Unnamed columns can be accidental exports, empty separators, or real fields whose names were lost. Treating them as normal data can make analysis confusing.",
            "example": "An `Unnamed: 0` column often comes from an exported dataframe index rather than a business field.",
            "method": "Detection: inspect blank names and common auto-generated names such as `Unnamed: ...`. No column is deleted automatically because the column may still contain meaningful data.",
            "fix": "Inspect the column contents. Rename it if it is meaningful; remove it only when its contents confirm it is an unwanted export artifact.",
        })

    # Duplicate column names
    duplicate_columns = quality.get("duplicate_columns", pd.DataFrame())
    if isinstance(duplicate_columns, pd.DataFrame) and not duplicate_columns.empty:
        guides.append({
            "issue": "Duplicate column names",
            "field": "Column structure",
            "what": f"{len(duplicate_columns):,} column name(s) occur more than once.",
            "why": "Duplicate names make formulas, code, and analysis ambiguous because two different fields share the same label.",
            "example": "Two columns both named `Sales` make it unclear which Sales field a formula or analyst intends to use.",
            "method": "Detection: count occurrences of each column name. Cleaning method: rename columns to unique, meaningful names after inspecting their contents.",
            "fix": "Resolve the names before serious analysis. Do not silently discard one of the columns.",
        })

    # Range violations
    ranges = quality.get("range_validation", pd.DataFrame())
    if isinstance(ranges, pd.DataFrame) and not ranges.empty:
        affected = ranges[ranges["Invalid Values"] > 0]
        for _, row in affected.iterrows():
            column = str(_row_value(row, "Column"))
            expected = str(_row_value(row, "Expected Range"))
            invalid = int(_row_value(row, "Invalid Values", 0))
            guides.append({
                "issue": "Values outside expected range",
                "field": column,
                "what": f"{column} has {invalid:,} value(s) outside the detected expected range of {expected}.",
                "why": "Values outside an expected business range can indicate entry errors, unit mismatches, parsing problems, or legitimate exceptions. Automatically clipping them could destroy information.",
                "example": "A discount stored as 25 instead of 0.25 may be a percentage-vs-decimal mismatch rather than a genuinely extreme discount.",
                "method": "Detection: compare numeric values with the expected bounds. No automatic correction is applied because the correct fix depends on the source and business meaning.",
                "fix": "Inspect the offending values and source definition first. Correct the source or conversion rule when the problem is confirmed.",
            })

    # Type anomalies
    anomalies = quality.get("type_anomalies", pd.DataFrame())
    if isinstance(anomalies, pd.DataFrame) and not anomalies.empty:
        for _, row in anomalies.iterrows():
            column = str(_row_value(row, "Column"))
            pattern = str(_row_value(row, "Detected Pattern"))
            evidence = float(_row_value(row, "Evidence %", 0))
            guides.append({
                "issue": "Storage type anomaly",
                "field": column,
                "what": f"{column} is stored as text even though about {evidence:.2f}% of its non-missing values look like {pattern.lower().replace('mostly ', '')}.",
                "why": "A field stored as text may sort incorrectly, fail numeric aggregation, or prevent date calculations.",
                "example": "Text values `2`, `10`, `100` can sort alphabetically as 10, 100, 2 rather than numerically.",
                "method": "Detection: attempt safe numeric/date parsing and measure the proportion that can be interpreted consistently. Conversion is not automatic when coercion could change values.",
                "fix": "Validate the source format, then convert the field to the correct analytical type. Excel examples include `VALUE()` for numeric text and date conversion when the source format is known.",
            })

    # Categorical consistency
    consistency = quality.get("categorical_consistency", pd.DataFrame())
    if isinstance(consistency, pd.DataFrame) and not consistency.empty:
        for _, row in consistency.iterrows():
            column = str(_row_value(row, "Column"))
            whitespace_variants = int(_row_value(row, "Whitespace Variants", 0))
            case_variants = int(_row_value(row, "Case Variants", 0))
            details = []
            if whitespace_variants:
                details.append(f"{whitespace_variants:,} whitespace variant(s)")
            if case_variants:
                details.append(f"{case_variants:,} case variant(s)")
            guides.append({
                "issue": "Category consistency",
                "field": column,
                "what": f"{column} contains category variants: {', '.join(details)}.",
                "why": "Inconsistent spelling, spaces, or capitalization can split one business category into several groups.",
                "example": "`Retail`, `retail`, and `Retail ` may become three categories in a PivotTable even though they mean the same thing.",
                "method": "Detection compares raw values with whitespace-normalized and case-normalized versions. Common text methods are `TRIM()` for spaces and `LOWER()`/`UPPER()` for case normalization.",
                "fix": "Normalize only when the variants are confirmed to represent the same category. Whitespace trimming is low risk; case normalization should be reviewed for case-sensitive identifiers.",
            })

    # Identifier integrity
    identifiers = quality.get("identifier_integrity", pd.DataFrame())
    if isinstance(identifiers, pd.DataFrame) and not identifiers.empty:
        # Repeated IDs are not automatically treated as an error. In a
        # transaction/line-item dataset, an Order ID or Product ID can
        # legitimately appear many times. Missing IDs are the safer
        # dataset-independent teaching signal.
        affected = identifiers[identifiers["Missing IDs"] > 0]
        for _, row in affected.iterrows():
            column = str(_row_value(row, "Column"))
            missing_ids = int(_row_value(row, "Missing IDs", 0))
            duplicate_ids = int(_row_value(row, "Duplicate Non-null IDs", 0))
            duplicate_note = (
                f" It also has {duplicate_ids:,} repeated non-null ID occurrence(s), "
                "which may be valid when one entity has multiple records."
                if duplicate_ids else ""
            )
            guides.append({
                "issue": "Identifier integrity",
                "field": column,
                "what": f"{column} has {missing_ids:,} missing ID(s)." + duplicate_note,
                "why": "Missing identifiers can make records difficult to join, count, or trace back to their source entity. Repeated IDs are not automatically wrong because dataset grain matters.",
                "example": "A missing Customer ID can prevent a transaction from being reliably connected to a customer. Multiple rows with the same Order ID may be completely valid in a line-item dataset.",
                "method": "Detection: count missing identifier values and inspect repeated non-null IDs in the context of the dataset grain. No automatic repair is attempted because the correct ID must come from the source system.",
                "fix": "Trace missing IDs to the source or business rule. Do not invent IDs simply to make the column unique.",
            })

    # Date logic
    date_logic = quality.get("date_logic", pd.DataFrame())
    if isinstance(date_logic, pd.DataFrame) and not date_logic.empty:
        affected = date_logic[date_logic["Violations"] > 0]
        for _, row in affected.iterrows():
            start = str(_row_value(row, "Start Column"))
            end = str(_row_value(row, "End Column"))
            violations = int(_row_value(row, "Violations", 0))
            guides.append({
                "issue": "Date relationship",
                "field": f"{start} → {end}",
                "what": f"{violations:,} row(s) violate the expected rule `{end} >= {start}`.",
                "why": "Invalid date relationships can produce negative durations, incorrect turnaround times, and misleading trends.",
                "example": f"If {end} is earlier than {start}, a calculated duration such as `{end} - {start}` becomes negative.",
                "method": f"Detection: compare each non-missing pair using `{end} >= {start}`. No automatic date swap is performed because the original fields may contain a source or parsing error.",
                "fix": "Inspect the source dates and parsing format first. Correct the source or conversion rule rather than silently swapping dates.",
            })

    # Outliers
    outliers = quality.get("outliers", pd.DataFrame())
    if isinstance(outliers, pd.DataFrame) and not outliers.empty:
        affected = outliers[outliers["Potential Outliers"] > 0]
        for _, row in affected.iterrows():
            column = str(_row_value(row, "Column"))
            count = int(_row_value(row, "Potential Outliers", 0))
            lower = _row_value(row, "Lower Bound")
            upper = _row_value(row, "Upper Bound")
            guides.append({
                "issue": "Potential outliers",
                "field": column,
                "what": f"{column} has {count:,} value(s) flagged as potential outliers by the IQR rule.",
                "why": "An outlier may be an error, a rare but valid event, or an important business signal. Removing it automatically can bias the analysis.",
                "example": "A very large order may look unusual statistically but could be a genuine high-value transaction worth analyzing rather than deleting.",
                "method": f"Detection: IQR = Q3 − Q1; lower bound = Q1 − 1.5×IQR ({lower}); upper bound = Q3 + 1.5×IQR ({upper}).",
                "fix": "Investigate the flagged records. Correct clear data-entry errors; keep legitimate extreme values. No automatic outlier deletion is performed.",
            })

    # Constant columns are useful as a lesson, but only if they exist.
    constants = quality.get("constant_columns", pd.DataFrame())
    if isinstance(constants, pd.DataFrame) and not constants.empty:
        columns = ", ".join(str(value) for value in constants["Column"].tolist()[:5])
        suffix = "" if len(constants) <= 5 else " and others"
        guides.append({
            "issue": "Constant column",
            "field": columns + suffix,
            "what": f"{len(constants):,} column(s) contain only one distinct non-missing value.",
            "why": "A field with no variation cannot explain differences between records and usually adds little value to comparative analysis.",
            "example": "If Country is `United States` for every row, it cannot distinguish one group from another in this dataset.",
            "method": "Detection: count distinct non-missing values; a count of 1 means there is no observed variation.",
            "fix": "Usually keep the field if it provides useful context, but do not expect it to be useful as a grouping variable. It is not automatically deleted.",
        })

    return guides
