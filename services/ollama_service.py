import os
from dotenv import load_dotenv
from groq import Groq

# Explicitly load .env file from working directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def generate_llm_response(prompt: str, system_prompt: str = "", model: str = "llama-3.1-8b-instant") -> str:
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
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error executing model: {str(e)}"

class OllamaService:
    def generate(self, prompt: str, system_prompt: str = "", model: str = "llama-3.1-8b-instant") -> str:
        return generate_llm_response(prompt=prompt, system_prompt=system_prompt, model=model)

ollama_service = OllamaService()
