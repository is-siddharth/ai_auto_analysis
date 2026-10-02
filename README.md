# AI Data Analytics Assistant

An AI-assisted data analytics workflow that turns a raw CSV or Excel dataset into a structured understanding of the data, data-quality checks, analysis recommendations, KPI recommendations, Excel learning opportunities, charts, and a downloadable Excel analysis workbook with a dashboard blueprint.

The project is designed around a practical analyst workflow:

> **Understand the dataset first. Then decide what to calculate, visualize, and communicate.**

## Core principle

> **Python determines what the data says; the LLM helps determine what the data means.**

The system deliberately separates deterministic analytics from semantic AI interpretation.

---

## The problem this solves

When analysts receive a new dataset, the difficult part is often not writing `SUM()` or making a chart. It is knowing what those calculations should mean in context.

A dataset may contain IDs, dates, dimensions, measures, rates, scores, geographic fields, and text, but a new analyst still has to work out:

- Which fields are identifiers?
- Which numeric fields are actual measures?
- Which numbers are percentages, scores, attributes, or codes?
- What does each column mean?
- What data-quality problems should be checked?
- Which questions are worth asking?
- Which KPIs are meaningful?
- Which Excel functions are useful for the actual dataset?
- Which charts fit the questions?
- How should the final dashboard be arranged?

This project is intended to provide that analytical foundation while keeping the human in control of the final selection and presentation.

---

## Current end-to-end workflow

```text
CSV / Excel upload
        ↓
Dataset ingestion
        ↓
Column-role classification
        ↓
Data-quality profiling
        ↓
Relationship / validation checks
        ↓
Data dictionary
        ↓
Analytical field groups
        ↓
Analysis recommendations
        ↓
KPI recommendations
        ↓
Excel-function recommendations
        ↓
Chart recommendations
        ↓
User selects KPIs + analyses
        ↓
Python calculates selected outputs
        ↓
User previews results
        ↓
User selects a visual dashboard layout
        ↓
Final Excel workbook
        ↓
Dashboard blueprint for manual assembly
```

The human remains responsible for selecting outputs, reviewing results, customizing the dashboard, and presenting the final analysis.

---

## Architecture

### Deterministic Python layer

Python is responsible for facts that should be calculated from the data itself:

- row and column counts
- pandas data types
- missing values
- duplicate rows
- whitespace problems
- cardinality
- constant columns
- numeric summaries
- date parsing and validation
- date relationships
- identifier integrity
- outlier flags
- analytical field classification
- analysis calculations
- KPI calculations
- chart selection logic
- Excel-function opportunity detection
- workbook generation

### Semantic AI layer

The language model is used for tasks such as:

- interpreting abbreviated or cryptic field names
- identifying likely domain context
- interpreting important entities
- explaining analytical opportunities
- resolving ambiguity in column meaning
- making recommendations easier for a human analyst to understand

The raw dataset is not sent to the model simply to perform arithmetic. The semantic layer works from a compact structured dataset context.

### Why this separation matters

An LLM is useful for understanding meaning, but it should not be the authority for numerical calculations.

For example:

```text
Dataset
  ↓
Python calculates Total Sales
  ↓
LLM explains what the Sales field appears to represent
```

This makes the system easier to validate and reduces the risk of fabricated numerical results.

---

## Project structure

