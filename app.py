import hashlib
import os
import tempfile

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from src.pipeline import analyze_dataset, analyze_dataframe
from src.analysis.engine import run_analysis
from src.analysis.kpis import calculate_kpi
from src.analysis.filters import recommend_filters
from src.analysis.charts import CHART_OPTIONS
from src.profiling.cleaning import apply_cleaning_actions, automated_cleaning_action_ids
from src.profiling.quality_guide import build_quality_guides
from src.ai.qa import ask_question


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DataGuide",
    page_icon="🧭",
    layout="wide"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _has_rows(value):
    """Return True when a quality-result object contains at least one row.

    Quality checks may return pandas DataFrames, lists, dictionaries, or None.
    Never evaluate a pandas DataFrame directly in a boolean expression.
    """
    if value is None:
        return False

    if isinstance(value, pd.DataFrame):
        return not value.empty

    if isinstance(value, pd.Series):
        return not value.empty

    if isinstance(value, (list, tuple, set, dict, str)):
        return len(value) > 0

    try:
        return bool(value)
    except (TypeError, ValueError):
        return False

def display_field_group(
    title,
    fields
):
    """
    Display an analytical field group as visual field chips.
    """

    st.markdown(
        f"#### {title}"
    )

    if not fields:

        st.caption(
            "No fields detected."
        )

        return


    field_html = ""


    for field in fields:

        field_html += f"""
        <span style="
            display: inline-block;
            padding: 6px 12px;
            margin: 3px 5px 3px 0;
            border: 1px solid #d1d5db;
            border-radius: 14px;
            background-color: #f8fafc;
            color: #1f2937;
            font-size: 14px;
            line-height: 1.4;
        ">
            {field}
        </span>
        """


    st.markdown(
        field_html,
        unsafe_allow_html=True
    )


def _available_visual_choices(analysis_type, result):
    """Return chart choices that are both educational and compatible with the result."""
    choices = list(CHART_OPTIONS.get(analysis_type, []))
    if not choices:
        return ["Table / KPI"]

    table = result.get("table", pd.DataFrame())
    x_column = result.get("x")
    if x_column and x_column in table.columns:
        category_count = int(table[x_column].nunique(dropna=True))
        if category_count > 10:
            choices = [c for c in choices if c not in {"Pie Chart", "Donut Chart"}]

    return choices or ["Table / KPI"]


def _render_analysis_chart(result, chart_choice):
    """Render a user-selected visual from deterministic analysis output."""
    table = result.get("table")
    chart_data = result.get("chart_data", table)
    x_column = result.get("x")
    y_column = result.get("y")

    if chart_choice in {None, "Table / KPI"} or chart_data is None:
        return

    if chart_choice in {"Histogram", "Box Plot"}:
        if not x_column or x_column not in chart_data.columns:
            return
        series = pd.to_numeric(chart_data[x_column], errors="coerce").dropna()
        if series.empty:
            return
        fig, ax = plt.subplots(figsize=(9, 4.8))
        if chart_choice == "Histogram":
            ax.hist(series, bins=min(20, max(5, int(series.nunique() ** 0.5))))
            ax.set_xlabel(x_column)
            ax.set_ylabel("Frequency")
            ax.set_title(f"Distribution of {x_column}")
        else:
            ax.boxplot(series, vert=False)
            ax.set_xlabel(x_column)
            ax.set_yticks([1])
            ax.set_yticklabels([x_column])
            ax.set_title(f"Box Plot — {x_column}")
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        return

    if not x_column or x_column not in chart_data.columns:
        return

    if y_column and y_column in chart_data.columns:
        frame = chart_data[[x_column, y_column]].dropna().copy()
    else:
        frame = chart_data[[x_column]].dropna().copy()
        frame["Count"] = 1
        y_column = "Count"

    if frame.empty:
        return

    if chart_choice in {"Pie Chart", "Donut Chart"}:
        grouped = frame.groupby(x_column, dropna=False)[y_column].sum().sort_values(ascending=False)
        grouped = grouped.head(10)
        if grouped.empty or (grouped < 0).any() or grouped.sum() <= 0:
            st.warning(
                "A pie/donut chart is not appropriate for this result because the values include negative amounts or do not form a positive whole. "
                "Use a bar/column chart instead."
            )
            return
        fig, ax = plt.subplots(figsize=(7, 5))
        wedges, _ = ax.pie(grouped.values, startangle=90)
        if chart_choice == "Donut Chart":
            centre = plt.Circle((0, 0), 0.60, fc="white")
            ax.add_artist(centre)
        ax.legend(wedges, [str(v) for v in grouped.index], loc="center left", bbox_to_anchor=(1, 0.5))
        ax.set_title(f"{chart_choice} — {x_column}")
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        return

    if chart_choice == "Line Chart":
        frame = frame.sort_values(x_column).set_index(x_column)
        st.line_chart(frame[[y_column]], use_container_width=True)
        return

    frame = frame.sort_values(y_column, ascending=False)
    if chart_choice == "Horizontal Bar Chart":
        frame = frame.head(min(15, len(frame)))
        frame = frame.set_index(x_column)
        st.bar_chart(frame[[y_column]], use_container_width=True)
        return

    # Bar/column are both represented with Streamlit's bar chart; the choice
    # remains visible to the learner even though the rendering is equivalent.
    frame = frame.head(15).set_index(x_column)
    st.bar_chart(frame[[y_column]], use_container_width=True)


