"""Minimal retrieval over the local knowledge base.

This is a deliberately dependency-free BM25-lite scorer, not a vector DB -
the corpus is a handful of markdown files, so an embedding index would add
a dependency without adding retrieval quality. The interface
(`retrieve(query, k)`) is the actual contract other code depends on, so
swapping this for a real vector store (Milvus, pgvector, ...) later is a
one-file change with no callers to touch.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from travel_agent.config import DATA_DIR

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class Chunk:
    source: str
    text: str
    tokens: list[str]


class KnowledgeBase:
    def __init__(self, kb_dir: Path | None = None):
        kb_dir = kb_dir or (DATA_DIR / "knowledge_base")
        self.chunks: list[Chunk] = []
        for path in sorted(kb_dir.glob("*.md")):
            for para in path.read_text().split("\n\n"):
                para = para.strip()
                if not para:
                    continue
                self.chunks.append(Chunk(source=path.name, text=para, tokens=_tokenize(para)))
        self._doc_freq: dict[str, int] = {}
        for chunk in self.chunks:
            for term in set(chunk.tokens):
                self._doc_freq[term] = self._doc_freq.get(term, 0) + 1

    def _score(self, query_tokens: list[str], chunk: Chunk) -> float:
        if not chunk.tokens:
            return 0.0
        term_freq: dict[str, int] = {}
        for t in chunk.tokens:
            term_freq[t] = term_freq.get(t, 0) + 1
        score = 0.0
        n_docs = max(len(self.chunks), 1)
        for term in query_tokens:
            tf = term_freq.get(term, 0)
            if tf == 0:
                continue
            df = self._doc_freq.get(term, 0)
            idf = math.log((n_docs + 1) / (df + 1)) + 1
            score += (tf / len(chunk.tokens)) * idf
        return score

    def retrieve(self, query: str, k: int = 3) -> list[Chunk]:
        query_tokens = _tokenize(query)
        scored = [(self._score(query_tokens, c), c) for c in self.chunks]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [c for score, c in scored[:k] if score > 0]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def retrieve_context(query: str, k: int = 3) -> str:
    chunks = get_knowledge_base().retrieve(query, k=k)
    if not chunks:
        return "(no relevant context found)"
    return "\n\n".join(f"[{c.source}] {c.text}" for c in chunks)
