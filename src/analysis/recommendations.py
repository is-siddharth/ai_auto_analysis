import pandas as pd


OUTPUT_COLUMNS = [
    "Question",
    "Analysis Type",
    "Measure",
    "Dimension",
    "Date Column",
    "Priority",
    "Rationale",
]


def _add_question(
    rows,
    question,
    analysis_type,
    measure=None,
    dimension=None,
    date_column=None,
    priority="Medium",
    rationale=None,
):
    rows.append(
        {
            "Question": question,
            "Analysis Type": analysis_type,
            "Measure": measure,
            "Dimension": dimension,
            "Date Column": date_column,
            "Priority": priority,
            "Rationale": rationale,
        }
    )


def _safe_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _valid_columns(values, columns):
    return [value for value in values if value in columns]



def _has_iqr_outliers(df, field):
    if field not in df.columns or not pd.api.types.is_numeric_dtype(df[field]):
        return False
    series = pd.to_numeric(df[field], errors="coerce").dropna()
    if len(series) < 4:
        return False
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return False
    return bool(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).any())


def _field_groups(analytical_fields, columns):
    fields = analytical_fields or {}

    return {
        "measures": _valid_columns(_safe_list(fields.get("measures")), columns),
        "numerical_attributes": _valid_columns(
            _safe_list(fields.get("numerical_attributes")), columns
        ),
        "rates": _valid_columns(_safe_list(fields.get("rates")), columns),
        "scores": _valid_columns(_safe_list(fields.get("scores")), columns),
        "ordinal": _valid_columns(_safe_list(fields.get("ordinal")), columns),
        "dimensions": _valid_columns(_safe_list(fields.get("dimensions")), columns),
        "dates": _valid_columns(_safe_list(fields.get("dates")), columns),
        "text": _valid_columns(_safe_list(fields.get("text")), columns),
        "ids": _valid_columns(_safe_list(fields.get("ids")), columns),
        "boolean": _valid_columns(_safe_list(fields.get("boolean")), columns),
        "geographic": _valid_columns(_safe_list(fields.get("geographic")), columns),
        "unclassified": _valid_columns(_safe_list(fields.get("unclassified")), columns),
    }


