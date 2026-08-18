"""
Nexus AI debate graph.

Flow (matches the target architecture):
  1. User query
  2. LLM3 clarification interview          -> generate_clarifying_questions()
  3. LLM1 proposes Option A                -> ideator node
  4. LLM2 challenges & proposes Option B   -> critic node
  5. LLM3 judges convergence               -> convergence node
        - not converged & rounds remain -> loop back to step 3 (another round)
        - converged OR rounds exhausted -> extract
  6. Extract Option A & Option B (raw debate transcript)
  7. LLM3 synthesizes ONE final answer from the full debate -> synthesize node
  8. UI display + SQLite logging happen OUTSIDE this graph,
     in the calling app, once run_debate() returns a DebateResult.
"""

from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from agents.debate_agents import (
    clarification_agent,
    ideator_agent,
    critic_agent,
    convergence_agent,
    synthesis_agent,
    router_agent,
    direct_answer_agent,
    live_answer_agent,
    explanation_writer_agent,
    explanation_reviewer_agent,
    explanation_synthesis_agent,
    explanation_fallback_agent,
)
from models.schemas import (
    DualOption,
    ClarificationQuestions,
    DebateResult,
    SynthesizedAnswer,
    RouterDecision,
    DirectAnswer,
    LiveResult,
    ExplanationDraft,
    ExplanationSynthesis,
)
from services.live_data_service import get_live_context, search_web
from services.rag_service import rag_service

MAX_ROUNDS = 3


class DebateState(TypedDict):
    user_query: str
    clarification_answers: Optional[str]
    conversation: Optional[str]
    context: str
    round: int
    transcript: List[Dict[str, Any]]  # [{"round": n, "option_a": DualOption, "option_b": DualOption}, ...]
    option_a: Optional[DualOption]
    option_b: Optional[DualOption]
    converged: bool
    convergence_reasoning: str
    synthesis: Optional[SynthesizedAnswer]


def format_transcript(transcript: List[Dict[str, Any]]) -> str:
    lines = []
    for r in transcript:
        lines.append(f"--- Round {r['round']} ---")
        lines.append(f"Option A: {r['option_a'].model_dump_json()}")
        lines.append(f"Option B: {r['option_b'].model_dump_json()}")
    return "\n\n".join(lines)


def context_prep_node(state: DebateState) -> Dict[str, Any]:
    combined = f"User Request: {state['user_query']}"
    if state.get("conversation"):
        combined = f"Conversation so far:\n{state['conversation']}\n\n{combined}"
    if state.get("clarification_answers"):
        combined += f"\nUser Preferences:\n{state['clarification_answers']}"

    research = rag_service.fetch_research(state["user_query"])
    if research["raw_context"]:
        combined += f"\n\nRelevant background research (ground your proposal in this where applicable):\n{research['raw_context']}"

    return {"context": combined, "round": 0, "transcript": []}


def ideator_node(state: DebateState) -> Dict[str, Any]:
    round_num = state["round"] + 1
    if round_num == 1:
        option_a = ideator_agent.opening(state["context"])
    else:
        option_a = ideator_agent.rebuttal(state["context"], format_transcript(state["transcript"]))
    return {"option_a": option_a, "round": round_num}


def critic_node(state: DebateState) -> Dict[str, Any]:
    if state["round"] == 1:
        option_b = critic_agent.opening(state["context"], state["option_a"])
    else:
        option_b = critic_agent.rebuttal(state["context"], format_transcript(state["transcript"]))
    new_transcript = state["transcript"] + [
        {"round": state["round"], "option_a": state["option_a"], "option_b": option_b}
    ]
    return {"option_b": option_b, "transcript": new_transcript}


def convergence_node(state: DebateState) -> Dict[str, Any]:
    verdict = convergence_agent.run(format_transcript(state["transcript"]))
    return {"converged": verdict.converged, "convergence_reasoning": verdict.reasoning}


def route_after_convergence(state: DebateState) -> str:
    if state["converged"] or state["round"] >= MAX_ROUNDS:
        return "extract"
    return "loop"


def extract_node(state: DebateState) -> Dict[str, Any]:
    # Option A / Option B are already the latest-round values in state.
    # Nothing further to compute — this node exists so the graph shape
    # mirrors the diagram's explicit "Extract Option A & Option B" step.
    return {}


def synthesize_node(state: DebateState) -> Dict[str, Any]:
    # LLM3 reads the full transcript and produces one final recommendation.
    synthesis = synthesis_agent.run(state["context"], format_transcript(state["transcript"]))
    return {"synthesis": synthesis}


