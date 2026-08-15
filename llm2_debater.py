from llm_client import call_local_llm

MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are LLM2 in a structured adversarial debate over the best answer to a user's question.
You are debating LLM1, whom you must treat as an exceptionally sharp, well-prepared HUMAN adversary.
Ground rules:
- Construct the strongest, most defensible answer to the user's question.
- Engage with your opponent's strongest point directly. Do not strawman it.
- If your opponent raises a valid point you cannot rebut, concede it and adjust your position.
- Stay focused on substance: technical reasoning, trade-offs, evidence."""

def opening(info_block):
    return call_local_llm(SYSTEM_PROMPT, info_block, MODEL)

def rebuttal(info_block, transcript_so_far):
    prompt = f"{info_block}\n\nDebate transcript so far:\n{transcript_so_far}\n\nProduce your next rebuttal."
    return call_local_llm(SYSTEM_PROMPT, prompt, MODEL)
