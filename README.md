# DataGuide

DataGuide is a guided data-analysis workspace designed to help a user understand a dataset without needing to move between Python, Excel, and Power BI just to get started.

## Product flow

**Upload → Overview → Data Quality → Ask DataGuide → Analysis**

### Overview

DataGuide shows:
- row and column counts
- storage data types
- a data preview
- detected analytical roles such as IDs, dates, dimensions, measures, rates, scores, and geographic fields
- an AI-assisted first interpretation when the Hugging Face model is available

### Data Quality

DataGuide only teaches issues actually detected in the uploaded dataset. Depending on the file, this can include:
- missing values
- exact duplicate rows
- leading/trailing whitespace
- category inconsistencies
- values outside expected ranges
- storage-type anomalies
- identifier integrity
- invalid date relationships
- IQR-based potential outliers
- constant columns

Each lesson explains:
- what the issue means
- why it can affect analysis
- an example from the uploaded dataset itself
- how the issue is detected
- how it can be handled

Safe, deterministic cleaning actions can be approved by the user. When applied, the cleaned working dataset becomes the basis for all downstream analysis. The original upload remains unchanged.

### Ask DataGuide

Users can ask natural-language questions such as:
- What is this dataset about?
- What are the important fields?
- What should I analyze first?
- What does this column mean?
- What data-quality issue should I understand?

The LLM receives a compact, deterministic dataset context rather than the raw dataset. Python remains responsible for calculations; the LLM is responsible for interpretation and explanation.

### Analysis

The Analysis workspace recommends dataset-appropriate:
- KPIs
- analytical questions
- comparisons
- rankings
- contributions
- trends
- distributions
- outlier investigations
- charts

The user can filter the working dataset, run recommended analyses, compare suitable visual forms, and learn why a visual is appropriate.

The first recommendations are intentionally limited so the workspace guides the user instead of presenting an overwhelming catalogue. Additional recommendations are available when needed.

## Excel output

Excel workbook generation is no longer part of the user-facing DataGuide workflow. The previous Excel implementation remains isolated in the repository as legacy code so it can be revisited later if the product direction changes, but the application does not generate or download workbooks.

## AI architecture

The core design is:

```text
Uploaded Dataset
      ↓
Deterministic Profiling
      ↓
Dataset Context
      ↓
┌───────────────────────┐
│                       │
│  Python Analytics     │──→ Calculations / Quality / Recommendations
│                       │
│  Hugging Face LLM     │──→ Interpretation / Q&A / Explanations
│                       │
└───────────────────────┘
```

The semantic context contains dataset structure, field metadata, representative values, deterministic summaries, quality findings, and analytical recommendations. The full raw dataset is not sent to the LLM.

## Hugging Face configuration

Create `.env` from `.env.example`:

```text
HF_TOKEN=your_huggingface_token
HF_MODEL=openai/gpt-oss-120b
```

The application uses Hugging Face's OpenAI-compatible router.

If the LLM is unavailable, deterministic profiling and analysis continue to work. Ask DataGuide reports the configuration/API problem instead of silently inventing an answer.

## Run

```powershell
streamlit run app.py
```

## Testing

```powershell
pytest -q
python scripts/verify_build.py
```

The release verification script checks the deterministic pipeline, recommendations, cleaning logic, analysis engine, and legacy workbook compatibility tests. Workbook generation is not exposed by the application.

## Current DataGuide experience

DataGuide is organized as a guided story:

1. **Overview** — get a quick map of the dataset: size, structure, storage types and analytical roles.
2. **Data Guide** — understand what the dataset appears to represent, what each column means, how fields work together, and what questions the data can answer.
3. **Data Quality** — learn only about quality issues actually detected in the uploaded dataset, with dataset-specific examples and approval-based cleaning.
4. **Data Analysis** — follow dataset-aligned KPIs, analytical questions, filters and visual recommendations.

A persistent **Ask DataGuide** assistant stays available in the bottom-right corner. It is deliberately separate from Data Guide: the Guide teaches the dataset as a whole, while the assistant answers ad-hoc questions about the dataset.

### AI architecture

The product follows a simple boundary:

> **Python determines what the data says; the LLM helps explain what the data means.**

Deterministic Python handles profiling, quality checks, field roles, calculations, recommendations and chart logic. Hugging Face provides the semantic interpretation and natural-language question layer. The application also has deterministic fallbacks so a temporary LLM/API failure does not break the dataset guide or analysis workspace.

Configure the LLM with:

```text
HF_TOKEN=your_huggingface_token
HF_MODEL=openai/gpt-oss-120b
```
