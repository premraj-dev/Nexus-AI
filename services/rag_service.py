import json
import datetime
from duckduckgo_search import DDGS
from llm_client import call_local_llm

class RAGService:
    def fetch_research(self, query: str) -> dict:
        current_date = datetime.date.today().strftime('%Y-%m-%d')
        
        # Mandatory query enrichment for 2026 temporal queries
        search_query = f"Bollywood movies released in 2026 release date box office {query}"
        raw_snippets = ""
        
        try:
            with DDGS(timeout=5) as ddgs:
                results = list(ddgs.text(search_query, max_results=6))
                for r in results:
                    raw_snippets += f"- Title: {r.get('title','')}\n  Snippet: {r.get('body','')}\n\n"
        except Exception as e:
            raw_snippets = f"Search failed: {str(e)}"

        # Extraction Agent: Convert raw text into strictly validated JSON
        extraction_system_prompt = (
            f"You are a Strict Data Extraction Agent. Today's date is {current_date}.\n"
            "Extract movies mentioned in the text that strictly belong to the year 2026.\n"
            "Rules:\n"
            "1. Extract ONLY movies released or scheduled for release in 2026.\n"
            "2. Reject any movie released before 2026 (e.g., Pathaan, Tiger 3, Laal Singh Chaddha).\n"
            "3. Separate into 'released_2026' and 'upcoming_2026'.\n"
            "Return STRICT JSON only:\n"
            "{\n"
            '  "released_2026": [{"title": "", "release_date": "", "verdict": ""}],\n'
            '  "upcoming_2026": [{"title": "", "release_date": "", "status": ""}],\n'
            '  "verification_status": "SUCCESS" or "FAILED"\n'
            "}"
        )
        
        extracted_json = call_local_llm(f"RAW SEARCH DATA:\n{raw_snippets}", extraction_system_prompt)
        
        return {
            "raw_context": raw_snippets,
            "structured_data": extracted_json
        }

rag_service = RAGService()
