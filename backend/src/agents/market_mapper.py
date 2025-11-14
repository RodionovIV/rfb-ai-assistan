from __future__ import annotations

from typing import Iterable, List

from src.agents.base import Agent
from src.agents.vector_store import BaseVectorStore, VectorDocument, create_vector_store
from src.api.projects import MarketInsight, MarketMapperOutput


class MarketMapperAgent(Agent):
    name = "market_mapper"

    def __init__(
        self,
        knowledge_base: Iterable[VectorDocument] | None = None,
        vector_store: BaseVectorStore | None = None,
        top_k: int = 5,
    ) -> None:
        self.vector_store = vector_store or create_vector_store()
        self.top_k = top_k
        self.knowledge_base: List[VectorDocument] = list(knowledge_base or [])
        if self.knowledge_base:
            self.vector_store.add_texts(self.knowledge_base)

    def add_documents(self, documents: Iterable[VectorDocument]) -> None:
        docs = list(documents)
        if not docs:
            return
        self.knowledge_base.extend(docs)
        self.vector_store.add_texts(docs)

    def run(self, *, queries: Iterable[str]) -> dict:
        insights: List[MarketInsight] = []
        for query in queries:
            results = self.vector_store.similarity_search(query=query, k=self.top_k)
            if not results:
                continue
            summary = self._compose_summary(query, results)
            insights.append(
                MarketInsight(
                    topic=query,
                    summary=summary,
                    sources=[doc.metadata.get("source", "knowledge-base") for doc in results],
                )
            )
        return MarketMapperOutput(insights=insights).model_dump()

    @staticmethod
    def _compose_summary(query: str, documents: Iterable[VectorDocument]) -> str:
        snippets = [document.text[:200] for document in documents]
        unique_snippets = []
        for snippet in snippets:
            if snippet not in unique_snippets:
                unique_snippets.append(snippet)
        return f"Insights for '{query}': " + " | ".join(unique_snippets)

