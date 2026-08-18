from services.ollama_service import ollama_service
from models.schemas import (
    DualOption, ConvergenceCheck, ClarificationQuestions, SynthesizedAnswer,
    RouterDecision, DirectAnswer, LiveResult, ExplanationDraft, ExplanationSynthesis,
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
    LIVE_ANSWER_SYSTEM_PROMPT,
    EXPLAIN_WRITER_SYSTEM_PROMPT,
    EXPLAIN_REVIEWER_SYSTEM_PROMPT,
    EXPLAIN_SYNTHESIS_SYSTEM_PROMPT,
    EXPLAIN_FALLBACK_SYSTEM_PROMPT,
)


class LiveAnswerAgent:
    """LLM3 — turns retrieved live data into a grounded user-facing answer."""

    def run(self, user_query: str, context: str, sources: list[dict], conversation: str = "") -> LiveResult:
        source_text = "\n".join(
            f"- {source.get('title', 'Source')}: {source.get('url', '')}"
            for source in sources
        )
        conversation_part = f"Conversation so far:\n{conversation}\n\n" if conversation else ""
        prompt = (
            f"{conversation_part}"
            f"User query: {user_query}\n\n"
            f"Retrieved live data:\n{context}\n\n"
            f"Available source records:\n{source_text}"
        )
        return ollama_service.generate_structured(
            LIVE_ANSWER_SYSTEM_PROMPT, prompt, LiveResult
        )


class ExplanationWriterAgent:
    """Internal first pass for broad educational questions."""

    def run(self, user_query: str, conversation: str = "", evidence: str = "") -> ExplanationDraft:
        conversation_part = f"Conversation so far:\n{conversation}\n\n" if conversation else ""
        evidence_part = f"Free public evidence:\n{evidence}\n\n" if evidence else ""
        prompt = f"{conversation_part}{evidence_part}User question: {user_query}"
        return ollama_service.generate_structured(
            EXPLAIN_WRITER_SYSTEM_PROMPT, prompt, ExplanationDraft
        )


class ExplanationReviewerAgent:
    """Internal fact-checking and improvement pass."""

    def run(self, user_query: str, draft: ExplanationDraft, evidence: str = "") -> ExplanationDraft:
        evidence_part = f"Free public evidence:\n{evidence}\n\n" if evidence else ""
        prompt = (
            f"{evidence_part}User question: {user_query}\n\n"
            f"Writer draft:\n{draft.model_dump_json()}"
        )
        return ollama_service.generate_structured(
            EXPLAIN_REVIEWER_SYSTEM_PROMPT, prompt, ExplanationDraft
        )


class ExplanationSynthesisAgent:
    """LLM3 supervisor that produces only the final educational answer."""

    def run(self, user_query: str, draft: ExplanationDraft, review: ExplanationDraft, evidence: str = "") -> ExplanationSynthesis:
        evidence_part = f"Free public evidence:\n{evidence}\n\n" if evidence else ""
        prompt = (
            f"{evidence_part}User question: {user_query}\n\n"
            f"Writer draft:\n{draft.model_dump_json()}\n\n"
            f"Reviewer draft:\n{review.model_dump_json()}"
        )
        return ollama_service.generate_structured(
            EXPLAIN_SYNTHESIS_SYSTEM_PROMPT, prompt, ExplanationSynthesis
        )


class ExplanationFallbackAgent:
    """Plain-text fallback used only when structured explanation calls fail."""

    def run(self, user_query: str, conversation: str = "") -> str:
        conversation_part = f"Conversation so far:\n{conversation}\n\n" if conversation else ""
        return ollama_service.generate_text(
            EXPLAIN_FALLBACK_SYSTEM_PROMPT,
            f"{conversation_part}User question: {user_query}",
            max_tokens=1200,
        )


class RouterAgent:
    """LLM3 — triages every incoming query before anything else runs."""

    def run(self, user_query: str, conversation: str = "") -> RouterDecision:
        prompt = f"Conversation so far:\n{conversation}\n\nNew user message: {user_query}" if conversation else f"User query: {user_query}"
        return ollama_service.generate_structured(ROUTER_SYSTEM_PROMPT, prompt, RouterDecision)


class DirectAnswerAgent:
    """Single-call plain answer for DIRECT-mode queries. No debate involved."""

    def run(self, user_query: str, conversation: str = "") -> DirectAnswer:
        prompt = f"Conversation so far:\n{conversation}\n\nNew user message: {user_query}" if conversation else f"User query: {user_query}"
        return ollama_service.generate_structured(DIRECT_ANSWER_SYSTEM_PROMPT, prompt, DirectAnswer)


class ClarificationAgent:
    """LLM3 — runs the clarification interview. Every query goes through this first,
    no router/mode split anymore."""

    def run(self, user_query: str, conversation: str = "") -> ClarificationQuestions:
        prompt = f"Conversation so far:\n{conversation}\n\nNew user message: {user_query}" if conversation else f"User query: {user_query}"
        return ollama_service.generate_structured(CLARIFICATION_SYSTEM_PROMPT, prompt, ClarificationQuestions)


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
live_answer_agent = LiveAnswerAgent()
explanation_writer_agent = ExplanationWriterAgent()
explanation_reviewer_agent = ExplanationReviewerAgent()
explanation_synthesis_agent = ExplanationSynthesisAgent()
explanation_fallback_agent = ExplanationFallbackAgent()