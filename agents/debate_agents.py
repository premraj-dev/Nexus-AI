from services.ollama_service import ollama_service
from models.schemas import DualOption, OverseerEvaluation, RouterDecision

class RouterAgent:
    """Agent 0: Classifies the user query into DIRECT, EXPERT, DECISION, or CLARIFY."""
    def run(self, query: str) -> RouterDecision:
        system_prompt = (
            "You are the ROUTER for an AI system. Classify the query into strictly ONE mode:\n"
            "- DIRECT: simple factual questions, recipes, definitions, general how-to with one main answer.\n"
            "- EXPERT: coding tasks, debugging, specialist output.\n"
            "- DECISION: queries with real trade-offs between valid competing technical/business/strategic choices.\n"
            "- CLARIFY: queries missing critical constraints (like budget, scale, or preferences).\n"
            "Rules:\n"
            "1. Default to DIRECT.\n"
            "2. 'Best chicken curry recipe' = DIRECT.\n"
            "3. 'Which database to pick' = DECISION."
        )
        return ollama_service.generate_structured(system_prompt, f"Classify this query: {query}", RouterDecision)

class DirectAgent:
    """Handles DIRECT mode queries naturally without agent meta-language."""
    def run(self, query: str) -> str:
        prompt = (
            "You are a helpful assistant. Answer the user query directly and completely.\n"
            "Do NOT use agent labels, taglines, ratings, or Overseer verdicts.\n"
            "Give a clear, direct answer (e.g., full recipe with ingredients and steps)."
        )
        return ollama_service.generate(f"{prompt}\n\nUser query: {query}")

class IdeatorAgent:
    def run(self, context: str) -> DualOption:
        system_prompt = "You are Agent 1. Provide the best primary option with 2-4 points."
        return ollama_service.generate_structured(system_prompt, context, DualOption)

class CriticAgent:
    def run(self, context: str) -> DualOption:
        system_prompt = "You are Agent 2. Provide a strong alternative option with 2-4 points."
        return ollama_service.generate_structured(system_prompt, context, DualOption)

class OverseerAgent:
    def run(self, context: str, option_a: DualOption, option_b: DualOption) -> OverseerEvaluation:
        system_prompt = (
            "You are the Overseer AI. Pick ONE best option and explain why in 1 simple sentence. "
            "Never use internal jargon."
        )
        eval_context = f"Context:\n{context}\n\nOpt A:\n{option_a.model_dump_json()}\n\nOpt B:\n{option_b.model_dump_json()}"
        return ollama_service.generate_structured(system_prompt, eval_context, OverseerEvaluation)

router_agent = RouterAgent()
direct_agent = DirectAgent()
ideator_agent = IdeatorAgent()
critic_agent = CriticAgent()
overseer_agent = OverseerAgent()
