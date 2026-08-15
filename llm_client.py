import json
import re
import ollama

def call_local_llm(system_prompt, user_content, model="llama3.2:3b"):
    response = ollama.generate(
        model=model,
        system=system_prompt,
        prompt=user_content
    )
    return response.get("response", "")

def parse_json_response(raw_text):
    cleaned = re.sub(r"^`(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*`$", "", cleaned, flags=re.MULTILINE).strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Failed to parse JSON: {raw_text}")
