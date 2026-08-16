"""
Nexus AI RAG service.

Retrieves relevant passages from a local knowledge base (plain .md/.txt files
in the knowledge/ folder) and grounds the LLM1/LLM2 debate in real facts
instead of only model priors.

Swap in your own dataset by dropping more .md/.txt files into knowledge/ —
no code changes needed. Each file is chunked on blank-line/heading boundaries;
retrieval is pure keyword overlap (no embeddings, no external API, no cost).
This is intentionally simple and dependency-free so it's easy to explain and
defend in an interview: swap this function body for a vector store later
without touching the rest of the pipeline.
"""

import re
from pathlib import Path
from dataclasses import dataclass

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "but", "for",
    "of", "to", "in", "on", "with", "vs", "versus", "should", "i", "my", "me",
    "what", "which", "how", "do", "does", "it", "this", "that", "be", "as",
    "best", "good", "better", "use", "using", "need", "want", "app", "project",
}


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]*", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _load_chunks() -> list[Chunk]:
    chunks = []
    if not KNOWLEDGE_DIR.exists():
        return chunks
    for path in KNOWLEDGE_DIR.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        sections = re.split(r"\n---\n|\n(?=# )", content)
        for section in sections:
            section = section.strip()
            if not section:
                continue
            heading_match = re.match(r"^#+\s*(.+)", section)
            heading = heading_match.group(1).strip() if heading_match else path.stem
            chunks.append(Chunk(source=path.name, heading=heading, text=section))
    for path in KNOWLEDGE_DIR.glob("*.txt"):
        content = path.read_text(encoding="utf-8")
        for para in content.split("\n\n"):
            para = para.strip()
            if para:
                chunks.append(Chunk(source=path.name, heading=path.stem, text=para))
    return chunks


class RAGService:
    def __init__(self):
        self._chunks = _load_chunks()

    def reload(self) -> None:
        """Call after adding/editing files in knowledge/ without restarting the app."""
        self._chunks = _load_chunks()

    def fetch_research(self, query: str, top_k: int = 3) -> dict:
        """Returns the top_k most relevant knowledge chunks for the query,
        scored by keyword overlap. Returns empty context if nothing scores > 0
        (e.g. the query is outside the knowledge base's topics) — the debate
        agents fall back to model priors in that case."""
        if not self._chunks:
            return {"raw_context": "", "sources": []}

        query_tokens = _tokenize(query)
        scored = []
        for chunk in self._chunks:
            chunk_tokens = _tokenize(chunk.heading + " " + chunk.text)
            overlap = len(query_tokens & chunk_tokens)
            if overlap >= 2:  # single coincidental word match isn't enough signal
                scored.append((overlap, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [c for _, c in scored[:top_k]]

        raw_context = "\n\n".join(f"[Source: {c.source} — {c.heading}]\n{c.text}" for c in top)
        return {"raw_context": raw_context, "sources": [c.source for c in top]}


rag_service = RAGService()