```text
data_analytics_ai/
│
├── app.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
├── pytest.ini
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── experiments.ipynb
│
├── scripts/
│   ├── test_huggingface.py
│   └── verify_build.py
│
├── src/
│   ├── ingestion/
│   │   └── loader.py
│   │
│   ├── profiling/
│   │   ├── classifier.py
│   │   ├── quality.py
│   │   └── relationships.py
│   │
│   ├── interpretation/
│   │   ├── dictionary.py
│   │   ├── context.py
│   │   └── semantic.py
│   │
│   ├── analysis/
│   │   ├── recommendations.py
│   │   ├── engine.py
│   │   ├── kpis.py
│   │   ├── excel_functions.py
│   │   └── charts.py
│   │
│   ├── ai/
│   │   ├── llm.py
│   │   ├── prompts.py
│   │   └── embeddings.py
│   │
│   ├── excel/
│   │   ├── tables.py
│   │   ├── pivots.py
│   │   ├── charts.py
│   │   └── workbook.py
│   │
│   └── dashboard/
│       └── generator.py
│
└── tests/
    ├── test_loader.py
    ├── test_classifier.py
    ├── test_quality.py
    ├── test_pipeline.py
    ├── test_relationships.py
    ├── test_dictionary.py
    ├── test_recommendations.py
    ├── test_semantic.py
    ├── test_engine.py
    ├── test_kpis.py
    ├── test_excel_functions.py
    ├── test_charts.py
    └── test_workbook.py
```

---

## Application flow

### 1. Upload

The Streamlit app accepts CSV and Excel files.

### 2. Understand

The application profiles the dataset and classifies columns into analytical roles rather than blindly trusting pandas storage dtype.

Examples:

```text
Employee ID       → Potential ID
Order Date        → Date / Time
Sales             → Numerical Measure
Discount          → Rate / Percentage
Age               → Numerical Attribute
Satisfaction      → Score / Rating
Region            → Geographic Code
Segment           → Categorical Dimension
```

An integer is therefore not automatically treated as a measure. A postal code can be numeric while still being a geographic code, and an ID can be numeric while having no meaningful arithmetic interpretation.

### 3. Check quality

The quality layer checks missing values, duplicates, whitespace, cardinality, constant columns, ranges, type anomalies, categorical consistency, identifier integrity, date logic, and potential outliers.

Potential outliers are flagged rather than silently deleted.

### 4. Interpret

A data dictionary and analytical field groups are created.

### 5. Recommend

The application produces dataset-aware recommendations for:

- analysis questions
- KPIs
- Excel functions
- charts

The system recommends tasks supported by the actual field structure rather than presenting generic lists.

### 6. Explore and learn

The **Analysis** tab is an independent analysis workspace. The user can select KPIs and analysis questions, see their calculated results and charts immediately, and use interactive filter controls to change the displayed results.

These exploratory selections do not determine the final workbook.

### 7. Select final deliverable

The **Generate** tab has its own independent selections. The user chooses which KPIs, analysis questions, dashboard filters, and dashboard layout should become part of the final Excel workbook.

### 8. Calculate and preview

Python calculates the selected final KPIs and analysis results from the actual DataFrame, and the Generate tab previews those outputs before workbook creation.

### 9. Choose dashboard layout

Five visual dashboard blueprints are recommended based on dataset capabilities and the user's selected outputs.

Examples include:

- KPI + Left Slicers
- KPI + Trend Focus
- Hero Chart + KPI Strip
- Comparison Board
- Balanced Analytics Grid

The user sees a visual arrangement rather than choosing only an abstract label.

### 11. Generate workbook

The selected outputs are written into a formatted Excel workbook.

---

# Final Excel workbook

The workbook is intentionally structured as an analyst handoff rather than a single giant worksheet.

Typical structure:

```text
00_Read_Me
01_Raw_Data
02_Cleaned_Data
03_Data_Dictionary
KPI_01_...
KPI_02_...
KPI_03_...
Analysis_01
Analysis_02
Analysis_03
...
Excel_Guide
Filter_Guide
Dashboard_Instructions
Dashboard_Template
```

The exact number of KPI and analysis sheets is dynamic.

## `00_Read_Me`

Explains the generated workbook and summarizes what was selected.

## `01_Raw_Data`

Contains the original uploaded values.

## `02_Cleaned_Data`

Contains light standardization such as surrounding whitespace removal from text values and normalization of blank text.

No rows are silently deleted by the workbook generator.

## `03_Data_Dictionary`

Contains the detected analytical role, description, data type, unique values, and missing-value count for every field.

## KPI sheets

