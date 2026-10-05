from src.ingestion.loader import load_dataset
from src.profiling.classifier import classify_columns
from src.profiling.quality import profile_data_quality
from src.profiling.cleaning import recommend_cleaning_actions
from src.profiling.relationships import detect_date_relationships
from src.interpretation.dictionary import (
    build_data_dictionary,
    identify_analytical_fields,
)
from src.analysis.recommendations import (
    generate_analysis_questions,
)
from src.analysis.kpis import generate_kpi_recommendations
from src.analysis.excel_functions import generate_excel_function_recommendations
from src.analysis.charts import recommend_charts
from src.interpretation.semantic import (
    build_semantic_analysis,
)


def _safe_relationship_detection(df):
    """
    Relationship detection should never prevent the rest of the
    dataset from being analyzed.
    """
    try:
        return detect_date_relationships(df)
    except Exception:
        return None


def _safe_quality_profile(df):
    """
    Quality profiling should not destroy the main pipeline.
    """
    try:
        return profile_data_quality(df)
    except Exception as exc:
        return {
            "error": str(exc),
            "summary": {
                "Rows": len(df),
                "Columns": len(df.columns),
            },
        }


def _safe_semantic_analysis(
    df,
    classification,
    quality,
    relationships,
    data_dictionary,
    analytical_fields,
    analysis_questions,
    kpi_recommendations,
    excel_function_recommendations,
    chart_recommendations,
):
    """
    Semantic analysis is optional.

    If the LLM is not configured or unavailable, the deterministic
    pipeline still succeeds.
    """

    try:

        return build_semantic_analysis(
            df=df,
            classification=classification,
            quality=quality,
            relationships=relationships,
            data_dictionary=data_dictionary,
            analytical_fields=analytical_fields,
            analysis_questions=analysis_questions,
            kpi_recommendations=kpi_recommendations,
            excel_function_recommendations=excel_function_recommendations,
            chart_recommendations=chart_recommendations,
        )

    except Exception as exc:

        return {
            "context": None,
            "interpretation": {
                "enabled": False,
                "success": False,
                "message": (
                    f"Semantic analysis unavailable: {exc}"
                ),
                "model": None,
                "data": None,
            },
        }


def analyze_dataframe(df, include_semantic=True):
    """Run the full deterministic pipeline and optionally semantic AI."""

    if df is None or not hasattr(df, "columns"):
        raise ValueError("The dataset could not be analyzed.")

    classification = classify_columns(df)

    # ---------------------------------------------------------------
    # 3. Quality
    # ---------------------------------------------------------------

    quality = _safe_quality_profile(df)
    cleaning_recommendations = recommend_cleaning_actions(df)

    # ---------------------------------------------------------------
    # 4. Relationships
    # ---------------------------------------------------------------

    relationships = _safe_relationship_detection(df)

    # ---------------------------------------------------------------
    # 5. Data dictionary
    # ---------------------------------------------------------------

    data_dictionary = build_data_dictionary(
        df,
        classification,
    )

    # ---------------------------------------------------------------
    # 6. Analytical field groups
    # ---------------------------------------------------------------

    analytical_fields = identify_analytical_fields(
        classification
    )

    # ---------------------------------------------------------------
    # 7. Deterministic recommendations
    # ---------------------------------------------------------------

    analysis_questions = generate_analysis_questions(
        df,
        analytical_fields,
    )

    # ---------------------------------------------------------------
    # 8. KPI recommendations
    # ---------------------------------------------------------------

    kpi_recommendations = generate_kpi_recommendations(
        df,
        analytical_fields,
    )

    # ---------------------------------------------------------------
    # 9. Excel learning recommendations
    # ---------------------------------------------------------------

    excel_function_recommendations = generate_excel_function_recommendations(
        df,
        analytical_fields,
    )

    # ---------------------------------------------------------------
    # 10. Chart recommendations
    # ---------------------------------------------------------------

    chart_recommendations = recommend_charts(
        analysis_questions,
    )

    # ---------------------------------------------------------------
    # 11. Semantic / AI interpretation
    # ---------------------------------------------------------------

    if include_semantic:
        semantic_analysis = _safe_semantic_analysis(
            df=df,
            classification=classification,
            quality=quality,
            relationships=relationships,
            data_dictionary=data_dictionary,
            analytical_fields=analytical_fields,
            analysis_questions=analysis_questions,
            kpi_recommendations=kpi_recommendations,
            excel_function_recommendations=excel_function_recommendations,
            chart_recommendations=chart_recommendations,
        )
    else:
        semantic_analysis = {
            "context": None,
            "interpretation": {
                "enabled": False,
                "success": False,
                "message": "Semantic AI skipped for deterministic validation.",
                "model": None,
                "data": None,
            },
        }

    # ---------------------------------------------------------------
    # 12. Stable result contract
    # ---------------------------------------------------------------

    return {
        "data": df,
        "classification": classification,
        "quality": quality,
        "cleaning_recommendations": cleaning_recommendations,
        "relationships": relationships,
        "data_dictionary": data_dictionary,
        "analytical_fields": analytical_fields,
        "analysis_questions": analysis_questions,
        "kpi_recommendations": kpi_recommendations,
        "excel_function_recommendations": excel_function_recommendations,
        "chart_recommendations": chart_recommendations,
        "semantic_analysis": semantic_analysis,
    }

def analyze_dataset(file_path):
    """Load a dataset and run the full deterministic + semantic pipeline."""
    df = load_dataset(file_path)
    if df is None:
        raise ValueError("The dataset could not be loaded.")
    return analyze_dataframe(df)
