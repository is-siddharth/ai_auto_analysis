import os
import tempfile

import pandas as pd
import streamlit as st

from src.pipeline import analyze_dataset
from src.ingestion.loader import load_raw_dataset
from src.analysis.engine import run_analysis
from src.analysis.kpis import calculate_kpi
from src.analysis.filters import recommend_filters
from src.dashboard.generator import recommend_dashboard_layouts
from src.excel.workbook import generate_excel_workbook


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Data Analytics Assistant",
    page_icon="📊",
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


def display_analysis_result(
    result
):
    """
    Display a calculated analysis result.

    The analysis engine returns:
        table
        chart_type
        x
        y
        optional chart_data
    """

    table = result.get(
        "table"
    )


    if table is None:

        st.info(
            "No result was produced."
        )

        return


    if table.empty:

        st.info(
            "The selected analysis did not produce any results."
        )

        return


    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    st.dataframe(
        table,
        use_container_width=True
    )


    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    chart_type = result.get(
        "chart_type"
    )

    if chart_type is None:
        return


    chart_data = result.get(
        "chart_data",
        table
    )

    x_column = result.get(
        "x"
    )

    y_column = result.get(
        "y"
    )


    if (
        x_column not in chart_data.columns
        or
        y_column not in chart_data.columns
    ):

        return


    chart_frame = (
        chart_data[
            [
                x_column,
                y_column
            ]
        ]
        .dropna()
        .set_index(
            x_column
        )
    )


    if chart_frame.empty:
        return


    if chart_type == "bar":

        st.bar_chart(
            chart_frame,
            use_container_width=True
        )


    elif chart_type == "line":

        st.line_chart(
            chart_frame,
            use_container_width=True
        )


# ============================================================
# APPLICATION HEADER
# ============================================================

st.title(
    "AI Data Analytics Assistant"
)

st.write(
    """
    An intelligent analytics workflow that transforms raw datasets
    into structured data understanding, data-quality checks,
    analytical recommendations, and eventually automated Excel outputs.
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

        **6. Generate Results**

        **7. Build Excel Output**
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
            ### Build

            Eventually generate:

            - Excel analysis
            - PivotTables
            - Charts
            - KPI sheets
            - Dashboard structures
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

        analysis_result = analyze_dataset(
            temporary_path
        )


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
        # EXPLORATION KPIs
        # ----------------------------------------------------

        st.subheader("1. KPIs to Explore")
        st.caption(
            "These selections are for learning and exploration only. They are independent from the KPIs you later choose for the final Excel workbook."
        )

        exploration_kpis = []
        if kpi_recommendations.empty:
            st.info("No strong generic KPI recommendations could be inferred from this dataset.")
        else:
            kpi_columns = st.columns(3)
            for index, row in kpi_recommendations.iterrows():
                with kpi_columns[index % 3]:
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

        st.subheader("2. Analysis Questions to Explore")
        st.caption(
            "Select questions you want to investigate. Results and charts appear here immediately and respond to the exploration filters above."
        )

        exploration_analysis_indices = []
        if analysis_questions.empty:
            st.info("No analytical recommendations could be generated from this dataset.")
        else:
            for index, row in analysis_questions.iterrows():
                priority = row.get("Priority", "Medium")
                chart_match = chart_recommendations[chart_recommendations["Analysis Index"] == index]
                chart_name = chart_match.iloc[0]["Recommended Chart"] if not chart_match.empty else "Table"
                label = f"{row['Question']} — {row['Analysis Type']} — {chart_name} · {priority} priority"
                if st.checkbox(label, value=False, key=f"explore_analysis_{index}"):
                    exploration_analysis_indices.append(index)

        if exploration_analysis_indices:
            st.markdown("#### Selected Analysis Results")
            for index in exploration_analysis_indices:
                recommendation = analysis_questions.loc[index]
                st.markdown(f"**{recommendation['Question']}**")
                st.caption(f"{recommendation['Analysis Type']}")
                try:
                    display_analysis_result(run_analysis(exploration_df, recommendation))
                except Exception as error:
                    st.error(f"Could not generate this analysis: {error}")

        st.divider()

        st.subheader("3. Excel Functions You Can Practice")
        st.caption(
            "These suggestions are tied to tasks supported by this dataset, rather than being a generic list of popular Excel functions."
        )
        if excel_function_recommendations.empty:
            st.info("No specific Excel-function opportunities were inferred.")
        else:
            st.dataframe(excel_function_recommendations, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("4. Recommended Visuals")
        st.caption("Each visual recommendation is attached to an analytical question so the chart has a reason to exist.")
        if chart_recommendations.empty:
            st.info("No chart recommendations were generated.")
        else:
            st.dataframe(chart_recommendations, use_container_width=True, hide_index=True)

        st.info(
            "Use this tab as your analysis workspace. When you are ready to create the deliverable, go to **Generate**. "
            "The Generate tab has its own independent KPI, analysis, filter, and dashboard-layout selections."
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
