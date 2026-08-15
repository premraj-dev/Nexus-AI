import re
import datetime
from services.rag_service import rag_service
from llm1_debater import run_llm1
from llm2_debater import run_llm2
from llm3_referee import evaluate_and_referee
from llm_client import call_local_llm

def is_time_sensitive(prompt: str) -> bool:
    # Rule 1: Year regex + temporal keywords detection
    temporal_pattern = r'\b(2025|2026|2027|latest|current|today|yesterday|upcoming|releasing|this week|next month)\b'
    return bool(re.search(temporal_pattern, prompt, re.IGNORECASE))

def route_and_execute(prompt: str) -> dict:
    time_flag = is_time_sensitive(prompt)
    
    if time_flag:
        # Rule 2: Force mandatory live research
        research_data = rag_service.fetch_research(prompt)
        research_context = f"STRUCTURED 2026 METADATA:\n{research_data['structured_data']}\n\nRAW SNIPPETS:\n{research_data['raw_context']}"
    else:
        research_context = "No temporal research required for general non-time-sensitive query."

    transcript = ""
    max_rounds = 2
    current_round = 1
    final_answer = ""
    
    while current_round <= max_rounds:
        # Debaters receive query + structured temporal research context
        op1 = run_llm1(prompt, research_context, transcript)
        transcript += f"\n--- Round {current_round} [LLM 1] ---\n{op1}\n"
        
        op2 = run_llm2(prompt, research_context, transcript)
        transcript += f"\n--- Round {current_round} [LLM 2] ---\n{op2}\n"
        
        # Referee enforces temporal validation
        eval_result = evaluate_and_referee(prompt, research_context, transcript, current_round, time_flag)
        
        if eval_result.get("stop", False) or current_round == max_rounds:
            final_answer = eval_result.get("final_response", "")
            if not final_answer:
                final_answer = op2 if op2 else op1
            break
            
        current_round += 1

    return {
        "mode": "MULTI_AGENT_DEBATE",
        "time_sensitive": time_flag,
        "rounds": current_round,
        "response": final_answer
    }