def generate_analysis_questions(df, analytical_fields):
    """Generate deterministic, role-aware analysis recommendations."""

    columns = list(df.columns)
    groups = _field_groups(analytical_fields, columns)

    measures = groups["measures"]
    attributes = groups["numerical_attributes"]
    rates = groups["rates"]
    scores = groups["scores"]
    ordinal = groups["ordinal"]
    dimensions = groups["dimensions"]
    dates = groups["dates"]
    text_fields = groups["text"]
    boolean_fields = groups["boolean"]
    unclassified = groups["unclassified"]

    recommendations = []

    # Core aggregatable measures.
    for measure in measures[:4]:
        _add_question(
            recommendations,
            f"What is the overall profile of {measure}?",
            "Overall Profile",
            measure=measure,
            priority="High",
            rationale=(
                "Summarize an aggregatable numerical measure using totals, "
                "central tendency, range, and record count."
            ),
        )

    # Non-aggregatable numeric attributes.
    for field in attributes[:2]:
        _add_question(
            recommendations,
            f"What does the distribution of {field} look like?",
            "Attribute Distribution",
            measure=field,
            priority="High",
            rationale=(
                "This numeric field describes observations or entities and is "
                "more useful as a distribution than as a summed measure."
            ),
        )

    # Rates / percentages.
    for field in rates[:2]:
        _add_question(
            recommendations,
            f"What is the typical level and distribution of {field}?",
            "Rate Profile",
            measure=field,
            priority="High",
            rationale=(
                "Rates and percentages should normally be interpreted through "
                "their typical level, range, and distribution rather than summed."
            ),
        )

    # Scores / ratings.
    for field in scores[:2]:
        _add_question(
            recommendations,
            f"How are {field} values distributed?",
            "Score Profile",
            measure=field,
            priority="High",
            rationale=(
                "Scores and ratings are better understood through their "
                "distribution and central tendency."
            ),
        )

    # Distribution and outlier learning. Only recommend this when the
    # dataset actually contains IQR-flagged values, so the lesson is contextual.
    outlier_candidates = []
    for field in measures[:3] + attributes[:2] + rates[:2] + scores[:2]:
        if field not in outlier_candidates and _has_iqr_outliers(df, field):
            outlier_candidates.append(field)
    for field in outlier_candidates[:2]:
        _add_question(
            recommendations,
            f"What does the distribution of {field} look like, and where are the potential outliers?",
            "Distribution & Outliers",
            measure=field,
            priority="High",
            rationale=(
                "Use the distribution and IQR rule together to learn how the field is spread "
                "and which observations sit beyond the statistical outlier bounds."
            ),
        )

    # Dimension comparisons with true measures.
    for dimension in dimensions[:4]:
        for measure in measures[:2]:
            _add_question(
                recommendations,
                f"How does {measure} vary across {dimension}?",
                "Dimension Comparison",
                measure=measure,
                dimension=dimension,
                priority="High",
                rationale=(
                    "Compare an aggregatable measure across meaningful groups."
                ),
            )

    # Ranking.
    if measures:
        for dimension in dimensions[:3]:
            measure = measures[0]
            _add_question(
                recommendations,
                f"Which {dimension} values have the highest {measure}?",
                "Ranking",
                measure=measure,
                dimension=dimension,
                priority="High",
                rationale=(
                    "Rank groups by the primary numerical measure to identify "
                    "the largest contributors or highest-volume groups."
                ),
            )

    # Contribution.
    if dimensions and measures:
        dimension = dimensions[0]
        measure = measures[0]
        _add_question(
            recommendations,
            f"How much does each {dimension} contribute to total {measure}?",
            "Contribution",
            measure=measure,
            dimension=dimension,
            priority="Medium",
            rationale=(
                "Show each group's share of the overall measure."
            ),
        )

    # Time trends.
    for date_column in dates[:2]:
        for measure in measures[:2]:
            _add_question(
                recommendations,
                f"How has {measure} changed over time?",
                "Time Trend",
                measure=measure,
                date_column=date_column,
                priority="High",
                rationale=(
                    "Track changes in an aggregatable measure across the available "
                    "time period."
                ),
            )

        for field in rates[:1] + scores[:1]:
            _add_question(
                recommendations,
                f"How has {field} changed over time?",
                "Rate Trend" if field in rates else "Score Trend",
                measure=field,
                date_column=date_column,
                priority="Medium",
                rationale=(
                    "Rates and scores can reveal temporal changes without treating "
                    "them as additive quantities."
                ),
            )

    # Attribute vs outcome.
    if measures:
        for attribute in attributes[:2]:
            _add_question(
                recommendations,
                f"How does {measures[0]} vary across different {attribute} levels?",
                "Attribute Comparison",
                measure=measures[0],
                dimension=attribute,
                priority="Medium",
                rationale=(
                    "Examine whether the primary outcome differs across ranges "
                    "of a numerical attribute."
                ),
            )

    # Ordinal comparisons.
    if measures:
        for field in ordinal[:2]:
            _add_question(
                recommendations,
                f"How is {measures[0]} distributed across {field} levels?",
                "Ordinal Comparison",
                measure=measures[0],
                dimension=field,
                priority="Medium",
                rationale=(
                    "Compare an outcome across naturally ordered categories."
                ),
            )

    # Boolean comparisons.
    if measures:
        for field in boolean_fields[:2]:
            _add_question(
                recommendations,
                f"How does {measures[0]} differ between {field} states?",
                "Boolean Comparison",
                measure=measures[0],
                dimension=field,
                priority="Medium",
                rationale=(
                    "Compare an outcome between the two states of a boolean field."
                ),
            )

    # Geography is useful even when classified separately.
    if measures:
        for field in groups["geographic"][:2]:
            _add_question(
                recommendations,
                f"How does {measures[0]} vary geographically by {field}?",
                "Geographic Comparison",
                measure=measures[0],
                dimension=field,
                priority="Medium",
                rationale=(
                    "Use a geographic field to identify location-based differences."
                ),
            )

    # Text and uncertain fields are routed toward semantic interpretation.
    for field in text_fields[:2]:
        _add_question(
            recommendations,
            f"What analytical meaning does {field} appear to have?",
            "Semantic Interpretation",
            priority="Low",
            rationale=(
                "Free-form text usually requires semantic interpretation before "
                "specific numerical analysis can be proposed."
            ),
        )

    for field in unclassified[:3]:
        _add_question(
            recommendations,
            f"What role does {field} play in this dataset?",
            "Semantic Interpretation",
            priority="Low",
            rationale=(
                "The deterministic classifier could not confidently assign an "
                "analytical role."
            ),
        )

    # Datasets without measures still need useful questions.
    if not measures:
        if dimensions:
            _add_question(
                recommendations,
                "What are the major categories or segments represented in this dataset?",
                "Dataset Structure",
                priority="Medium",
                rationale=(
                    "No aggregatable numerical measures were detected, so structural "
                    "exploration is more appropriate."
                ),
            )

        if dates:
            _add_question(
                recommendations,
                "What time period does this dataset cover?",
                "Time Coverage",
                date_column=dates[0],
                priority="Medium",
                rationale=(
                    "A date field exists even though no aggregatable measure was "
                    "confidently identified."
                ),
            )

        if attributes:
            _add_question(
                recommendations,
                f"What is the distribution of {attributes[0]}?",
                "Attribute Distribution",
                measure=attributes[0],
                priority="Medium",
                rationale=(
                    "A numerical attribute can still support distribution analysis "
                    "without being treated as an additive measure."
                ),
            )

        if rates:
            _add_question(
                recommendations,
                f"What is the typical level and distribution of {rates[0]}?",
                "Rate Profile",
                measure=rates[0],
                priority="Medium",
                rationale=(
                    "A rate or percentage can be analyzed without requiring a "
                    "traditional numerical measure."
                ),
            )

        if text_fields:
            _add_question(
                recommendations,
                "What themes or semantic patterns are present in the text fields?",
                "Text Exploration",
                priority="Medium",
                rationale=(
                    "The dataset contains descriptive text that may require semantic analysis."
                ),
            )

    result = pd.DataFrame(recommendations, columns=OUTPUT_COLUMNS)

    if len(result) > 20:
        result = result.head(20).copy()

    return result.reset_index(drop=True)
