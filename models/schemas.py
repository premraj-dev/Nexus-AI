from pydantic import BaseModel
from typing import List, Optional, Literal

class RouterDecision(BaseModel):
    mode: Literal["DIRECT", "EXPERT", "DECISION", "CLARIFY"]
    reason: str

class ClarificationQuestions(BaseModel):
    questions: List[str]

class DualOption(BaseModel):
    agent_name: str
    option_title: str
    category_or_type: str
    tagline: str
    key_highlights: List[str]
    vibe_or_takeaway: str

class OverseerEvaluation(BaseModel):
    winning_option: str
    winner_title: str
    category_or_type: str
    tagline: str
    key_highlights: List[str]
    winning_verdict: str
    why_preferred_over_alternative: str

class FinalSingleChoice(BaseModel):
    best_option: OverseerEvaluation
    alternative_option: DualOption