Each selected KPI gets its own worksheet.

For example:

```text
KPI_01_Total Sales
```

The sheet contains:

- large KPI value
- KPI category
- calculation
- source fields
- formula logic
- rationale

This makes the KPI understandable rather than simply displaying a number.

## Analysis sheets

Each selected analysis gets its own worksheet.

Each sheet contains:

- the analytical question
- analysis type
- priority
- rationale
- calculated summary table
- generated Excel chart when the result supports one

The summary table is intentionally generated from deterministic calculations.

> The current workbook creates **pivot-style summary tables**, not native Excel PivotTable objects. This keeps the workbook generation reliable with `openpyxl`. Native PivotTable creation can be added later if it becomes a specific requirement.

## `Excel_Guide`

Contains dataset-specific Excel function recommendations, including:

- task
- function
- relevant fields
- when to use it
- example
- learning level
- why the function matters

The guiding principle is:

> **Recommend a function because the dataset creates a real task for it.**

## `Dashboard_Instructions`

Maps dashboard components back to their generated source sheets.

For example:

```text
KPI 1 → KPI_01_Total Sales
Chart 1 → Analysis_01
Chart 2 → Analysis_02
```

This is the bridge between the automated analytical work and the user's final dashboard assembly.

## `Dashboard_Template`

This is deliberately the **final worksheet**.

It visually represents the dashboard arrangement selected by the user.

For example:

```text
┌─────────────────────────────────────────────────────┐
│                 DASHBOARD TITLE                     │
├──────────┬──────────┬──────────┬──────────┐         │
│  KPI 1   │  KPI 2   │  KPI 3   │  KPI 4   │         │
├──────┬───┴──────────┴──────────┴──────────┴─────────┤
│FILTER│              CHART 1                         │
│AREA  │              CHART 2                         │
│      │                                               │
├──────┼───────────────────────────────────────────────┤
│      │              CHART 3                         │
│      │              CHART 4                         │
└──────┴───────────────────────────────────────────────┘
```

The placeholders reference the actual generated KPI and analysis worksheets. Selected dashboard filters are also written into the template and instruction sheets.

The user then performs the final presentation work:

- place/copy the KPI values
- place/copy the generated charts
- optionally add native Excel slicers; the generated workbook also keeps the cleaned data and summary tables filter-ready
- adjust titles, branding, sizing, and presentation style

The project therefore prepares the analytical foundation without pretending that dashboard design is completely automatic.

---

## Dashboard recommendation philosophy

Dashboard layouts are recommended using dataset capabilities such as:

- whether dates are available
- whether meaningful dimensions exist
- whether aggregatable measures exist
- how many KPIs were selected
- how many analyses were selected
- whether the selected analyses are likely to support a dominant visual

The application does not claim that one layout is universally correct. It gives the user several concrete arrangements to choose from.

---

## KPI philosophy

KPIs are generated from analytical roles rather than blindly summing every numeric column.

Examples:

```text
Employee ID → Total Employees
Sales       → Total Sales / Average Sales
Discount    → Average Discount
Rating      → Average Rating
Profit + Sales → Profit Margin
```

IDs are treated as distinct entities when appropriate, not as arithmetic measures.

Rates and percentages are normally averaged or otherwise interpreted as rates rather than summed.

The recommendation describes the calculation; Python performs it.

---

## Chart philosophy

Chart recommendations are tied to analytical questions.

Examples:

```text
Time Trend            → Line Chart
Ranking               → Horizontal Bar Chart
Dimension Comparison  → Bar Chart
Contribution          → Column Chart
Attribute Comparison  → Column Chart
Rate Trend            → Line Chart
```

The same analysis definition is intended to drive:

```text
Analysis definition
        ├── result table
        ├── chart
        ├── chart explanation
        ├── Excel lesson
        └── dashboard placement
```

This prevents different parts of the application from independently inventing interpretations of the same question.

---

## Hugging Face configuration

The current semantic layer uses the OpenAI-compatible Hugging Face router.

