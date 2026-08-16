from services.ollama_service import ollama_service
from models.schemas import (
    DualOption, ConvergenceCheck, ClarificationQuestions, SynthesizedAnswer,
    RouterDecision, DirectAnswer,
)
from prompts.agent_prompts import (
    ROUTER_SYSTEM_PROMPT,
    DIRECT_ANSWER_SYSTEM_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
    IDEATOR_OPENING_PROMPT,
    IDEATOR_REBUTTAL_PROMPT,
    CRITIC_OPENING_PROMPT,
    CRITIC_REBUTTAL_PROMPT,
    CONVERGENCE_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
)


class RouterAgent:
    """LLM3 — triages every incoming query before anything else runs."""

    def run(self, user_query: str) -> RouterDecision:
        return ollama_service.generate_structured(
            ROUTER_SYSTEM_PROMPT, f"User query: {user_query}", RouterDecision
        )


class DirectAnswerAgent:
    """Single-call plain answer for DIRECT-mode queries. No debate involved."""

    def run(self, user_query: str) -> DirectAnswer:
        return ollama_service.generate_structured(
            DIRECT_ANSWER_SYSTEM_PROMPT, f"User query: {user_query}", DirectAnswer
        )


class ClarificationAgent:
    """LLM3 — runs the clarification interview. Every query goes through this first,
    no router/mode split anymore."""

    def run(self, user_query: str) -> ClarificationQuestions:
        return ollama_service.generate_structured(
            CLARIFICATION_SYSTEM_PROMPT, f"User query: {user_query}", ClarificationQuestions
        )


class IdeatorAgent:
    """LLM1 — proposes and defends Option A across debate rounds."""

    def opening(self, context: str) -> DualOption:
        return ollama_service.generate_structured(IDEATOR_OPENING_PROMPT, context, DualOption)

    def rebuttal(self, context: str, transcript_so_far: str) -> DualOption:
        prompt = f"{context}\n\nDebate transcript so far:\n{transcript_so_far}"
        return ollama_service.generate_structured(IDEATOR_REBUTTAL_PROMPT, prompt, DualOption)


class CriticAgent:
    """LLM2 — challenges Option A and proposes/defends Option B."""

    def opening(self, context: str, option_a: DualOption) -> DualOption:
        prompt = f"{context}\n\nOption A proposed by LLM1:\n{option_a.model_dump_json()}"
        return ollama_service.generate_structured(CRITIC_OPENING_PROMPT, prompt, DualOption)

    def rebuttal(self, context: str, transcript_so_far: str) -> DualOption:
        prompt = f"{context}\n\nDebate transcript so far:\n{transcript_so_far}"
        return ollama_service.generate_structured(CRITIC_REBUTTAL_PROMPT, prompt, DualOption)


class ConvergenceAgent:
    """LLM3 — judges per-round whether the debate has converged.
    Never picks a winner; that's the human user's call, made in the UI."""

    def run(self, transcript_so_far: str) -> ConvergenceCheck:
        return ollama_service.generate_structured(
            CONVERGENCE_SYSTEM_PROMPT, f"Debate transcript:\n{transcript_so_far}", ConvergenceCheck
        )


class SynthesisAgent:
    """LLM3 — after the debate ends, synthesizes one final answer from the full transcript."""

    def run(self, context: str, transcript_so_far: str) -> SynthesizedAnswer:
        prompt = f"{context}\n\nFull debate transcript:\n{transcript_so_far}"
        return ollama_service.generate_structured(SYNTHESIS_SYSTEM_PROMPT, prompt, SynthesizedAnswer)


clarification_agent = ClarificationAgent()
ideator_agent = IdeatorAgent()
critic_agent = CriticAgent()
convergence_agent = ConvergenceAgent()
synthesis_agent = SynthesisAgent()
router_agent = RouterAgent()
direct_answer_agent = DirectAnswerAgent()