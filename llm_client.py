import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)


def call_local_llm(prompt: str, system_prompt: str = "", model: str = "llama-3.1-8b-instant") -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return "Error: GROQ_API_KEY environment variable not set in .env file."

    client = Groq(api_key=key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


def call_llm(prompt: str, system_prompt: str = "", model: str = "llama-3.1-8b-instant") -> str:
    return call_local_llm(prompt, system_prompt, model)


def parse_json_response(text: str) -> dict:
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception:
        return {}