`.env` should contain:

```text
HF_TOKEN=your_huggingface_token
HF_MODEL=openai/gpt-oss-120b
```

Do not commit `.env` or API tokens to GitHub.

`.env.example` is provided as the safe template.

The deterministic application remains usable even when semantic AI is unavailable; the semantic layer is handled defensively by the pipeline.

---

## Installation

Create and activate a virtual environment, then install the requirements:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the application:

```powershell
streamlit run app.py
```

---

## Testing

Run the full test suite:

```powershell
python -m pytest -q
```

The current release includes tests for:

- ingestion
- column classification
- quality profiling
- relationships
- data dictionary
- recommendations
- semantic context
- analysis engine
- KPI recommendations and calculations
- Excel function recommendations
- chart recommendations
- dashboard layout recommendations
- workbook structure and chart generation

The release verification script provides an additional integration smoke test:

```powershell
python scripts/verify_build.py
```

When the bundled Superstore sample is available, this also generates a temporary workbook and verifies that:

- KPI sheets are generated
- analysis sheets are generated
- charts are embedded
- five dashboard layouts are available
- `Dashboard_Template` is the final worksheet

---

## GitHub workflow

Before the first GitHub push:

1. Confirm `.env` is ignored.
2. Do not commit API keys or access tokens.
3. Run:

```powershell
python -m pytest -q
python scripts/verify_build.py
```

4. Run the Streamlit application locally.
5. Upload the Superstore sample and generate a workbook.
6. Open the generated workbook and inspect the sheets and dashboard template.

A useful commit sequence for this project is:

```text
Initial analytical foundation
↓
Recommendation engine
↓
KPI + chart selection
↓
Workbook generation
↓
Dashboard blueprint
↓
Future refinements
```

Keep commits focused so regressions can be traced easily.

---

## Current status

The project currently supports:

- CSV/XLSX ingestion
- analytical column classification
- data-quality profiling
- relationship validation
- data dictionary generation
- semantic interpretation through Hugging Face
- analysis recommendations
- KPI recommendations
- deterministic KPI calculation
- Excel-function recommendations
- chart recommendations
- interactive KPI and analysis preview
- five dataset-aware dashboard layout recommendations
- dataset-aware filter/slicer recommendations and a filter teaching guide
- a dedicated Generate tab for layout, filter confirmation, preview, and workbook creation
- formatted Excel workbook generation
- one worksheet per selected KPI
- one worksheet per selected analysis
- generated Excel charts for supported analyses
- Excel learning guide
- dashboard instructions
- final dashboard template worksheet

The next refinements can focus on presentation quality, richer Excel functionality, native PivotTable support, dashboard customization, and additional analytical intelligence rather than rebuilding the core pipeline.

---

## Future extensions

Possible future directions include:

### Embeddings

Useful for semantic similarity and retrieval between column meanings, historical analysis patterns, and business terminology.

### RAG

Useful when external knowledge becomes available, such as:

- business glossaries
- company-specific metric definitions
- documentation
- historical analysis patterns

### Classical machine learning

Potential future applications include:

- anomaly detection
- clustering
- segmentation
- prediction
- pattern discovery

### Learning from validated analysis patterns

The system should not blindly train on every uploaded dataset.

A safer future pattern is:

```text
Uploaded Dataset
      ↓
Detected Pattern
      ↓
User Validation / Selection
      ↓
Successful Analysis Pattern
      ↓
Pattern Library
      ↓
Future Recommendation Improvement
```

This creates a path toward a system that improves from validated analytical patterns without treating every generated output as ground truth.

---

## Design philosophy

The project is ultimately trying to guide a user through:

**Understand → Clean → Interpret → Recommend → Select → Calculate → Visualize → Explain → Teach → Prepare Dashboard**

The human does:

**Select → Review → Customize → Present**

The goal is not to replace the analyst. It is to remove the uncertainty that usually comes between receiving a new dataset and knowing what to do with it.