workflow = StateGraph(DebateState)
workflow.add_node("context_prep", context_prep_node)
workflow.add_node("ideator", ideator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("convergence", convergence_node)
workflow.add_node("extract", extract_node)
workflow.add_node("synthesize", synthesize_node)

workflow.set_entry_point("context_prep")
workflow.add_edge("context_prep", "ideator")
workflow.add_edge("ideator", "critic")
workflow.add_edge("critic", "convergence")
workflow.add_conditional_edges(
    "convergence",
    route_after_convergence,
    {"loop": "ideator", "extract": "extract"},
)
workflow.add_edge("extract", "synthesize")
workflow.add_edge("synthesize", END)

debate_graph = workflow.compile()


def route_query(user_query: str, conversation: str = "") -> RouterDecision:
    """LLM3 triages the new message while considering the current chat."""
    return router_agent.run(user_query, conversation)


def answer_explain(user_query: str, conversation: str = "") -> ExplanationSynthesis:
    """Primary educational path with free evidence, source links, and a plain-text fallback."""
    evidence_text = ""
    sources: list[dict[str, str]] = []
    try:
        evidence = search_web(user_query, count=2)
        evidence_text = evidence.get("context", "")
        sources = evidence.get("sources", [])
    except Exception as evidence_error:
        print(f"Free evidence lookup skipped: {evidence_error}")

    try:
        draft: ExplanationDraft = explanation_writer_agent.run(
            user_query, conversation, evidence_text
        )
        review: ExplanationDraft = explanation_reviewer_agent.run(
            user_query, draft, evidence_text
        )
        result = explanation_synthesis_agent.run(
            user_query, draft, review, evidence_text
        )
        if sources:
            source_lines = "\n\n### Sources\n" + "\n".join(
                f"- [{source['title']}]({source['url']})" for source in sources
            )
            result = ExplanationSynthesis(answer=result.answer + source_lines)
        return result
    except Exception as primary_error:
        # Keep provider details in the terminal log, never in the user-facing answer.
        print(f"Educational quality pipeline fallback: {primary_error}")
        fallback_text = explanation_fallback_agent.run(user_query, conversation)
        return ExplanationSynthesis(answer=fallback_text)


def answer_direct(user_query: str, conversation: str = "") -> str:
    """DIRECT mode remains concise but conversation-aware."""
    result: DirectAnswer = direct_answer_agent.run(user_query, conversation)
    return result.answer


def answer_live(user_query: str, decision: RouterDecision, conversation: str = "") -> LiveResult:
    """LIVE-mode path — retrieve current data, then answer from that data only."""
    if decision.tool == "weather" and not decision.location:
        raise ValueError(
            "Please include a city or location for weather, for example: "
            "'What is today's weather in Mumbai?'"
        )
    live_data = get_live_context(decision.tool, user_query, decision.location)
    return live_answer_agent.run(
        user_query=user_query,
        context=live_data["context"],
        sources=live_data["sources"],
        conversation=conversation,
    )


def generate_clarifying_questions(user_query: str, conversation: str = "") -> List[str]:
    """LLM3 asks only questions that materially change a decision answer."""
    result: ClarificationQuestions = clarification_agent.run(user_query, conversation)
    return result.questions


def run_debate(user_query: str, clarification_answers: str = "", conversation: str = "") -> DebateResult:
    """Steps 3-6 of the flow — the proposal/challenge/convergence loop.
    Call this after the user has answered the clarifying questions."""
    initial_state: DebateState = {
        "user_query": user_query,
        "clarification_answers": clarification_answers,
        "conversation": conversation,
        "context": "",
        "round": 0,
        "transcript": [],
        "option_a": None,
        "option_b": None,
        "converged": False,
        "convergence_reasoning": "",
        "synthesis": None,
    }
    final_state = debate_graph.invoke(initial_state)
    return DebateResult(
        option_a=final_state["option_a"],
        option_b=final_state["option_b"],
        synthesis=final_state["synthesis"],
        rounds_run=final_state["round"],
        converged=final_state["converged"],
    )


if __name__ == "__main__":
    q = "Should I use PostgreSQL or MongoDB for my AI application with 10,000 users?"
    questions = generate_clarifying_questions(q)
    print("Clarifying questions:", questions)
    result = run_debate(q, clarification_answers="Budget: tight. Timeline: 2 weeks.")
    print(f"\nRounds run: {result.rounds_run} | Converged: {result.converged}")
    print("\nOption A:", result.option_a.model_dump_json(indent=2))
    print("\nOption B:", result.option_b.model_dump_json(indent=2))