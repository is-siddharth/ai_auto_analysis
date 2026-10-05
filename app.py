import hashlib
import os
import tempfile

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from src.pipeline import analyze_dataset, analyze_dataframe
from src.ingestion.loader import load_raw_dataset
from src.analysis.engine import run_analysis
from src.analysis.kpis import calculate_kpi
from src.analysis.filters import recommend_filters
from src.analysis.charts import CHART_OPTIONS
from src.profiling.cleaning import apply_cleaning_actions, automated_cleaning_action_ids
from src.profiling.quality_guide import build_quality_guides
from src.dashboard.generator import recommend_dashboard_layouts
from src.excel.workbook import generate_excel_workbook


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
# APPLICATION HEADER
# ============================================================

st.title(
    "DataGuide"
)

st.write(
    """
    Your dataset guide: understand the data, learn what quality issues mean,
    explore the right analysis, visualize the findings, and learn why each choice makes sense.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "Workflow"
    )

    st.markdown(
        """
        **1. Upload Dataset**

        **2. Understand Data**

        **3. Check Data Quality**

        **4. Interpret Columns**

        **5. Discover Analysis**

        **6. Explore & Learn**

        **7. Optional Excel Output**
        """
    )

    st.divider()

    st.caption(
        "AI-powered interpretation and advanced analytics "
        "will be added progressively."
    )


# ============================================================
# FILE UPLOAD
# ============================================================

st.header(
    "Upload Dataset"
)

uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=[
        "csv",
        "xlsx",
        "xls"
    ]
)


# ============================================================
# EMPTY STATE
# ============================================================

if uploaded_file is None:

    st.info(
        "Upload a CSV or Excel dataset to begin the analysis."
    )

    st.subheader(
        "What this application will eventually provide"
    )

    col1, col2, col3 = st.columns(3)


    with col1:

        st.markdown(
            """
            ### Understand

            Automatically identify:

            - Dataset structure
            - Data types
            - IDs
            - Dates
            - Dimensions
            - Measures
            - Geographic fields
            """
        )


    with col2:

        st.markdown(
            """
            ### Analyze

            Discover:

            - Trends
            - Comparisons
            - Rankings
            - Contributions
            - KPIs
            - Business questions
            """
        )


    with col3:

        st.markdown(
            """
            ### Learn & Present

            Explore the dataset in one place:

            - Recommended analysis
            - Interactive visuals
            - KPI explanations
            - Outlier learning
            - Contextual data-quality lessons
            """
        )


    st.stop()


# ============================================================
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
    quality_guides = build_quality_guides(quality)

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

    st.success(
        f"Dataset successfully analyzed: "
        f"{uploaded_file.name}"
    )


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


    # ========================================================
    # MAIN TABS
    # ========================================================

    (
        overview_tab,
        quality_tab,
        interpretation_tab,
        analysis_tab,
    generate_tab
    ) = st.tabs(
        [
            "Overview",
            "Data Quality",
            "Data Interpretation",
            "Analysis",
            "Generate"
        ]
    )


    # ========================================================
    # TAB 1 — OVERVIEW
    # ========================================================

    with overview_tab:

        st.subheader(
            "Data Preview"
        )

        st.dataframe(
            df.head(20),
            use_container_width=True
        )


        st.subheader(
            "Column Structure"
        )

        st.caption(
            "Detected analytical role and storage characteristics "
            "for each column."
        )

        st.dataframe(
            classification,
            use_container_width=True
        )


    # ========================================================
    # TAB 2 — DATA QUALITY
    # ========================================================

    with quality_tab:

        st.subheader(
            "Data Quality Summary"
        )

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

        if (
            quality_summary[
                "Total Missing Values"
            ] == 0
            and
            quality_summary[
                "Duplicate Rows"
            ] == 0
        ):

            st.success(
                "No missing values or duplicate rows "
                "were detected."
            )

        else:

            st.warning(
                "Potential data-quality issues were detected. "
                "Review the checks below."
            )


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
    # TAB 3 — DATA INTERPRETATION
    # ========================================================

    with interpretation_tab:

        st.subheader(
            "Data Dictionary"
        )

        st.caption(
            "A structured interpretation of detected "
            "columns and their analytical roles."
        )

        st.dataframe(
            data_dictionary,
            use_container_width=True
        )


        st.divider()


        st.subheader(
            "Analytical Field Groups"
        )

        st.caption(
            "Columns are grouped according to their "
            "current analytical role."
        )


        # ----------------------------------------------------
        # ROW 1
        # ----------------------------------------------------

        field_col1, field_col2, field_col3 = (
            st.columns(3)
        )


        with field_col1:

            display_field_group(
                "Identifiers",
                analytical_fields[
                    "ids"
                ]
            )


        with field_col2:

            display_field_group(
                "Dates",
                analytical_fields[
                    "dates"
                ]
            )


        with field_col3:

            display_field_group(
                "Measures",
                analytical_fields[
                    "measures"
                ]
            )


        # ----------------------------------------------------
        # ROW 2
        # ----------------------------------------------------

        field_col4, field_col5, field_col6 = (
            st.columns(3)
        )


        with field_col4:

            display_field_group(
                "Dimensions",
                analytical_fields[
                    "dimensions"
                ]
            )


        with field_col5:

            display_field_group(
                "Geographic Fields",
                analytical_fields[
                    "geographic"
                ]
            )


        with field_col6:

            display_field_group(
                "Text Fields",
                analytical_fields[
                    "text"
                ]
            )


        # ----------------------------------------------------
        # ROW 3
        # ----------------------------------------------------

        st.divider()


        display_field_group(
            "Boolean Fields",
            analytical_fields[
                "boolean"
            ]
        )


    # ========================================================
    # TAB 4 — ANALYSIS
    # ========================================================

    with analysis_tab:

        st.subheader("Explore the Dataset")
        st.caption(
            "This tab is your analysis workspace. Select KPIs and questions to study the data, "
            "then use the interactive filters below to change what the charts and results show. "
            "Nothing selected here controls the final Excel workbook."
        )

        # ----------------------------------------------------
        # EXPLORATION FILTERS / SLICERS
        # ----------------------------------------------------

        filter_recommendations = recommend_filters(df, analytical_fields)
        st.markdown("### Explore with Filters / Slicers")
        st.caption(
            "These controls act like dashboard slicers for this analysis workspace. "
            "Changing a selection recalculates the displayed KPI and analysis results."
        )

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
        # GUIDED EXPLORATION
        # ----------------------------------------------------

        st.subheader("Start with the recommended questions")
        st.caption(
            "You do not need to run everything. Start with the highest-priority questions, "
            "then explore the result and choose a visual that helps you understand it."
        )

        # Keep the main workspace intentionally small. Advanced options remain available below.
        recommended_kpis = kpi_recommendations.head(6) if not kpi_recommendations.empty else kpi_recommendations
        recommended_analyses = analysis_questions.copy()
        if not recommended_analyses.empty:
            priority_order = {"High": 0, "Medium": 1, "Low": 2}
            recommended_analyses["_priority_order"] = recommended_analyses["Priority"].map(priority_order).fillna(9)
            recommended_analyses = recommended_analyses.sort_values(["_priority_order"]).head(5).drop(columns=["_priority_order"])

        exploration_kpis = []
        if not recommended_kpis.empty:
            st.markdown("#### Useful KPIs")
            kpi_columns = st.columns(min(3, len(recommended_kpis)))
            for position, (index, row) in enumerate(recommended_kpis.iterrows()):
                with kpi_columns[position % len(kpi_columns)]:
                    selected = st.checkbox(
                        row["KPI"],
                        value=False,
                        key=f"explore_kpi_{index}",
                        help=f"{row['Calculation']} | {row['Rationale']}",
                    )
                    st.caption(f"{row['Category']} · {row['Calculation']}")
                    if selected:
                        exploration_kpis.append(index)

        if exploration_kpis:
            st.markdown("#### KPI results")
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

        exploration_analysis_indices = []
        if not recommended_analyses.empty:
            st.markdown("#### Questions to investigate")
            for index, row in recommended_analyses.iterrows():
                priority = row.get("Priority", "Medium")
                chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                chart_name = chart_match.iloc[0]["Recommended Chart"] if not chart_match.empty else "Table"
                label = f"{row['Question']}"
                help_text = f"{priority} priority · Recommended visual: {chart_name}"
                if st.checkbox(label, value=False, key=f"explore_analysis_{index}", help=help_text):
                    exploration_analysis_indices.append(index)

        if exploration_analysis_indices:
            st.markdown("#### Results")
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
                            "Visual",
                            visual_choices,
                            index=0,
                            key=f"explore_visual_{index}",
                            help=(
                                "DataGuide recommends the first option. Other choices are shown only "
                                "when they are analytically reasonable."
                            ),
                        )
                        st.caption(
                            f"Recommended: {visual_choices[0]}. Changing the visual changes the presentation, not the calculation."
                        )
                    else:
                        selected_visual = "Table / KPI"
                    display_analysis_result(
                        analysis_result_for_display,
                        recommendation["Analysis Type"],
                        selected_visual,
                    )
                except Exception as error:
                    st.error(f"Could not generate this analysis: {error}")

        with st.expander("Optional: explore more questions and KPIs"):
            if not kpi_recommendations.empty and len(kpi_recommendations) > len(recommended_kpis):
                st.markdown("**More KPIs**")
                more_kpis = kpi_recommendations.iloc[len(recommended_kpis):]
                for index, row in more_kpis.iterrows():
                    st.checkbox(
                        row["KPI"],
                        value=False,
                        key=f"explore_kpi_extra_{index}",
                        help=f"{row['Calculation']} | {row['Rationale']}",
                    )
            if not analysis_questions.empty and len(analysis_questions) > len(recommended_analyses):
                st.markdown("**More analysis questions**")
                recommended_ids = set(recommended_analyses.index)
                for index, row in analysis_questions.iterrows():
                    if index in recommended_ids:
                        continue
                    priority = row.get("Priority", "Medium")
                    chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                    chart_name = chart_match.iloc[0]["Recommended Chart"] if not chart_match.empty else "Table"
                    st.checkbox(
                        row["Question"],
                        value=False,
                        key=f"explore_analysis_extra_{index}",
                        help=f"{priority} priority · Recommended visual: {chart_name}",
                    )

        with st.expander("Learn more about the methods"):
            st.caption(
                "These sections explain the tools DataGuide used or recommends for this dataset. "
                "They are optional learning material, not extra work you must complete."
            )
            st.markdown("**Excel functions you can practice**")
            if excel_function_recommendations.empty:
                st.info("No specific Excel-function opportunities were inferred.")
            else:
                st.dataframe(excel_function_recommendations, use_container_width=True, hide_index=True)

            st.markdown("**Why these visuals were recommended**")
            if chart_recommendations.empty:
                st.info("No chart recommendations were generated.")
            else:
                st.dataframe(chart_recommendations, use_container_width=True, hide_index=True)

        st.info(
            "DataGuide's main job here is to guide you: start with the recommended questions, "
            "inspect the result, then use the visual choice to learn how the same finding can be communicated."
        )

    # ========================================================
    # TAB 5 — GENERATE
    # ========================================================

    with generate_tab:

        st.subheader("Build Your Final Deliverable")
        st.caption(
            "This is a separate final-selection workspace. What you select here determines what goes into the generated Excel workbook; "
            "your exploratory choices in the Analysis tab do not carry over."
        )

        # ----------------------------------------------------
        # FINAL WORKBOOK OUTPUT SELECTIONS
        # ----------------------------------------------------

        st.markdown("### 1. Choose Final Workbook KPIs")
        st.caption("Select only the KPIs you want included as dedicated KPI sheets in the final workbook.")
        generation_kpis = []
        if kpi_recommendations.empty:
            st.info("No KPI recommendations are available.")
        else:
            kpi_columns = st.columns(3)
            for index, row in kpi_recommendations.iterrows():
                with kpi_columns[index % 3]:
                    selected = st.checkbox(
                        row["KPI"],
                        value=False,
                        key=f"generate_kpi_{index}",
                        help=f"{row['Calculation']} | {row['Rationale']}",
                    )
                    st.caption(f"{row['Category']} · {row['Calculation']}")
                    if selected:
                        generation_kpis.append(index)

        st.divider()

        st.markdown("### 2. Choose Final Workbook Analyses")
        st.caption("Select the analytical questions that should become dedicated analysis sheets in the final workbook.")
        generation_analysis_indices = []
        if analysis_questions.empty:
            st.info("No analysis recommendations are available.")
        else:
            for index, row in analysis_questions.iterrows():
                priority = row.get("Priority", "Medium")
                chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                chart_name = chart_match.iloc[0]["Recommended Chart"] if not chart_match.empty else "Table"
                label = f"{row['Question']} — {row['Analysis Type']} — Suggested visual: {chart_name} · {priority} priority"
                if st.checkbox(label, value=False, key=f"generate_analysis_{index}"):
                    generation_analysis_indices.append(index)

        st.divider()

        # Dataset-aware layouts are based on the final selections, not exploration selections.
        dashboard_layouts = recommend_dashboard_layouts(
            analytical_fields,
            selected_kpi_count=len(generation_kpis),
            selected_analysis_count=len(generation_analysis_indices),
        )

        st.markdown("### 3. Choose a Dashboard Layout")
        st.caption("This controls the final dashboard template, not the exploratory analysis workspace.")

        def render_layout_preview(layout):
            key = layout.get("Key", "balanced_grid")
            blocks = {
                "kpi_left_slicer": [
                    ("header", "DASHBOARD"), ("kpis", "KPI 1   |   KPI 2   |   KPI 3   |   KPI 4"),
                    ("slicer", "FILTERS / SLICERS"), ("chart", "CHART 1   |   CHART 2"), ("chart", "CHART 3   |   CHART 4"),
                ],
                "kpi_top_trend": [
                    ("header", "DASHBOARD"), ("kpis", "KPI 1   |   KPI 2   |   KPI 3   |   KPI 4"),
                    ("hero", "HERO TREND / MAIN ANALYSIS"), ("chart", "CHART 2   |   CHART 3"),
                ],
                "hero_chart": [
                    ("header", "DASHBOARD"), ("kpis", "KPI 1   |   KPI 2   |   KPI 3"),
                    ("hero", "HERO CHART / MAIN STORY"), ("chart", "CHART 2   |   CHART 3"),
                ],
                "comparison_board": [
                    ("header", "DASHBOARD"), ("kpis", "KPI 1   |   KPI 2   |   KPI 3"),
                    ("slicer", "FILTERS / SLICERS"), ("chart", "COMPARISON 1   |   COMPARISON 2"), ("chart", "COMPARISON 3   |   COMPARISON 4"),
                ],
                "balanced_grid": [
                    ("header", "DASHBOARD"), ("kpis", "KPI 1   |   KPI 2   |   KPI 3   |   KPI 4"),
                    ("slicer", "FILTERS / SLICERS"), ("chart", "CHART 1   |   CHART 2"), ("chart", "CHART 3   |   CHART 4"),
                ],
            }
            html = '<div style="border:2px solid #334155;border-radius:10px;padding:10px;background:#f8fafc;color:#111827;min-height:260px;">'
            for kind, text_value in blocks.get(key, blocks["balanced_grid"]):
                if kind == "header":
                    html += f'<div style="background:#1e293b;color:#ffffff;padding:9px;border-radius:6px;margin-bottom:7px;text-align:center;font-weight:700;">{text_value}</div>'
                elif kind == "kpis":
                    html += f'<div style="background:#dbeafe;color:#111827;border:1px solid #60a5fa;padding:12px;border-radius:6px;margin-bottom:7px;text-align:center;font-size:12px;font-weight:700;">{text_value}</div>'
                elif kind == "slicer":
                    html += f'<div style="background:#fef3c7;color:#111827;border:2px dashed #b45309;padding:12px;border-radius:6px;margin-bottom:7px;text-align:center;font-size:11px;white-space:pre-line;font-weight:700;">{text_value}</div>'
                elif kind == "hero":
                    html += f'<div style="background:#e0f2fe;color:#111827;border:2px solid #0284c7;padding:28px 8px;border-radius:6px;margin-bottom:7px;text-align:center;font-size:12px;font-weight:700;">{text_value}</div>'
                else:
                    html += f'<div style="background:#ffffff;color:#111827;border:1px solid #64748b;padding:15px 5px;border-radius:6px;margin-bottom:7px;text-align:center;font-size:11px;font-weight:600;">{text_value}</div>'
            return html + '</div>'

        preview_columns = st.columns(2)
        for position, layout in enumerate(dashboard_layouts):
            with preview_columns[position % 2]:
                st.markdown(f"**{position + 1}. {layout['Layout']}**")
                st.markdown(render_layout_preview(layout), unsafe_allow_html=True)
                st.caption(layout["Why It Fits"])

        layout_labels = [layout["Layout"] for layout in dashboard_layouts]
        selected_layout_label = st.radio("Select the layout to generate", layout_labels, index=0, key="selected_dashboard_layout")
        selected_layout = next(layout for layout in dashboard_layouts if layout["Layout"] == selected_layout_label)

        st.divider()
        st.markdown("### 4. Choose Final Dashboard Filters / Slicers")
        st.caption("These are the filter fields the final dashboard blueprint should reserve space for. They are independent from Analysis-tab exploration filters.")

        filter_options = filter_recommendations["Field"].tolist() if not filter_recommendations.empty else []
        confirmed_filters = st.multiselect(
            "Filters / slicers to include in the dashboard template",
            options=filter_options,
            default=[],
            key="generate_filters",
            help="Select fields the eventual dashboard viewer should be able to use to narrow the displayed data.",
        )
        if confirmed_filters:
            st.info("Selected final-dashboard filters: " + ", ".join(confirmed_filters))
        else:
            st.caption("No dashboard filters selected. The workbook will still contain filter-ready source tables.")

        st.divider()
        st.markdown("### 5. Preview Final Workbook Selection")
        if not generation_kpis and not generation_analysis_indices:
            st.warning("Select at least one final KPI or analysis question above.")
        else:
            if generation_kpis:
                st.markdown("#### Final Workbook KPIs")
                calculated_kpis = []
                for index in generation_kpis:
                    recommendation = kpi_recommendations.loc[index]
                    try:
                        calculated_kpis.append(calculate_kpi(df, recommendation))
                    except Exception as error:
                        st.error(f"Could not calculate KPI '{recommendation['KPI']}': {error}")
                if calculated_kpis:
                    cols = st.columns(min(4, len(calculated_kpis)))
                    for pos, kpi in enumerate(calculated_kpis):
                        with cols[pos % len(cols)]:
                            value = kpi["Value"]
                            if value is None:
                                display_value = "N/A"
                            elif kpi["Category"] == "Ratio":
                                display_value = f"{value:.1%}"
                            elif isinstance(value, float):
                                display_value = f"{value:,.2f}"
                            else:
                                display_value = f"{value:,}"
                            st.metric(kpi["KPI"], display_value)

            if generation_analysis_indices:
                st.markdown("#### Final Workbook Analyses")
                for index in generation_analysis_indices:
                    recommendation = analysis_questions.loc[index]
                    st.markdown(f"**{recommendation['Question']}**")
                    st.caption(f"{recommendation['Analysis Type']}")
                    try:
                        display_analysis_result(run_analysis(df, recommendation))
                    except Exception as error:
                        st.error(f"Could not generate this analysis: {error}")

        st.divider()
        st.markdown("### 6. Generate Final Excel Workbook")
        st.caption(
            "The final workbook contains only the KPIs and analyses selected in this Generate tab, plus the source data, cleaned data, data dictionary, learning guide, filter guide, dashboard instructions, and final dashboard template."
        )

        if st.button("Generate Final Excel Workbook", type="primary", key="generate_workbook"):
            if not generation_kpis and not generation_analysis_indices:
                st.warning("Select at least one final KPI or analysis before generating the workbook.")
            else:
                generated_kpis, generated_analyses, generation_errors = [], [], []
                for index in generation_kpis:
                    recommendation = kpi_recommendations.loc[index]
                    try:
                        generated_kpis.append(calculate_kpi(df, recommendation))
                    except Exception as error:
                        generation_errors.append(f"KPI '{recommendation['KPI']}': {error}")

                for index in generation_analysis_indices:
                    recommendation = analysis_questions.loc[index]
                    try:
                        result = run_analysis(df, recommendation)
                        chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                        chart_label = str(chart_match.iloc[0]["Recommended Chart"]) if not chart_match.empty else "Table"
                        generated_analyses.append({
                            "recommendation": recommendation.to_dict(),
                            "result": result,
                            "chart_label": chart_label,
                        })
                    except Exception as error:
                        generation_errors.append(f"Analysis '{recommendation['Question']}': {error}")

                if generation_errors:
                    st.error("Some selected outputs could not be generated:\n\n" + "\n".join(generation_errors))
                else:
                    try:
                        raw_df = load_raw_dataset(temporary_path)
                        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
                        with st.spinner("Building and validating the final Excel workbook..."):
                            generate_excel_workbook(
                                output_path=output_path,
                                raw_df=raw_df,
                                cleaned_df=df.copy(),
                                data_dictionary=data_dictionary,
                                kpis=generated_kpis,
                                analyses=generated_analyses,
                                excel_function_recommendations=excel_function_recommendations,
                                dashboard_layout=selected_layout,
                                dataset_name=uploaded_file.name,
                                selected_filters=confirmed_filters,
                                filter_recommendations=filter_recommendations,
                                cleaning_audit=st.session_state.get("cleaning_audit", pd.DataFrame()),
                            )
                        with open(output_path, "rb") as workbook_file:
                            workbook_bytes = workbook_file.read()
                        os.remove(output_path)
                        st.success(
                            f"Workbook generated successfully: {len(generated_kpis)} KPI(s), {len(generated_analyses)} analysis sheet(s), {len(confirmed_filters)} filter field(s)."
                        )
                        st.download_button(
                            "Download Final Excel Workbook",
                            data=workbook_bytes,
                            file_name=f"{os.path.splitext(uploaded_file.name)[0]}_analytics_output.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_workbook",
                        )
                    except Exception as error:
                        st.exception(error)

        st.divider()
        st.caption(
            f"Final workbook selection: {len(generation_kpis)} KPI(s) · {len(generation_analysis_indices)} analysis question(s) · {len(confirmed_filters)} dashboard filter(s) · Layout: {selected_layout['Layout']}"
        )


# ============================================================
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
