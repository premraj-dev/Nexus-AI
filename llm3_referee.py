import json
import datetime
from llm_client import call_local_llm

def evaluate_and_referee(prompt: str, research: str, transcript: str, current_round: int, time_flag: bool) -> dict:
    today_str = datetime.date.today().strftime('%B %d, %Y')
    
    system_prompt = (
        f"You are LLM 3 (Referee & Chief Evaluator). Today's date is {today_str}.\n\n"
        "STRICT VALIDATION RULES:\n"
        "1. RULE 3 & 5: NEVER recommend movies released prior to 2026 (e.g. Pathaan [2023], Tiger 3 [2023], Laal Singh Chaddha [2022]) when asked for 2026 movies. Doing so is a CRITICAL FAILURE.\n"
        "2. RULE 4: Validate that every recommended movie has release_year == 2026 based ONLY on the provided research.\n"
        "3. RULE 6: If the structured research contains no verified 2026 titles, explicitly state: 'Reliable real-time release data for this specific query could not be verified from live web results.' Do NOT invent titles.\n"
        "4. RULE 7 (INTENT DISAMBIGUATION): If the query asks for 'best movie of 2026', explicitly split your answer into two distinct categories:\n"
        "   - Category A: Best Bollywood Movies Released So Far in 2026\n"
        "   - Category B: Most Anticipated Upcoming Bollywood Movies of 2026\n\n"
        "Return STRICT JSON format:\n"
        "{\n"
        '  "stop": true,\n'
        '  "reason": "Validation notes",\n'
        '  "final_response": "Synthesized final answer strictly formatted to rules"\n'
        "}"
    )
    
    user_prompt = (
        f"USER QUERY: {prompt}\n"
        f"TIME SENSITIVE: {time_flag}\n\n"
        f"VERIFIED RESEARCH CONTEXT:\n{research}\n\n"
        f"DEBATE TRANSCRIPT:\n{transcript}"
    )
    
    raw_response = call_local_llm(user_prompt, system_prompt)
    
    try:
        json_start = raw_response.find('{')
        json_end = raw_response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            return json.loads(raw_response[json_start:json_end])
    except Exception:
        pass

    return {"stop": True, "reason": "Fallback completion", "final_response": raw_response}
