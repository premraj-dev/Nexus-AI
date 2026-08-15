from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from agents.debate_agents import router_agent, direct_agent, ideator_agent, critic_agent, overseer_agent
from models.schemas import DualOption, OverseerEvaluation, FinalSingleChoice, ClarificationQuestions, RouterDecision
from services.ollama_service import ollama_service

class DebateState(TypedDict):
    user_query: str
    clarification_answers: Optional[str]
    context: str
    mode: Optional[str]
    direct_response: Optional[str]
    ideator_proposal: Optional[DualOption]
    critic_proposal: Optional[DualOption]
    final_choice: Optional[FinalSingleChoice]

def router_node(state: DebateState) -> Dict[str, Any]:
    res: RouterDecision = router_agent.run(state["user_query"])
    return {"mode": res.mode}

def direct_node(state: DebateState) -> Dict[str, Any]:
    response = direct_agent.run(state["user_query"])
    return {"direct_response": response}

def context_prep_node(state: DebateState) -> Dict[str, Any]:
    combined_query = f"User Request: {state['user_query']}"
    if state.get("clarification_answers"):
        combined_query += f"\nUser Preferences:\n{state['clarification_answers']}"
    return {"context": combined_query}

def ideator_node(state: DebateState) -> Dict[str, Any]:
    proposal = ideator_agent.run(state["context"])
    return {"ideator_proposal": proposal}

def critic_node(state: DebateState) -> Dict[str, Any]:
    context_with_ideator = f"{state['context']}\n\nOption A Choice: {state['ideator_proposal'].option_title}"
    proposal = critic_agent.run(context_with_ideator)
    return {"critic_proposal": proposal}

def overseer_node(state: DebateState) -> Dict[str, Any]:
    evaluation = overseer_agent.run(
        state["context"], 
        state["ideator_proposal"], 
        state["critic_proposal"]
    )
    alt = state["critic_proposal"] if "Option A" in evaluation.winning_option else state["ideator_proposal"]
    return {"final_choice": FinalSingleChoice(best_option=evaluation, alternative_option=alt)}

def route_decision(state: DebateState) -> str:
    mode = state.get("mode", "DIRECT")
    if mode == "DIRECT":
        return "direct"
    elif mode == "CLARIFY":
        return "context_prep"
    else:
        return "context_prep"

def generate_clarifications(user_query: str) -> List[str]:
    prompt = "Generate 3 short clarifying questions for user preferences."
    res = ollama_service.generate_structured(prompt, user_query, ClarificationQuestions)
    return res.questions

# Build Conditional Graph
workflow = StateGraph(DebateState)

workflow.add_node("router", router_node)
workflow.add_node("direct", direct_node)
workflow.add_node("context_prep", context_prep_node)
workflow.add_node("ideator", ideator_node)
workflow.add_node("critic", critic_node)
workflow.add_node("overseer", overseer_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "direct": "direct",
        "context_prep": "context_prep"
    }
)

workflow.add_edge("direct", END)
workflow.add_edge("context_prep", "ideator")
workflow.add_edge("ideator", "critic")
workflow.add_edge("critic", "overseer")
workflow.add_edge("overseer", END)

app_graph = workflow.compile()
