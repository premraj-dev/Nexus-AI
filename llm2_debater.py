from llm_client import call_local_llm

def run_llm2(prompt: str, research: str, transcript: str) -> str:
    system_prompt = (
        "You are Debater 2 (Perspective B). Review Debater 1's points, the research context, and prior debate. "
        "Identify missing details, correct factual flaws, or propose a stronger, more complete alternative."
    )
    user_prompt = f"QUERY: {prompt}\n\nRESEARCH:\n{research}\n\nPREVIOUS DEBATE TRANSCRIPT:\n{transcript}"
    return call_local_llm(user_prompt, system_prompt)
