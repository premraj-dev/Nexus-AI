from llm_client import call_local_llm, parse_json_response

MODEL = "llama3.2:3b"

CONVERGENCE_SYSTEM_PROMPT = """You are the Debate Referee (LLM3). Judge whether continuing the debate is producing genuine improvement.
Output STRICT JSON only, matching this structure:
{"converged": true or false, "reasoning": "one sentence"}"""

SYNTHESIS_SYSTEM_PROMPT = """You are the Debate Referee (LLM3), producing the final answer for the user.
Synthesize ONE best answer based on the debate transcript.
Rules:
- Never mention "LLM1," "LLM2," "the debate," or internal processes.
- Write in one authoritative, helpful voice.
- Be direct: lead with the answer, then the supporting reasoning."""

def check_convergence(full_transcript):
    raw = call_local_llm(CONVERGENCE_SYSTEM_PROMPT, f"Analyze transcript for convergence:\n{full_transcript}", MODEL)
    try:
        return parse_json_response(raw)
    except Exception:
        return {"converged": False, "reasoning": "Failed to parse JSON, continuing debate"}

def synthesize(user_query, full_transcript):
    prompt = f"User's original question: {user_query}\n\nFull debate transcript:\n{full_transcript}"
    return call_local_llm(SYNTHESIS_SYSTEM_PROMPT, prompt, MODEL)
