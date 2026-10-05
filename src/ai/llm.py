import json
import os

from dotenv import load_dotenv

from src.ai.prompts import SYSTEM_PROMPT, build_semantic_prompt


load_dotenv()


def get_hf_token():
    """Return the Hugging Face API token from the environment."""
    token = os.getenv("HF_TOKEN")

    if not token:
        raise RuntimeError(
            "HF_TOKEN is not configured. "
            "Add your Hugging Face token to the .env file."
        )

    return token


def get_model_name():
    """Return the configured Hugging Face model."""
    return os.getenv(
        "HF_MODEL",
        "openai/gpt-oss-120b",
    )


def get_client():
    """Create an OpenAI-compatible client connected to Hugging Face."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required for Hugging Face's "
            "OpenAI-compatible endpoint. Run: pip install openai"
        ) from exc

    return OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=get_hf_token(),
        timeout=90.0,
        max_retries=2,
    )


def is_llm_configured():
    """Check whether the Hugging Face token is available."""
    token = os.getenv("HF_TOKEN")
    return bool(token)


def _extract_json(content):
    """Parse JSON even when a compatible model wraps it in a code fence."""
    if not content:
        raise RuntimeError("The Hugging Face model returned an empty response.")
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise RuntimeError("The model returned invalid JSON.")


def _fallback_interpretation(dataset_context, reason=None):
    """Return a deterministic, honest interpretation when the LLM is unavailable."""
    dataset = dataset_context.get("dataset", {}) if isinstance(dataset_context, dict) else {}
    columns = dataset_context.get("columns", []) if isinstance(dataset_context, dict) else []
    recommendations = dataset_context.get("deterministic_recommendations", []) if isinstance(dataset_context, dict) else []
    quality = dataset_context.get("quality_summary", {}) if isinstance(dataset_context, dict) else {}

    measures = [c.get("name") for c in columns if c.get("classification") == "Numerical Measure"]
    dimensions = [c.get("name") for c in columns if c.get("classification") in {"Categorical Dimension", "Geographic Code", "Ordinal"}]
    dates = [c.get("name") for c in columns if c.get("classification") == "Date / Time"]
    ids = [c.get("name") for c in columns if c.get("classification") == "Potential ID"]

    if measures and dimensions:
        summary = (
            f"This dataset contains {dataset.get('rows', 0):,} records and appears to combine measurable outcomes "
            f"such as {', '.join(map(str, measures[:3]))} with grouping fields such as {', '.join(map(str, dimensions[:4]))}."
        )
    else:
        summary = (
            f"This dataset contains {dataset.get('rows', 0):,} records across {dataset.get('columns', 0):,} fields. "
            "Its structure can be understood from the field roles shown below."
        )

    important_fields = []
    for item in columns:
        cls = item.get("classification", "Unclassified")
        desc = item.get("deterministic_description") or f"This field is classified as {cls}."
        important_fields.append({
            "column": item.get("name"),
            "interpreted_role": cls,
            "meaning": desc,
            "confidence": "Medium" if cls != "Unclassified" else "Low",
        })

    opportunities = []
    for rec in recommendations[:6]:
        if isinstance(rec, dict):
            opportunities.append({
                "question": rec.get("Question", "Explore this field"),
                "reason": rec.get("Rationale", "This recommendation comes from the deterministic analytical profile."),
                "priority": rec.get("Priority", "Medium"),
                "required_fields": [str(x) for x in [rec.get("Measure"), rec.get("Dimension"), rec.get("Date Column")] if x and str(x) != "nan"],
            })

    ambiguities = []
    for item in columns:
        if item.get("classification") == "Unclassified":
            ambiguities.append({
                "column": item.get("name"),
                "issue": "The field could not be classified confidently from structure alone",
                "suggestion": "Use the observed values and business context to confirm what it represents.",
            })

    return {
        "enabled": False,
        "success": False,
        "model": None,
        "data": {
            "dataset_summary": summary,
            "likely_domain": "Uncertain without semantic AI",
            "confidence": "Low",
            "entities": ids[:6],
            "important_fields": important_fields,
            "analytical_opportunities": opportunities,
            "ambiguities": ambiguities,
        },
        "message": reason or "Semantic AI is unavailable; deterministic interpretation is being used instead.",
    }


def interpret_dataset(dataset_context):
    """Interpret the compact dataset context with HF, with a deterministic fallback."""
    try:
        client = get_client()
        prompt = build_semantic_prompt(dataset_context)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "dataset_semantic_interpretation",
                        "schema": SEMANTIC_SCHEMA,
                    },
                },
            )
            parsed = _extract_json(response.choices[0].message.content)
        except Exception:
            fallback_prompt = prompt + "\nReturn ONLY a valid JSON object matching the requested fields. No markdown."
            response = client.chat.completions.create(
                model=get_model_name(),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": fallback_prompt},
                ],
            )
            parsed = _extract_json(response.choices[0].message.content)

        return {
            "enabled": True,
            "success": True,
            "model": get_model_name(),
            "data": parsed,
        }
    except Exception as exc:
        return _fallback_interpretation(dataset_context, f"Semantic AI is temporarily unavailable: {exc}")


SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "dataset_summary": {
            "type": "string"
        },
        "likely_domain": {
            "type": "string"
        },
        "confidence": {
            "type": "string",
            "enum": [
                "High",
                "Medium",
                "Low"
            ]
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "important_fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {
                        "type": "string"
                    },
                    "interpreted_role": {
                        "type": "string"
                    },
                    "meaning": {
                        "type": "string"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low"
                        ]
                    }
                },
                "required": [
                    "column",
                    "interpreted_role",
                    "meaning",
                    "confidence"
                ],
                "additionalProperties": False
            }
        },
        "analytical_opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string"
                    },
                    "reason": {
                        "type": "string"
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low"
                        ]
                    },
                    "required_fields": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "question",
                    "reason",
                    "priority",
                    "required_fields"
                ],
                "additionalProperties": False
            }
        },
        "ambiguities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "column": {
                        "type": "string"
                    },
                    "issue": {
                        "type": "string"
                    },
                    "suggestion": {
                        "type": "string"
                    }
                },
                "required": [
                    "column",
                    "issue",
                    "suggestion"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "dataset_summary",
        "likely_domain",
        "confidence",
        "entities",
        "important_fields",
        "analytical_opportunities",
        "ambiguities"
    ],
    "additionalProperties": False
}

def _fallback_question_answer(dataset_context, question, reason):
    """Answer common dataset-orientation questions without pretending to be an LLM."""
    q = question.lower()
    columns = dataset_context.get("columns", []) if isinstance(dataset_context, dict) else []
    quality = dataset_context.get("quality_summary", {}) if isinstance(dataset_context, dict) else {}
    summary = dataset_context.get("dataset", {}) if isinstance(dataset_context, dict) else {}

    if any(term in q for term in ["what is this dataset", "dataset about", "what does this data"]):
        measures = [c.get("name") for c in columns if c.get("classification") == "Numerical Measure"]
        dims = [c.get("name") for c in columns if c.get("classification") in {"Categorical Dimension", "Geographic Code", "Ordinal"}]
        answer = f"This dataset has {summary.get('rows', 0):,} rows and {summary.get('columns', 0):,} columns."
        if measures: answer += f" Its main measurable fields include {', '.join(map(str, measures[:5]))}."
        if dims: answer += f" You can break those measures down by fields such as {', '.join(map(str, dims[:5]))}."
    elif any(term in q for term in ["quality", "missing", "duplicate", "clean"]):
        answer = (f"The current profile reports {quality.get('Total Missing Values', 0):,} missing values and "
                  f"{quality.get('Duplicate Rows', 0):,} exact duplicate rows. Open Data Quality for the issue-specific findings and lessons.")
    else:
        mentioned = next((c for c in columns if str(c.get("name", "")).lower() in q), None)
        if mentioned:
            answer = (f"{mentioned.get('name')} is classified as {mentioned.get('classification', 'Unclassified')}. "
                      f"The observed sample values include {', '.join(map(str, mentioned.get('sample_values', [])[:5])) or 'no representative non-missing values'}. "
                      "Use Data Guide for the full field explanation.")
        else:
            answer = ("I can answer that when the Hugging Face model is available. For now, Data Guide still contains the dataset structure, "
                      "field interpretations, quality findings and analysis recommendations, so you can continue without losing the work.")
    return answer + f"\n\nNote: {reason}"


def ask_dataset_question(dataset_context, question):
    """Answer a natural-language dataset question, with a safe fallback on service failure."""
    try:
        client = get_client()
        context_text = json.dumps(dataset_context, indent=2, default=str)
        prompt = f"""
You are DataGuide's persistent dataset assistant.

Answer the user's question using ONLY the supplied structured dataset context.
Python has already calculated deterministic facts. Do not invent statistics or
claim to have inspected raw rows that are not represented in the context.

Speak like a knowledgeable human analyst explaining something to a non-technical
person: clear, natural, direct, and conversational. Avoid canned phrases.

Rules:
- Every column you mention must exist in the context.
- Use concrete examples from THIS dataset whenever useful.
- Never invent values, categories, meanings, or statistics.
- If evidence is insufficient, say so clearly.
- Explain analytics concepts simply.
- If asked what to analyze next, recommend 1-3 useful next steps.
- If asked about quality, use the actual detected issue and count.
- Do not use generic placeholder examples.

USER QUESTION:
{question}

DATASET CONTEXT:
{context_text}

Return concise, user-friendly text.
"""
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("The Hugging Face model returned an empty response.")
        return {"enabled": True, "success": True, "model": get_model_name(), "question": question, "answer": content.strip()}
    except Exception as exc:
        return {"enabled": False, "success": False, "model": None, "question": question, "answer": _fallback_question_answer(dataset_context, question, str(exc))}
