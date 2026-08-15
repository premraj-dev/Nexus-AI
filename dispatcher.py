import json
import logging
from llm_client import call_local_llm, parse_json_response
import orchestrator

logging.basicConfig(
    filename="system_routing.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

MODEL = "llama3.2:3b"

ROUTER_PROMPT = """You are the ROUTER for an AI system. Classify the user query into strictly ONE mode:

DIRECT: simple factual questions, recipes, definitions, or standard how-to questions.
EXPERT: code generation, script writing, debugging, or specialist execution.
DECISION: complex architectural trade-offs, strategic choices, or competing options.
CLARIFY: queries missing critical constraints (such as budget, tech stack, or scale) needed to answer accurately.

Output STRICT JSON only:
{"mode": "DIRECT" | "EXPERT" | "DECISION" | "CLARIFY", "reason": "<one short sentence>"}"""

DIRECT_PROMPT = "You are a helpful assistant. Provide a complete, direct answer without metadata, labels, or agent talk."
EXPERT_PROMPT = "You are a specialist technical assistant. Deliver a concise, working solution or code snippet without unnecessary commentary."
CLARIFY_PROMPT = "Ask 2-3 short, numbered clarifying questions needed to narrow down constraints before providing an answer."

def route_and_execute(user_query: str, user_context: str = "") -> dict:
    raw_route = call_local_llm(ROUTER_PROMPT, f"Query: {user_query}", model=MODEL)
    try:
        route_data = parse_json_response(raw_route)
        mode = route_data.get("mode", "DIRECT")
    except Exception:
        mode = "DIRECT"

    rounds_run = 0
    if mode == "DIRECT":
        output = call_local_llm(DIRECT_PROMPT, user_query, model=MODEL)
    elif mode == "EXPERT":
        output = call_local_llm(EXPERT_PROMPT, user_query, model=MODEL)
    elif mode == "CLARIFY":
        output = call_local_llm(CLARIFY_PROMPT, user_query, model=MODEL)
    elif mode == "DECISION":
        output, transcript, rounds_run = orchestrator.run_debate(user_query, user_context)
    else:
        output = call_local_llm(DIRECT_PROMPT, user_query, model=MODEL)

    logging.info(f"QUERY: '{user_query}' | MODE: {mode} | ROUNDS: {rounds_run}")

    return {
        "mode": mode,
        "output": output,
        "rounds_run": rounds_run
    }
