from __future__ import annotations

import os
from typing import Iterable, List

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.agents.vector_store import BaseVectorStore, VectorDocument, create_vector_store
from src.api.projects import MarketInsight, MarketMapperOutput


class MarketMapperAgent(Agent):
    name = "market_mapper"

    def __init__(
        self,
        knowledge_base: Iterable[VectorDocument] | None = None,
        vector_store: BaseVectorStore | None = None,
        top_k: int = 5,
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
    ) -> None:
        self.vector_store = vector_store or create_vector_store()
        self.top_k = top_k
        self.use_llm = use_llm
        self.knowledge_base: List[VectorDocument] = list(knowledge_base or [])
        if self.knowledge_base:
            self.vector_store.add_texts(self.knowledge_base)

        # Инициализируем LangGraph агента для генерации summary
        if self.use_llm:
            try:
                self.llm_agent = LangGraphAgent(
                    model_name=model_name,
                    api_key=api_key or os.getenv("OPENAI_API_KEY"),
                    system_prompt=(
                        "You are an expert market analyst. Analyze the provided documents "
                        "and create a concise, insightful summary about the market topic. "
                        "Focus on key insights, trends, and important information."
                    ),
                )
            except ValueError:
                # Если API ключ не указан, отключаем LLM
                self.use_llm = False
                self.llm_agent = None
        else:
            self.llm_agent = None

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

    def _compose_summary(self, query: str, documents: Iterable[VectorDocument]) -> str:
        """Создает summary используя LLM агента или простой метод."""
        if self.use_llm and self.llm_agent:
            # Формируем контекст из найденных документов
            context_text = "\n\n".join(
                [f"Document {i+1}:\n{doc.text}" for i, doc in enumerate(documents)]
            )
            
            prompt = (
                f"Analyze the following documents related to '{query}' and provide "
                f"a concise summary with key insights:\n\n{context_text}"
            )
            
            try:
                result = self.llm_agent.run(query=prompt)
                return result.get("response", self._fallback_summary(query, documents))
            except Exception:
                # В случае ошибки используем fallback
                return self._fallback_summary(query, documents)
        else:
            return self._fallback_summary(query, documents)

    @staticmethod
    def _fallback_summary(query: str, documents: Iterable[VectorDocument]) -> str:
        """Простой метод создания summary без LLM."""
        snippets = [document.text[:200] for document in documents]
        unique_snippets = []
        for snippet in snippets:
            if snippet not in unique_snippets:
                unique_snippets.append(snippet)
        return f"Insights for '{query}': " + " | ".join(unique_snippets)

