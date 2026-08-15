from llm_client import call_local_llm

def run_llm1(prompt: str, research: str, transcript: str) -> str:
    system_prompt = (
        "You are Debater 1 (Perspective A). Analyze the query, web research, and prior debate transcript. "
        "Provide a factual, structured argument or refined solution. Focus on accuracy and key details."
    )
    user_prompt = f"QUERY: {prompt}\n\nRESEARCH:\n{research}\n\nPREVIOUS DEBATE TRANSCRIPT:\n{transcript}"
    return call_local_llm(user_prompt, system_prompt)
