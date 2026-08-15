from concurrent.futures import ThreadPoolExecutor
import llm1_debater
import llm2_debater
import llm3_referee

MAX_ROUNDS = 3

def format_transcript(rounds):
    lines = []
    for r in rounds:
        lines.append(f"--- Round {r['round']} ---")
        lines.append(f"LLM1: {r['llm1']}")
        lines.append(f"LLM2: {r['llm2']}")
    return "\n\n".join(lines)

def run_parallel(fn_a, args_a, fn_b, args_b):
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(fn_a, *args_a)
        future_b = executor.submit(fn_b, *args_b)
        return future_a.result(), future_b.result()

def run_debate(user_query, user_context=""):
    info_block = f"User's question: {user_query}"
    if user_context:
        info_block += f"\n\nAdditional context about the user: {user_context}"

    rounds = []
    print("-> Running Round 1 (Opening Arguments)...")
    llm1_out, llm2_out = run_parallel(
        llm1_debater.opening, (info_block,),
        llm2_debater.opening, (info_block,)
    )
    rounds.append({"round": 1, "llm1": llm1_out, "llm2": llm2_out})

    for round_num in range(2, MAX_ROUNDS + 1):
        print(f"-> Running Round {round_num} (Rebuttals)...")
        transcript_so_far = format_transcript(rounds)
        llm1_out, llm2_out = run_parallel(
            llm1_debater.rebuttal, (info_block, transcript_so_far),
            llm2_debater.rebuttal, (info_block, transcript_so_far)
        )
        rounds.append({"round": round_num, "llm1": llm1_out, "llm2": llm2_out})

        verdict = llm3_referee.check_convergence(format_transcript(rounds))
        print(f"   Convergence Check: {verdict}")
        if verdict.get("converged"):
            print("-> Debate Converged! Halting debate.")
            break

    print("-> Synthesizing Final Answer...")
    final_transcript = format_transcript(rounds)
    final_answer = llm3_referee.synthesize(user_query, final_transcript)

    return final_answer, final_transcript, len(rounds)

if __name__ == "__main__":
    query = "Should I use PostgreSQL or MongoDB for my AI application with 10,000 users?"
    answer, transcript, rounds_run = run_debate(query)
    print(f"\n[debug] Rounds Run: {rounds_run}\n")
    print("--- FINAL ANSWER (user-facing) ---\n")
    print(answer)
