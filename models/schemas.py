from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    """LLM3's triage decision made before any answer path runs."""

    mode: Literal["DIRECT", "LIVE", "DECISION", "EXPLAIN"]
    reasoning: str
    tool: Literal["none", "weather", "web_search"] = "none"
    location: Optional[str] = None


class DirectAnswer(BaseModel):
    """Answer generated from the model's general knowledge or supplied context."""

    answer: str


class ExplanationDraft(BaseModel):
    """A detailed educational draft or fact-check review."""

    agent_name: str
    answer: str
    key_facts: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)


class ExplanationSynthesis(BaseModel):
    """LLM3's final user-facing educational explanation."""

    answer: str


class Source(BaseModel):
    title: str
    url: str


class LiveResult(BaseModel):
    """A grounded answer plus the sources used to build it."""

    answer: str
    sources: List[Source] = Field(default_factory=list)


class ClarificationQuestions(BaseModel):
    """Output of the LLM3 clarification interview."""

    questions: List[str] = Field(..., min_length=2, max_length=3)


class DualOption(BaseModel):
    """A single proposal from either side of the debate."""

    agent_name: str
    option_title: str
    category_or_type: str
    tagline: str
    key_highlights: List[str]
    vibe_or_takeaway: str


class ConvergenceCheck(BaseModel):
    """LLM3's per-round judgment of whether another debate round is useful."""

    converged: bool
    reasoning: str


class SynthesizedAnswer(BaseModel):
    """LLM3's final answer after judging the LLM1 versus LLM2 debate."""

    final_recommendation: str
    reasoning: str
    key_points: List[str]
    caveats: List[str]


class DebateResult(BaseModel):
    """Final payload handed to the UI."""

    option_a: DualOption
    option_b: DualOption
    synthesis: SynthesizedAnswer
    rounds_run: int
    converged: bool