def display_analysis_result(result, analysis_type=None, chart_choice=None):
    """Display a calculated result and an optional learner-selected visual."""
    table = result.get("table")
    if table is None or table.empty:
        st.info("The selected analysis did not produce any results.")
        return

    st.dataframe(table, use_container_width=True)

    if analysis_type is None:
        return

    choices = _available_visual_choices(analysis_type, result)
    if choices == ["Table / KPI"]:
        return

    if chart_choice is None:
        chart_choice = choices[0]

    _render_analysis_chart(result, chart_choice)


# ============================================================

def _semantic_data(analysis_result):
    return analysis_result.get("semantic_analysis", {}).get("interpretation", {}).get("data") or {}


def _column_interpretation(column, semantic_data, data_dictionary):
    for item in semantic_data.get("important_fields", []):
        if item.get("column") == column and item.get("meaning"):
            return item["meaning"], item.get("confidence", "Medium")
    match = data_dictionary.loc[data_dictionary["Column"] == column]
    if not match.empty:
        row = match.iloc[0]
        return row.get("Description", "This field's role could not be interpreted confidently."), "Deterministic"
    return "This field's meaning could not be interpreted confidently from the available evidence.", "Low"


def _quality_status(quality):
    summary = quality.get("summary", {})
    return (int(summary.get("Total Missing Values", 0) or 0) > 0
            or int(summary.get("Duplicate Rows", 0) or 0) > 0
            or _has_rows(quality.get("whitespace"))
            or _has_rows(quality.get("range_validation"))
            or _has_rows(quality.get("type_anomalies"))
            or _has_rows(quality.get("outliers")))


# ============================================================
# APPLICATION HEADER
# ============================================================

st.title("DataGuide")
st.caption("Understand your data. Learn what it means. Check its quality. Then analyze it with confidence.")

with st.sidebar:
    st.header("Your journey")
    steps = [
        ("1", "Overview", "Get your bearings"),
        ("2", "Data Guide", "Understand the story inside the fields"),
        ("3", "Data Quality", "Learn what needs attention"),
        ("4", "Data Analysis", "Explore the questions worth asking"),
    ]
    for number, title, description in steps:
        st.markdown(f"**{number}. {title}**")
        st.caption(description)
    st.divider()
    st.caption("Python establishes the evidence. AI helps explain what that evidence means.")

st.header("Upload your dataset")
uploaded_file = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.markdown("### Start with a file, not a blank canvas")
    st.write("DataGuide takes you from a raw dataset to a clear understanding of what the data is saying. First you see what is here, then you learn what the fields mean, understand quality trade-offs, and finally explore the analysis that makes sense for this dataset.")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown("**Understand**\n\nRows, columns, types, field roles, dates, measures and dimensions.")
    c2.markdown("**Check**\n\nMissing values, duplicates, whitespace, ranges, type issues and IQR outliers.")
    c3.markdown("**Ask**\n\nWhat is this dataset? What does this field mean? What should I analyze?")
    c4.markdown("**Analyze**\n\nRecommended KPIs, questions, calculations, visuals and guided exploration.")
    st.info("Upload a dataset to begin. The DataGuide assistant will stay available in the bottom-right corner.")
    st.stop()

# TEMPORARY FILE
# ============================================================

file_extension = os.path.splitext(
    uploaded_file.name
)[1]

temporary_path = None


