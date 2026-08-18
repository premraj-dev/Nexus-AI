import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import ExplanationDraft, ExplanationSynthesis, RouterDecision
from services.live_data_service import WEATHER_CODES


def test_explain_route_contract() -> None:
    decision = RouterDecision(mode="EXPLAIN", reasoning="Broad educational request")
    assert decision.tool == "none"


def test_explanation_contracts() -> None:
    draft = ExplanationDraft(
        agent_name="Reviewer",
        answer="A clear explanation.",
        key_facts=["Fact"],
        examples=["Example"],
        caveats=["Caveat"],
    )
    final = ExplanationSynthesis(answer=draft.answer)
    assert final.answer == "A clear explanation."


def test_weather_codes_are_grounded() -> None:
    assert WEATHER_CODES[0] == "clear sky"
    assert WEATHER_CODES[95] == "thunderstorm"


if __name__ == "__main__":
    test_explain_route_contract()
    test_explanation_contracts()
    test_weather_codes_are_grounded()
    print("Quality-contract tests passed.")
