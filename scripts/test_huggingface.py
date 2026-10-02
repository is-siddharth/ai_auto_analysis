import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


token = os.getenv("HF_TOKEN")
model = os.getenv(
    "HF_MODEL",
    "openai/gpt-oss-120b:fireworks-ai",
)


if not token:
    raise RuntimeError(
        "HF_TOKEN was not found. Check your .env file."
    )


client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=token,
)


response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": (
                "Reply with exactly one sentence confirming "
                "that the Hugging Face model connection works."
            ),
        }
    ],
)


print("Model:", model)
print("Response:")
print(response.choices[0].message.content)