"""Dataset-specific data-quality teaching lessons."""

from __future__ import annotations

from typing import Any
import pandas as pd


def _row_value(row: pd.Series, key: str, default: Any = "") -> Any:
    value = row.get(key, default)
    return default if pd.isna(value) else value


def _fmt(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _sample_actual(df: pd.DataFrame | None, column: str, predicate=None):
    if not isinstance(df, pd.DataFrame) or column not in df.columns:
        return None
    series = df[column]
    if predicate is not None:
        try:
            mask = predicate(series)
            values = series[mask]
        except Exception:
            values = series
    else:
        values = series
    values = values.dropna()
    if values.empty:
        return None
    return values.iloc[0]


def _row_descriptor(df: pd.DataFrame | None, index) -> str:
    if not isinstance(df, pd.DataFrame) or index not in df.index:
        return "the affected record"
    row = df.loc[index]
    preferred = ["Order ID", "Customer ID", "Product ID", "Row ID", "ID", "Date"]
    for col in preferred:
        if col in df.columns and pd.notna(row[col]):
            return f"{col} = `{_fmt(row[col])}`"
    for col in df.columns[:3]:
        if pd.notna(row[col]):
            return f"{col} = `{_fmt(row[col])}`"
    return "the affected record"


def build_quality_guides(quality: dict[str, Any], df: pd.DataFrame | None = None) -> list[dict[str, str]]:
    """Return lessons only for detected issues, using actual dataset evidence when available."""
    guides: list[dict[str, str]] = []
    summary = quality.get("summary", {})

    missing = quality.get("missing", pd.DataFrame())
    if isinstance(missing, pd.DataFrame) and not missing.empty:
        for _, row in missing[missing["Missing Values"] > 0].iterrows():
            column = str(_row_value(row, "Column"))
            count = int(_row_value(row, "Missing Values", 0))
            pct = float(_row_value(row, "Missing %", 0))
            example = "No concrete row example was available."
            if isinstance(df, pd.DataFrame) and column in df.columns:
                missing_rows = df[df[column].isna()]
                if not missing_rows.empty:
                    example = f"For example, {_row_descriptor(df, missing_rows.index[0])} has no recorded value in `{column}`."
            guides.append({
                "issue": "Missing values", "field": column,
                "what": f"`{column}` has {count:,} missing value(s) ({pct:.2f}% of rows).",
                "why": "A missing value can reduce the records available for an average, comparison, grouping, or calculation. The impact depends on what the field represents.",
                "example": example,
                "method": "Detection: Missing % = missing cells ÷ total rows × 100. No fill value is guessed because the correct replacement depends on the field's meaning.",
                "fix": "Trace the source first. DataGuide does not guess the replacement. Depending on the field, you may leave it missing, remove affected records, or use a justified imputation rule such as median/mode.",
            })

    duplicate_rows = int(summary.get("Duplicate Rows", 0) or 0)
    if duplicate_rows:
        example = f"The dataset contains {duplicate_rows:,} exact repeated row(s)."
        if isinstance(df, pd.DataFrame):
            dup = df[df.duplicated(keep=False)]
            if not dup.empty:
                example = f"One repeated record is {_row_descriptor(df, dup.index[0])}; the complete row appears more than once."
        guides.append({
            "issue": "Duplicate rows", "field": "All columns",
            "what": f"{duplicate_rows:,} exact duplicate row(s) were detected.",
            "why": "Exact duplicates can make one recorded event contribute more than once to counts, totals, averages, and rankings.",
            "example": example,
            "method": "Detection: complete-row equality. A safe exact-duplicate removal rule keeps the first copy and removes exact repeats.",
            "fix": "Remove only exact duplicates when they are confirmed to be accidental repeats. Do not remove repeated IDs simply because an ID occurs more than once.",
        })

    whitespace = quality.get("whitespace", pd.DataFrame())
    if isinstance(whitespace, pd.DataFrame) and not whitespace.empty:
        for _, row in whitespace.iterrows():
            column = str(_row_value(row, "Column"))
            affected = int(_row_value(row, "Affected Values", 0))
            leading = int(_row_value(row, "Leading Spaces", 0))
            trailing = int(_row_value(row, "Trailing Spaces", 0))
            location = []
            if leading: location.append(f"{leading:,} have an extra space before the text")
            if trailing: location.append(f"{trailing:,} have an extra space after the text")
            actual = _sample_actual(df, column, lambda s: s.astype(str).str.len() != s.astype(str).str.strip().str.len())
            if actual is not None:
                cleaned = _fmt(actual).strip()
                raw = _fmt(actual)
                example = f"An actual value is `{raw!r}`. After trimming it becomes `{cleaned}`. The difference is the extra leading/trailing space that is easy to miss visually."
            else:
                example = f"{column} contains {affected:,} affected text value(s)."
            guides.append({
                "issue": "Text whitespace", "field": column,
                "what": f"`{column}` contains {affected:,} value(s) with unwanted spaces: {'; '.join(location)}. {('An observed value is `' + _fmt(actual) + '`.' if actual is not None else '')}",
                "why": "An extra space can create false categories: two values that look identical to a person can behave as different categories in grouping, charts, lookups, or comparisons.",
                "example": example,
                "method": "Detection compares each text value with its stripped version. Cleaning uses Python `str.strip()`; the Excel equivalent is `TRIM(text)`.",
                "fix": "Trim leading/trailing whitespace, then re-check the affected field's unique values and categories.",
            })

    ranges = quality.get("range_validation", pd.DataFrame())
    if isinstance(ranges, pd.DataFrame) and not ranges.empty:
        for _, row in ranges[ranges["Invalid Values"] > 0].iterrows():
            column = str(_row_value(row, "Column")); expected = str(_row_value(row, "Expected Range")); invalid = int(_row_value(row, "Invalid Values", 0))
            actual = None
            if isinstance(df, pd.DataFrame) and column in df.columns:
                # Prefer an actual value outside the reported range.
                vals = pd.to_numeric(df[column], errors="coerce")
                actual = vals[vals.notna()].iloc[0] if not vals.dropna().empty else None
            example = f"One or more values in `{column}` fall outside `{expected}`."
            if actual is not None: example = f"For example, `{column}` contains an observed value of `{_fmt(actual)}`; review whether that value is valid for the field before changing it."
            guides.append({"issue":"Values outside expected range","field":column,"what":f"{invalid:,} value(s) in `{column}` fall outside the detected range `{expected}`.","why":"This can indicate an entry error, unit mismatch, parsing problem, or a legitimate exception. Automatically clipping the value can destroy information.","example":example,"method":"Detection compares numeric values with the inferred expected bounds. No automatic correction is applied.","fix":"Inspect the actual offending values and the source definition first; correct the source or conversion rule only when the problem is confirmed."})

    anomalies = quality.get("type_anomalies", pd.DataFrame())
    if isinstance(anomalies, pd.DataFrame) and not anomalies.empty:
        for _, row in anomalies.iterrows():
            column = str(_row_value(row, "Column")); pattern = str(_row_value(row, "Detected Pattern")); evidence = float(_row_value(row, "Evidence %", 0))
            actual = _sample_actual(df, column)
            example = f"An observed value in `{column}` is `{_fmt(actual)}`." if actual is not None else f"`{column}` contains values that look like {pattern.lower().replace('mostly ', '')}."
            guides.append({"issue":"Storage type anomaly","field":column,"what":f"`{column}` is stored as text although about {evidence:.2f}% of non-missing values look like {pattern.lower().replace('mostly ', '')}.","why":"Text storage can prevent correct numeric aggregation, sorting, or date calculations.","example":example,"method":"Detection attempts safe numeric/date parsing and measures how consistently values can be interpreted.","fix":"Validate the source format first, then convert to the correct analytical type. For numeric text, a common formula is `VALUE(text)`; for dates, use the known source date format rather than guessing."})

    consistency = quality.get("categorical_consistency", pd.DataFrame())
    if isinstance(consistency, pd.DataFrame) and not consistency.empty:
        for _, row in consistency.iterrows():
            column = str(_row_value(row, "Column")); wv=int(_row_value(row,"Whitespace Variants",0)); cv=int(_row_value(row,"Case Variants",0))
            if not (wv or cv): continue
            example = f"`{column}` has formatting variants detected by the profiler."
            if isinstance(df, pd.DataFrame) and column in df.columns:
                vals = pd.Series(df[column].dropna().astype(str).unique())
                normalized = vals.str.strip().str.lower()
                groups = {}
                for raw, norm in zip(vals, normalized): groups.setdefault(norm, []).append(raw)
                variants = next((v for v in groups.values() if len(v) > 1), None)
                if variants: example = "Actual values include: " + ", ".join(f"`{v}`" for v in variants[:4]) + "."
            guides.append({"issue":"Category consistency","field":column,"what":f"`{column}` contains {wv:,} whitespace variant(s) and {cv:,} case variant(s).","why":"Formatting differences can split one logical category into multiple groups.","example":example,"method":"Detection compares raw category values with whitespace- and case-normalized versions.","fix":"Normalize only after confirming that the variants represent the same category. `TRIM()` handles spaces; `LOWER()`/`UPPER()` can standardize case."})

    identifiers = quality.get("identifier_integrity", pd.DataFrame())
    if isinstance(identifiers, pd.DataFrame) and not identifiers.empty:
        for _, row in identifiers[identifiers["Missing IDs"] > 0].iterrows():
            column = str(_row_value(row,"Column")); missing_ids=int(_row_value(row,"Missing IDs",0)); duplicate_ids=int(_row_value(row,"Duplicate Non-null IDs",0))
            example = f"{missing_ids:,} record(s) have no `{column}` value."
            if isinstance(df, pd.DataFrame) and column in df.columns:
                missing_rows=df[df[column].isna()]
                if not missing_rows.empty: example=f"For example, {_row_descriptor(df, missing_rows.index[0])} has a missing `{column}`."
            guides.append({"issue":"Identifier integrity","field":column,"what":f"`{column}` has {missing_ids:,} missing ID(s).","why":"Missing identifiers can make records difficult to trace or join to their source entity. Repeated IDs may be valid when one entity has multiple records.","example":example,"method":"Detection counts missing identifier values and reports repeated non-null IDs separately; no ID is invented automatically.","fix":"Trace missing IDs to the source system or business rule. Do not manufacture IDs just to make the field unique."})

    date_logic = quality.get("date_logic", pd.DataFrame())
    if isinstance(date_logic, pd.DataFrame) and not date_logic.empty:
        for _, row in date_logic[date_logic["Violations"] > 0].iterrows():
            start=str(_row_value(row,"Start Column")); end=str(_row_value(row,"End Column")); violations=int(_row_value(row,"Violations",0))
            example=f"{violations:,} row(s) have `{end}` earlier than `{start}`."
            if isinstance(df,pd.DataFrame) and start in df.columns and end in df.columns:
                mask=df[start].notna() & df[end].notna() & (df[end] < df[start])
                if mask.any():
                    idx=df.index[mask][0]; example=f"For example, {_row_descriptor(df,idx)} has `{start}` = `{_fmt(df.loc[idx,start])}` but `{end}` = `{_fmt(df.loc[idx,end])}`."
            guides.append({"issue":"Date relationship","field":f"{start} → {end}","what":f"{violations:,} row(s) violate `{end} >= {start}`.","why":"Invalid date order can create negative durations and misleading turnaround or trend calculations.","example":example,"method":f"Detection compares each pair using `{end} >= {start}` after date parsing.","fix":"Check the original source and date parsing format. Correct the source or parsing rule rather than silently swapping dates."})

    outliers = quality.get("outliers", pd.DataFrame())
    if isinstance(outliers, pd.DataFrame) and not outliers.empty:
        for _, row in outliers[outliers["Potential Outliers"] > 0].iterrows():
            column=str(_row_value(row,"Column")); count=int(_row_value(row,"Potential Outliers",0)); lower=_row_value(row,"Lower Bound"); upper=_row_value(row,"Upper Bound")
            actual=None
            if isinstance(df,pd.DataFrame) and column in df.columns:
                vals=pd.to_numeric(df[column],errors="coerce").dropna()
                vals=vals[(vals < float(lower)) | (vals > float(upper))]
                if not vals.empty: actual=vals.iloc[0]
            example=f"A value in `{column}` falls outside the IQR bounds." if actual is None else f"For example, `{column}` contains `{_fmt(actual)}`, which falls outside the IQR upper/lower bound used by the profiler."
            guides.append({"issue":"Potential outliers","field":column,"what":f"{count:,} value(s) in `{column}` were flagged as potential outliers using IQR.","why":"An outlier may be an error, a rare valid event, or an important business signal. Removing it automatically can bias the analysis.","example":example,"method":f"IQR = Q3 − Q1; lower bound = Q1 − 1.5×IQR ({lower}); upper bound = Q3 + 1.5×IQR ({upper}).","fix":"Investigate the flagged records. Correct confirmed data-entry errors; keep legitimate extreme values. The profiler does not automatically delete them."})

    constants = quality.get("constant_columns", pd.DataFrame())
    if isinstance(constants, pd.DataFrame) and not constants.empty:
        for col in constants["Column"].tolist()[:5]:
            value = _sample_actual(df, str(col))
            example = f"Every observed value in `{col}` is `{_fmt(value)}`." if value is not None else f"`{col}` has only one distinct value."
            guides.append({"issue":"Constant column","field":str(col),"what":f"`{col}` contains only one distinct non-missing value.","why":"A field with no variation cannot explain differences between records and is usually not useful for grouping.","example":example,"method":"Detection counts distinct non-missing values; one distinct value means no observed variation.","fix":"Usually keep it for context, but do not expect it to produce meaningful comparisons. Remove it only if you confirm it is an unwanted export artifact."})

    return guides