try:

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file_extension
    ) as temporary_file:

        temporary_file.write(
            uploaded_file.getbuffer()
        )

        temporary_path = (
            temporary_file.name
        )


    # ========================================================
    # RUN PIPELINE
    # ========================================================

    with st.spinner(
        "Analyzing dataset..."
    ):

        raw_analysis_result = analyze_dataset(
            temporary_path
        )

    # Keep the original upload immutable. Cleaning is an explicit,
    # approval-based transformation of the working dataset.
    upload_bytes = uploaded_file.getvalue()
    dataset_key = hashlib.md5(upload_bytes).hexdigest()

    if st.session_state.get("cleaning_dataset_key") != dataset_key:
        st.session_state["cleaning_dataset_key"] = dataset_key
        st.session_state["cleaning_original_df"] = raw_analysis_result["data"].copy()
        st.session_state["cleaning_working_df"] = raw_analysis_result["data"].copy()
        st.session_state["cleaning_audit"] = pd.DataFrame()
        st.session_state["cleaning_applied"] = False
        st.session_state["assistant_history"] = []

    working_df = st.session_state["cleaning_working_df"]

    if st.session_state.get("cleaning_applied", False):
        # Rebuild analytical metadata from the approved working dataset.
        # This keeps downstream analysis aligned with the actual cleaned data.
        with st.spinner("Refreshing analysis after approved cleaning..."):
            analysis_result = analyze_dataframe(working_df)
    else:
        analysis_result = raw_analysis_result

    # ========================================================
    # EXTRACT RESULTS
    # ========================================================

    df = analysis_result[
        "data"
    ]

    classification = analysis_result[
        "classification"
    ]

    quality = analysis_result[
        "quality"
    ]

    raw_quality = raw_analysis_result["quality"]
    cleaning_recommendations = raw_analysis_result["cleaning_recommendations"]

    # Build contextual learning lessons from the active dataset quality report.
    # This keeps the Data Quality teaching layer aligned with the current
    # working dataset after any approved cleaning has been applied.
    quality_guides = build_quality_guides(quality, df)

    relationships = analysis_result[
        "relationships"
    ]

    data_dictionary = analysis_result[
        "data_dictionary"
    ]

    analytical_fields = analysis_result[
        "analytical_fields"
    ]

    analysis_questions = analysis_result[
        "analysis_questions"
    ]

    kpi_recommendations = analysis_result[
        "kpi_recommendations"
    ]

    excel_function_recommendations = analysis_result[
        "excel_function_recommendations"
    ]

    chart_recommendations = analysis_result[
        "chart_recommendations"
    ]


    # ========================================================
    # SUCCESS
    # ========================================================

    st.success(f"Ready to explore: {uploaded_file.name}")


    # ========================================================
    # OVERVIEW METRICS
    # ========================================================

    st.header(
        "Dataset Overview"
    )

    overview_col1, overview_col2, overview_col3, overview_col4 = (
        st.columns(4)
    )


    overview_col1.metric(
        "Rows",
        len(df)
    )


    overview_col2.metric(
        "Columns",
        len(df.columns)
    )


    overview_col3.metric(
        "Missing Values",
        quality["summary"][
            "Total Missing Values"
        ]
    )


    overview_col4.metric(
        "Duplicate Rows",
        quality["summary"][
            "Duplicate Rows"
        ]
    )




    # Persistent assistant: questions are its job; teaching the dataset is the Data Guide's job.
    st.markdown("""
    <style>
    div[data-testid="stPopover"] {
        position: fixed !important;
        right: 1.25rem !important;
        bottom: 1.25rem !important;
        z-index: 9999 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.popover("💬 Ask DataGuide"):
        st.markdown("### Ask about this dataset")
        st.caption("Ask about fields, concepts, relationships, quality findings or useful next steps. Answers are grounded in this dataset.")
        for item in st.session_state.get("assistant_history", [])[-4:]:
            with st.chat_message(item["role"]):
                st.write(item["content"])
        assistant_question = st.text_area(
            "Question",
            placeholder="Why is Profit useful here? What does this column mean?",
            height=90,
            key="assistant_question",
        )
        if st.button("Ask", type="primary", key="assistant_ask"):
            if not assistant_question.strip():
                st.warning("Write a question first.")
            else:
                with st.spinner("Thinking about the dataset..."):
                    try:
                        answer = ask_question(analysis_result.get("dataset_context", {}), assistant_question)
                        response_text = answer.get("answer") or "I could not produce an answer."
                    except Exception as error:
                        response_text = (
                            "The AI service is temporarily unavailable. Data Guide and Data Analysis are still available, "
                            "and no dataset work has been lost. " + str(error)
                        )
                st.session_state.setdefault("assistant_history", []).extend([
                    {"role": "user", "content": assistant_question},
                    {"role": "assistant", "content": response_text},
                ])
                st.rerun()

    # ========================================================
    # MAIN TABS
    # ========================================================

    # The tabs form one narrative: map → meaning → trust → analysis.
    overview_tab, guide_tab, quality_tab, analysis_tab = st.tabs(
        ["Overview", "Data Guide", "Data Quality", "Data Analysis"]
    )


    # ========================================================
    # TAB 1 — OVERVIEW
    # ========================================================

    with overview_tab:

        semantic_data = analysis_result.get("semantic_analysis", {}).get("interpretation", {}).get("data")
        semantic_data = _semantic_data(analysis_result)
        if semantic_data:
            st.markdown("### What DataGuide sees")
            st.write(semantic_data.get("dataset_summary", ""))
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"Likely domain: {semantic_data.get('likely_domain', 'Uncertain')}")
            with c2:
                st.caption(f"Interpretation confidence: {semantic_data.get('confidence', 'Unknown')}")
        else:
            st.info("The AI interpretation is unavailable, but the deterministic dataset map is ready. Data Guide can still explain the structure and analytical roles.")

        st.subheader(
            "Data Preview"
        )

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

        st.subheader("Column Structure")
        type_summary = pd.DataFrame({"Column": df.columns, "Storage Type": [str(dtype) for dtype in df.dtypes]})
        st.dataframe(type_summary, use_container_width=True, hide_index=True)

        st.subheader("Analytical roles")

        st.caption(
            "What each field appears to be useful for in analysis."
        )

        st.dataframe(
            classification,
            use_container_width=True
        )


    # ========================================================
        # TAB 2 — DATA GUIDE
    # ========================================================

    with guide_tab:
        st.header("Data Guide")
        st.write("This is the heart of the learning experience. The goal is not to show you more metadata. It is to help you answer a simpler question: **What is this data actually about, and what can I sensibly learn from it?**")

        semantic_data = _semantic_data(analysis_result)
        semantic_meta = analysis_result.get("semantic_analysis", {}).get("interpretation", {})

        st.markdown("## What this dataset is trying to tell you")
        if semantic_data.get("dataset_summary"):
            st.write(semantic_data["dataset_summary"])
            st.caption(f"Likely domain: **{semantic_data.get('likely_domain', 'Uncertain')}** · Interpretation confidence: {semantic_data.get('confidence', 'Unknown')}")
        else:
            st.write("The AI interpretation is unavailable right now, so DataGuide is using the dataset's structure, field types and observed values as the guide. That is less semantic, but it is still grounded in the actual file.")
            if semantic_meta.get("message"):
                st.caption(semantic_meta["message"])

        st.markdown("## The main pieces of the story")
        entities = semantic_data.get("entities", [])
        if entities:
            st.write("**Important entities:** " + ", ".join(str(x) for x in entities))
        else:
            ids = analytical_fields.get("ids", [])
            dims = analytical_fields.get("dimensions", [])
            st.write("The dataset appears to revolve around " + (", ".join(map(str, ids[:4])) if ids else "the available record fields") + ". You can compare those records through " + (", ".join(map(str, dims[:5])) if dims else "the available categorical fields") + ".")

        st.markdown("## What you can learn from it")
        opportunities = semantic_data.get("analytical_opportunities", [])
        if opportunities:
            for item in opportunities[:6]:
                st.markdown(f"**{item.get('question', 'Useful analytical question')}** · {item.get('priority', 'Medium')} priority")
                if item.get("reason"):
                    st.caption(item["reason"])
        elif not analysis_questions.empty:
            for _, row in analysis_questions.head(6).iterrows():
                st.markdown(f"**{row['Question']}**")
                st.caption(row.get("Rationale", "This question was generated from the available analytical fields."))
        else:
            st.info("No strong analytical questions could be inferred from the current field structure.")

        st.markdown("## What each column means")
        st.caption("When the LLM has enough evidence, you get a semantic explanation. When it does not, DataGuide falls back to the deterministic role instead of pretending to know.")
        for column in df.columns:
            meaning, confidence = _column_interpretation(column, semantic_data, data_dictionary)
            row = data_dictionary.loc[data_dictionary["Column"] == column].iloc[0]
            with st.expander(f"{column} · {row['Classification']}"):
                st.write(meaning)
                st.caption(f"Confidence: {confidence} · Stored as {row['Data Type']} · {int(row['Unique Values']):,} unique non-missing values")
                st.info(f"In analysis, this field can typically be used as: {row['Description']}")

        st.markdown("## How the fields work together")
        if relationships is not None and not relationships.empty:
            st.write("DataGuide found these useful date relationships:")
            st.dataframe(relationships, use_container_width=True)
        else:
            date_fields = analytical_fields.get("dates", [])
            measure_fields = analytical_fields.get("measures", [])
            dimensions = analytical_fields.get("dimensions", [])
            st.write(
                "Read the dataset in three layers: **when** things happened"
                + (f" ({', '.join(map(str, date_fields[:3]))})" if date_fields else "")
                + ", **what** can be measured"
                + (f" ({', '.join(map(str, measure_fields[:4]))})" if measure_fields else "")
                + ", and **how records can be grouped**"
                + (f" ({', '.join(map(str, dimensions[:4]))})" if dimensions else "")
                + "."
            )

        ambiguities = semantic_data.get("ambiguities", [])
        if ambiguities:
            st.markdown("## What DataGuide is not fully sure about")
            for item in ambiguities[:8]:
                st.warning(f"**{item.get('column', 'Field')}** — {item.get('issue', 'Interpretation is uncertain')}. {item.get('suggestion', '')}")

        st.markdown("## A sensible place to start")
        st.write("You do not need to analyze everything. Start with the highest-priority question that matches the purpose of your work, then move to the comparisons or trends that explain it. Data Analysis will turn those recommendations into calculations and visuals.")
        st.info("Next: open **Data Quality**. Before trusting a story, check whether anything could distort it.")

# TAB 3 — DATA QUALITY
    # ========================================================

    with quality_tab:

        st.header("Data Quality")
        st.write("Now that you know what the dataset appears to mean, the next question is whether anything inside it could make that story misleading. DataGuide only teaches issues it actually finds in this file.")

        st.subheader("Data Quality Summary")

        quality_summary = quality[
            "summary"
        ]


        q1, q2, q3, q4 = st.columns(4)


        q1.metric(
            "Missing Values",
            quality_summary[
                "Total Missing Values"
            ]
        )


        q2.metric(
            "Duplicate Rows",
            quality_summary[
                "Duplicate Rows"
            ]
        )


        q3.metric(
            "Rows",
            quality_summary[
                "Rows"
            ]
        )


        q4.metric(
            "Columns",
            quality_summary[
                "Columns"
            ]
        )


        # ----------------------------------------------------
        # OVERALL STATUS
        # ----------------------------------------------------

        if st.session_state.get("cleaning_applied", False):
            st.success("A cleaning pass has been applied. The working dataset used by Analysis is the cleaned version.")
        elif (
            quality_summary["Total Missing Values"] == 0
            and quality_summary["Duplicate Rows"] == 0
            and not _has_rows(quality.get("whitespace"))
            and not _has_rows(quality.get("range_validation"))
            and not _has_rows(quality.get("type_anomalies"))
            and not _has_rows(quality.get("outliers"))
        ):
            st.success("No issues were detected by the current quality checks.")
        else:
            st.warning("This dataset is not fully clean according to the current checks. Review the lessons below before interpreting the analysis.")


        # ----------------------------------------------------
        # APPROVAL-BASED CLEANING
        # ----------------------------------------------------

        st.divider()
        st.subheader("Learn & Clean")
        st.caption(
            "DataGuide only teaches quality issues that were actually detected in this dataset. "
            "The lesson explains what the issue means, why it matters, how it is detected, and what method can fix it. "
            "Cleaning still requires your approval."
        )

        if quality_guides:
            st.markdown("#### What this dataset is teaching you")
            for guide_index, guide in enumerate(quality_guides):
                with st.expander(
                    f"{guide['issue']} — {guide['field']}",
                    expanded=guide_index == 0,
                ):
                    st.markdown(f"**What it means**  \n{guide['what']}")
                    st.markdown(f"**Why it matters**  \n{guide['why']}")
                    st.markdown(f"**Example**  \n{guide['example']}")
                    st.info(f"**Detection / method:** {guide['method']}")
                    st.markdown(f"**How to handle it**  \n{guide['fix']}")

        st.markdown("#### Recommended Cleaning")
        st.caption(
            "The application does not silently delete or change data. "
            "Each recommended action is shown first, and only actions you approve are applied."
        )

        if st.session_state.get("cleaning_applied", False):
            original_df = st.session_state["cleaning_original_df"]
            st.success(
                f"Approved cleaning is active: {len(original_df):,} original rows → {len(df):,} working rows."
            )
            audit = st.session_state.get("cleaning_audit", pd.DataFrame())
            if not audit.empty:
                st.dataframe(audit, use_container_width=True, hide_index=True)

            if st.button("Reset to Original Dataset", key="reset_cleaning"):
                st.session_state["cleaning_working_df"] = original_df.copy()
                st.session_state["cleaning_audit"] = pd.DataFrame()
                st.session_state["cleaning_applied"] = False
                st.rerun()
        elif cleaning_recommendations.empty:
            st.success("No high-confidence executable cleaning actions were detected.")
            st.info(
                "Other quality findings, such as missing values, outliers, and unusual ranges, "
                "are deliberately left for review because automatically changing them could alter the meaning of the data."
            )
        else:
            st.info(
                "Recommended actions are pre-selected only when they are high-confidence and low-risk. "
                "Missing-value imputation, outlier removal, range correction, and similar judgment-heavy changes are not automated."
            )

            st.markdown("#### Review each proposed change")
            approved_action_ids = []
            for action_index, action in cleaning_recommendations.iterrows():
                action_id = str(action["Action ID"])
                selected = st.checkbox(
                    f"{action['Recommended Action']} — {action['Field']} ({int(action['Affected Rows']):,} affected)",
                    value=str(action["Default"]) == "Approve",
                    key=f"clean_action_{action_index}",
                    help=f"{action['Why']} Confidence: {action['Confidence']}."
                )
                st.caption(
                    f"**Issue:** {action['Issue']} · **Confidence:** {action['Confidence']} · "
                    f"**Why:** {action['Why']}"
                )
                if action_id.startswith("trim_whitespace::"):
                    st.code("Python: str.strip()    |    Excel equivalent: TRIM(text)", language="text")
                elif action_id.startswith("blank_text_to_missing::"):
                    st.code("Rule: blank/whitespace-only text → missing value (pd.NA)    |    Excel concept: IF(TRIM(A2)="","",A2)", language="text")
                elif action_id == "remove_exact_duplicates":
                    st.code("Rule: duplicate complete rows → keep first occurrence    |    Excel: Remove Duplicates", language="text")
                elif action_id == "remove_blank_rows":
                    st.code("Rule: all fields missing → remove row    |    Excel concept: filter rows where COUNTA(row)=0", language="text")
                if selected:
                    approved_action_ids.append(action_id)

            button_col1, button_col2 = st.columns(2)
            with button_col1:
                if st.button("Apply Selected Cleaning Actions", type="primary", key="apply_cleaning"):
                    original_df = st.session_state["cleaning_original_df"]
                    cleaned_df, audit = apply_cleaning_actions(
                        original_df,
                        cleaning_recommendations,
                        approved_action_ids,
                    )
                    st.session_state["cleaning_working_df"] = cleaned_df
                    st.session_state["cleaning_audit"] = audit
                    st.session_state["cleaning_applied"] = True
                    st.rerun()

            with button_col2:
                if st.button("Let the Assistant Decide", key="auto_cleaning"):
                    auto_ids = automated_cleaning_action_ids(cleaning_recommendations)
                    original_df = st.session_state["cleaning_original_df"]
                    cleaned_df, audit = apply_cleaning_actions(
                        original_df,
                        cleaning_recommendations,
                        auto_ids,
                    )
                    st.session_state["cleaning_working_df"] = cleaned_df
                    st.session_state["cleaning_audit"] = audit
                    st.session_state["cleaning_applied"] = True
                    st.rerun()

            st.caption(
                "Let the Assistant Decide uses a conservative deterministic safety policy in this phase. "
                "It only applies high-confidence, low-risk transformations; it does not guess how to fill missing values or delete unusual records."
            )

        # ----------------------------------------------------
        # MISSING VALUES
        # ----------------------------------------------------

        with st.expander(
            "Missing Values",
            expanded=True
        ):

            missing_df = quality[
                "missing"
            ]

            missing_issues = missing_df[
                missing_df[
                    "Missing Values"
                ] > 0
            ]


            if missing_issues.empty:

                st.success(
                    "No missing values were detected."
                )

            else:

                st.warning(
                    f"{len(missing_issues)} column(s) "
                    "contain missing values."
                )

                st.dataframe(
                    missing_issues,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # DUPLICATES
        # ----------------------------------------------------

        with st.expander(
            "Duplicate Records",
            expanded=True
        ):

            duplicate_count = (
                quality_summary[
                    "Duplicate Rows"
                ]
            )


            if duplicate_count == 0:

                st.success(
                    "No exact duplicate rows were detected."
                )

            else:

                st.warning(
                    f"{duplicate_count:,} duplicate "
                    "row(s) detected."
                )


        # ----------------------------------------------------
        # WHITESPACE
        # ----------------------------------------------------

        with st.expander(
            "Text Formatting Issues"
        ):

            whitespace_df = quality[
                "whitespace"
            ]


            if whitespace_df.empty:

                st.success(
                    "No leading or trailing whitespace "
                    "issues were detected."
                )

            else:

                st.warning(
                    f"{len(whitespace_df)} column(s) "
                    "contain whitespace issues."
                )

                st.dataframe(
                    whitespace_df,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # CONSTANT COLUMNS
        # ----------------------------------------------------

        with st.expander(
            "Constant Columns"
        ):

            constant_df = quality[
                "constant_columns"
            ]


            if constant_df.empty:

                st.success(
                    "No constant columns were detected."
                )

            else:

                st.info(
                    "Constant columns contain only one "
                    "unique value. They are not necessarily "
                    "errors, but may have limited analytical value."
                )

                st.dataframe(
                    constant_df,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # NUMERIC PROFILE
        # ----------------------------------------------------

        with st.expander(
            "Numeric Field Profile"
        ):

            numeric_df = quality[
                "numeric"
            ]


            if numeric_df.empty:

                st.info(
                    "No numeric fields were detected."
                )

            else:

                st.dataframe(
                    numeric_df,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # RANGE VALIDATION
        # ----------------------------------------------------

        with st.expander(
            "Range Validation"
        ):

            range_df = quality[
                "range_validation"
            ]


            if range_df.empty:

                st.info(
                    "No predefined numeric range checks "
                    "were inferred from the dataset."
                )

            else:

                invalid_range = range_df[
                    range_df[
                        "Invalid Values"
                    ] > 0
                ]


                if invalid_range.empty:

                    st.success(
                        "No values were detected outside "
                        "the inferred ranges."
                    )

                else:

                    st.warning(
                        "Some values fall outside "
                        "the inferred ranges."
                    )


                st.dataframe(
                    range_df,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # DATE RELATIONSHIPS
        # ----------------------------------------------------

        with st.expander(
            "Date Relationship Checks",
            expanded=True
        ):

            if relationships.empty:

                st.info(
                    "No strong date relationships could "
                    "be automatically identified."
                )

            else:

                st.success(
                    f"{len(relationships)} potential "
                    "date relationship(s) identified."
                )

                st.dataframe(
                    relationships,
                    use_container_width=True
                )


        # ----------------------------------------------------
        # POTENTIAL OUTLIERS
        # ----------------------------------------------------

        with st.expander(
            "Potential Outliers"
        ):

            outlier_df = quality[
                "outliers"
            ]


            if outlier_df.empty:

                st.info(
                    "No numeric fields were available "
                    "for outlier analysis."
                )

            else:

                st.info(
                    "Outliers are potential anomalies, "
                    "not automatic errors. They are not "
                    "removed automatically."
                )

                st.dataframe(
                    outlier_df,
                    use_container_width=True
                )


    # ========================================================
    # TAB 4 — DATA ANALYSIS
    # ========================================================

    with analysis_tab:

        st.subheader("Guided Analysis")
        quality_summary = quality.get("summary", {})
        quality_issue = (
            int(quality_summary.get("Total Missing Values", 0) or 0) > 0
            or int(quality_summary.get("Duplicate Rows", 0) or 0) > 0
            or _has_rows(quality.get("whitespace"))
            or _has_rows(quality.get("range_validation"))
            or _has_rows(quality.get("type_anomalies"))
            or _has_rows(quality.get("outliers"))
        )
        if quality_issue and not st.session_state.get("cleaning_applied", False):
            st.warning("This dataset still has detected quality issues. Analysis is based on the current data and may be affected. Review Data Quality and apply the recommended safe cleaning actions when appropriate.")
        else:
            st.success("Analysis is running on the current working dataset.")
        st.caption("Start with the recommended questions. Use filters and visual choices only when you want to explore further.")

        # ----------------------------------------------------
        # EXPLORATION FILTERS / SLICERS
        # ----------------------------------------------------

        filter_recommendations = recommend_filters(df, analytical_fields)
        st.markdown("### Optional filters")
        st.caption("Use these only if you want to focus the analysis on a particular segment, region, category, or date.")

        exploration_df = df.copy()
        active_exploration_filters = {}

        if filter_recommendations.empty:
            st.info("No compact filter fields were detected for interactive exploration.")
        else:
            filter_columns = st.columns(2)
            for index, row in filter_recommendations.iterrows():
                field = row["Field"]
                if field not in exploration_df.columns:
                    continue

                series = exploration_df[field].dropna()
                unique_values = list(pd.unique(series))
                unique_values = sorted(unique_values, key=lambda value: str(value))

                # Keep exploration controls practical for high-cardinality fields.
                if len(unique_values) > 100:
                    continue

                options = ["All"] + unique_values
                with filter_columns[index % 2]:
                    selected_value = st.selectbox(
                        f"{field} — {row['Filter Type']}",
                        options=options,
                        index=0,
                        key=f"explore_filter_{index}",
                        help=row["Why Use It"],
                    )
                    st.caption(f"{row['Unique Values']} unique values · {row['Why Use It']}")

                if selected_value != "All":
                    active_exploration_filters[field] = selected_value
                    exploration_df = exploration_df[
                        exploration_df[field].astype(str) == str(selected_value)
                    ]

        if active_exploration_filters:
            st.info(
                "Active exploration filters: "
                + ", ".join(f"{field} = {value}" for field, value in active_exploration_filters.items())
                + f" · {len(exploration_df):,} rows remain"
            )
        else:
            st.caption(f"No exploration filters applied · {len(exploration_df):,} rows available")

        st.divider()

        # ----------------------------------------------------
        # EXPLORATION KPIs
        # ----------------------------------------------------

        st.subheader("1. Start with a KPI")
        st.caption("Choose one or two useful measures. DataGuide calculates them on the current filtered data.")

        exploration_kpis = []
        kpi_source = kpi_recommendations.head(6)
        if kpi_source.empty:
            st.info("No strong KPI recommendations could be inferred from this dataset.")
        else:
            kpi_columns = st.columns(3)
            for pos, (index, row) in enumerate(kpi_source.iterrows()):
                with kpi_columns[pos % 3]:
                    selected = st.checkbox(row["KPI"], value=False, key=f"explore_kpi_{index}", help=f"{row['Calculation']} | {row['Rationale']}")
                    st.caption(f"{row['Category']} · {row['Calculation']}")
                    if selected:
                        exploration_kpis.append(index)
            if len(kpi_recommendations) > 6:
                with st.expander("See more KPI recommendations"):
                    for index, row in kpi_recommendations.iloc[6:].iterrows():
                        selected = st.checkbox(row["KPI"], value=False, key=f"explore_kpi_more_{index}", help=f"{row['Calculation']} | {row['Rationale']}")
                        if selected:
                            exploration_kpis.append(index)

        if exploration_kpis:
            st.markdown("#### Selected KPI Results")
            calculated_exploration_kpis = []
            for index in exploration_kpis:
                recommendation = kpi_recommendations.loc[index]
                try:
                    calculated_exploration_kpis.append(calculate_kpi(exploration_df, recommendation))
                except Exception as error:
                    st.error(f"Could not calculate KPI '{recommendation['KPI']}': {error}")

            if calculated_exploration_kpis:
                cols = st.columns(min(4, len(calculated_exploration_kpis)))
                for pos, kpi in enumerate(calculated_exploration_kpis):
                    with cols[pos % len(cols)]:
                        value = kpi.get("Value")
                        if value is None:
                            display_value = "N/A"
                        elif kpi.get("Category") == "Ratio":
                            display_value = f"{value:.1%}"
                        elif isinstance(value, float):
                            display_value = f"{value:,.2f}"
                        else:
                            display_value = f"{value:,}"
                        st.metric(kpi["KPI"], display_value)

        st.divider()

        # ----------------------------------------------------
        # EXPLORATION ANALYSES
        # ----------------------------------------------------

        st.subheader("2. Questions DataGuide recommends")
        st.caption("Start with the first few questions. They are ordered by analytical priority for this dataset.")

        exploration_analysis_indices = []
        if analysis_questions.empty:
            st.info("No analytical recommendations could be generated from this dataset.")
        else:
            primary_questions = analysis_questions.head(6)
            for index, row in primary_questions.iterrows():
                priority = row.get("Priority", "Medium")
                chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                chart_name = chart_match.iloc[0]["Recommended Chart"] if not chart_match.empty else "Table"
                label = f"{row['Question']}  ·  {priority} priority  ·  {chart_name}"
                if st.checkbox(label, value=False, key=f"explore_analysis_{index}", help=row.get("Rationale", "")):
                    exploration_analysis_indices.append(index)
            if len(analysis_questions) > 6:
                with st.expander("See more recommended questions"):
                    for index, row in analysis_questions.iloc[6:].iterrows():
                        priority = row.get("Priority", "Medium")
                        if st.checkbox(f"{row['Question']}  ·  {priority} priority", value=False, key=f"explore_analysis_more_{index}", help=row.get("Rationale", "")):
                            exploration_analysis_indices.append(index)

        if exploration_analysis_indices:
            st.markdown("#### Selected Analysis Results")
            for index in exploration_analysis_indices:
                recommendation = analysis_questions.loc[index]
                st.markdown(f"**{recommendation['Question']}**")
                st.caption(f"{recommendation['Analysis Type']}")
                try:
                    analysis_result_for_display = run_analysis(exploration_df, recommendation)
                    visual_choices = _available_visual_choices(
                        recommendation["Analysis Type"],
                        analysis_result_for_display,
                    )
                    if visual_choices != ["Table / KPI"]:
                        selected_visual = st.selectbox(
                            "Choose a visual to explore",
                            visual_choices,
                            index=0,
                            key=f"explore_visual_{index}",
                            help=(
                                "DataGuide recommends the first option. Other options are shown when "
                                "they are analytically reasonable, so you can compare visual choices and learn why they differ."
                            ),
                        )
                        st.caption(
                            f"Recommended visual: {visual_choices[0]}. Your choice changes only the display, not the underlying calculation."
                        )
                        chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                        if not chart_match.empty:
                            st.info(f"Why this visual: {chart_match.iloc[0]['Why This Chart']}")
                    else:
                        selected_visual = "Table / KPI"
                    display_analysis_result(
                        analysis_result_for_display,
                        recommendation["Analysis Type"],
                        selected_visual,
                    )
                except Exception as error:
                    st.error(f"Could not generate this analysis: {error}")

        st.divider()
        st.info("DataGuide calculates the answer first, then recommends a visual. Changing the visual changes the presentation, not the underlying calculation.")

    # ========================================================
    # CLEANUP
# ============================================================

finally:

    if temporary_path is not None:

        try:

            os.remove(
                temporary_path
            )

        except OSError:

            pass
