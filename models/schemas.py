from pydantic import BaseModel, Field
from typing import List


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


class DebateResult(BaseModel):
    """Final payload handed to the UI: both live options, no winner selected."""
    option_a: DualOption
    option_b: DualOption
    rounds_run: int
    converged: bool
