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
        "openai/gpt-oss-120b:fireworks-ai",
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
    )


def is_llm_configured():
    """Check whether the Hugging Face token is available."""
    token = os.getenv("HF_TOKEN")
    return bool(token)


def interpret_dataset(dataset_context):
    """
    Send dataset context to the Hugging Face model and return
    structured semantic interpretation.
    """
    client = get_client()

    prompt = build_semantic_prompt(dataset_context)

    response = client.chat.completions.create(
        model=get_model_name(),
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "dataset_semantic_interpretation",
                "schema": SEMANTIC_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "The Hugging Face model returned an empty response."
        )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The model returned invalid JSON."
        ) from exc

    return {
        "enabled": True,
        "success": True,
        "model": get_model_name(),
        "data": parsed,
    }


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