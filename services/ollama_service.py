import os
import json
import re
from typing import Type, TypeVar

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError

# Explicitly load .env file from working directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama-3.1-8b-instant"

T = TypeVar("T", bound=BaseModel)


def _extract_json(raw_text: str) -> dict:
    """Strip markdown fences and parse JSON, falling back to a brace-matching scan
    if the model wrapped its JSON in extra prose."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def generate_llm_response(prompt: str, system_prompt: str = "", model: str = DEFAULT_MODEL) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return "Error: GROQ_API_KEY environment variable not set in .env file."

    local_client = Groq(api_key=key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = local_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error executing model: {str(e)}"


class OllamaService:
    """Named for the original local-Ollama path; now calls Groq's hosted API.
    Kept the name/interface so callers (agents, graph) don't need to change."""

    def generate(self, prompt: str, system_prompt: str = "", model: str = DEFAULT_MODEL) -> str:
        return generate_llm_response(prompt=prompt, system_prompt=system_prompt, model=model)

    def generate_structured(
        self,
        system_prompt: str,
        user_content: str,
        schema: Type[T],
        model: str = DEFAULT_MODEL,
    ) -> T:
        """Calls the model, parses the response as JSON, and validates it against
        a Pydantic schema. Retries once, feeding the validation error back to the
        model, before giving up."""
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            raise RuntimeError("GROQ_API_KEY environment variable not set in .env file.")

        local_client = Groq(api_key=key)
        schema_hint = (
            "\n\nRespond with STRICT JSON only, matching this schema exactly. "
            "No markdown fences, no commentary, no extra keys:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        full_system_prompt = system_prompt + schema_hint

        def _call(extra_note: str = "") -> T:
            messages = [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_content + extra_note},
            ]
            response = local_client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.4,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            data = _extract_json(raw)
            return schema.model_validate(data)

        try:
            return _call()
        except (ValidationError, ValueError, json.JSONDecodeError) as first_err:
            try:
                return _call(
                    f"\n\nYour previous response was invalid ({first_err}). "
                    "Return corrected STRICT JSON only, matching the schema."
                )
            except Exception as second_err:
                raise RuntimeError(
                    f"generate_structured failed after retry: {second_err}"
                ) from second_err


ollama_service = OllamaService()
