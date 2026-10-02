from src.interpretation.context import (
    build_dataset_context,
)
from src.ai.llm import (
    interpret_dataset,
)


def build_semantic_analysis(
    df,
    classification,
    quality=None,
    relationships=None,
    data_dictionary=None,
    analytical_fields=None,
    analysis_questions=None,
    kpi_recommendations=None,
    excel_function_recommendations=None,
    chart_recommendations=None,
):
    """
    Build the semantic context and optionally send it to the LLM.

    This function is the boundary between deterministic analytics
    and AI interpretation.
    """

    context = build_dataset_context(
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

    interpretation = interpret_dataset(
        context
    )

    return {
        "context": context,
        "interpretation": interpretation,
    }