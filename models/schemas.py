from pydantic import BaseModel, Field
from typing import List, Literal


class RouterDecision(BaseModel):
    """LLM3's triage call, made before anything else runs."""
    mode: Literal["DIRECT", "DECISION"]
    reasoning: str


class DirectAnswer(BaseModel):
    """Plain answer for simple factual/informational queries — no debate needed."""
    answer: str


class ClarificationQuestions(BaseModel):
    """Output of the LLM3 clarification interview — always 2-3 questions, every query."""
    questions: List[str] = Field(..., min_length=2, max_length=3)


class DualOption(BaseModel):
    """A single proposal (either Option A from the Ideator or Option B from the Critic).
    Same shape is reused for opening proposals and rebuttals across debate rounds."""
    agent_name: str
    option_title: str
    category_or_type: str
    tagline: str
    key_highlights: List[str]
    vibe_or_takeaway: str


class ConvergenceCheck(BaseModel):
    """LLM3's per-round judgment. It ONLY decides whether to keep debating —
    it never picks a winner. Picking is the human user's job."""
    converged: bool
    reasoning: str


class SynthesizedAnswer(BaseModel):
    """LLM3's final answer after judging the LLM1 vs LLM2 debate.
    A single authoritative recommendation, not a menu of options."""
    final_recommendation: str
    reasoning: str
    key_points: List[str]
    caveats: List[str]


class DebateResult(BaseModel):
    """Final payload handed to the UI: the synthesized answer, plus the
    raw debate positions for transparency/telemetry."""
    option_a: DualOption
    option_b: DualOption
    synthesis: SynthesizedAnswer
    rounds_run: int
    converged: bool