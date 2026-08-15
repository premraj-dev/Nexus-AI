from typing import List

class LightweightRAGService:
    def __init__(self):
        self.documents: List[str] = []

    def initialize_with_docs(self, texts: List[str]):
        """Indexes raw text snippets into local memory."""
        self.documents = texts

    def retrieve_context(self, query: str, k: int = 2) -> str:
        """Simple keyword matching retrieval (zero dependencies required)."""
        if not self.documents:
            return ""
            
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in self.documents:
            doc_words = set(doc.lower().split())
            score = len(query_words.intersection(doc_words))
            scored_docs.append((score, doc))
            
        # Sort by match score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = [doc for score, doc in scored_docs[:k]]
        return "\n".join([f"- {doc}" for doc in top_docs])

rag_service = LightweightRAGService()
