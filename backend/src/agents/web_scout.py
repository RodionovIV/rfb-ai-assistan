from __future__ import annotations

import os
from datetime import datetime
from typing import Iterable, List

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.api.projects import WebFinding, WebScoutOutput


class WebScoutAgent(Agent):
    name = "web_scout"

    def __init__(
        self,
        provider_name: str = "duckduckgo",
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
        use_real_search: bool = True,
    ) -> None:
        self.provider_name = provider_name
        self.use_llm = use_llm
        self.use_real_search = use_real_search and DDGS_AVAILABLE

        # Инициализируем LangGraph агента для обработки результатов поиска
        if self.use_llm:
            try:
                self.llm_agent = LangGraphAgent(
                    model_name=model_name,
                    api_key=api_key or os.getenv("OPENAI_API_KEY"),
                    system_prompt=(
                        "Вы опытный веб-исследователь и информационный аналитик. "
                        "Анализируйте результаты поиска в интернете и создавайте информативные summary "
                        "с ключевыми выводами. Будьте точны и предоставляйте полезную информацию."
                    ),
                )
            except ValueError:
                # Если API ключ не указан, отключаем LLM
                self.use_llm = False
                self.llm_agent = None
        else:
            self.llm_agent = None

    def run(self, *, queries: Iterable[str]) -> dict:
        findings: List[WebFinding] = []
        
        for query in queries:
            if self.use_real_search:
                # Выполняем реальный поиск в интернете
                search_results = self._perform_web_search(query)
                if search_results:
                    # Обрабатываем результаты поиска
                    for result in search_results[:3]:  # Берем топ-3 результата
                        finding = self._process_search_result(result, query)
                        if finding:
                            findings.append(finding)
                else:
                    # Если поиск не дал результатов, используем fallback
                    finding = self._generate_finding_fallback(query, datetime.utcnow().isoformat())
                    findings.append(finding)
            else:
                # Используем старый метод (заглушка)
                timestamp = datetime.utcnow().isoformat()
                if self.use_llm and self.llm_agent:
                    finding = self._generate_finding_with_llm(query, timestamp)
                else:
                    finding = self._generate_finding_fallback(query, timestamp)
                findings.append(finding)
        
        return WebScoutOutput(findings=findings).model_dump()

    def _perform_web_search(self, query: str, max_results: int = 5) -> List[dict]:
        """Выполняет реальный поиск в интернете используя DuckDuckGo."""
        if not DDGS_AVAILABLE:
            return []
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as e:
            print(f"Ошибка при поиске в интернете: {e}")
            return []

    def _process_search_result(self, result: dict, query: str) -> WebFinding | None:
        """Обрабатывает результат поиска и создает WebFinding."""
        try:
            title = result.get("title", f"{query.title()} overview")
            url = result.get("href", f"https://search.example.com/{query.replace(' ', '-')}")
            body = result.get("body", "")
            
            # Если есть LLM, используем его для создания summary
            if self.use_llm and self.llm_agent and body:
                snippet = self._create_summary_with_llm(query, body)
            else:
                snippet = body[:300] if body else f"Результат поиска для '{query}'"
            
            return WebFinding(
                title=title[:100],
                url=url,
                snippet=snippet,
            )
        except Exception as e:
            print(f"Ошибка при обработке результата поиска: {e}")
            return None

    def _create_summary_with_llm(self, query: str, content: str) -> str:
        """Создает краткое summary используя LLM."""
        if not self.llm_agent:
            return content[:300]
        
        prompt = (
            f"Создай краткое summary (2-3 предложения) на основе следующего контента "
            f"для запроса '{query}':\n\n{content[:1000]}"
        )
        
        try:
            result = self.llm_agent.run(query=prompt)
            return result.get("response", content[:300])
        except Exception:
            return content[:300]

    def _generate_finding_with_llm(self, query: str, timestamp: str) -> WebFinding:
        """Генерирует finding используя LLM."""
        prompt = (
            f"Сгенерируй результаты веб-исследования для данного запроса: '{query}'. "
            "Обеспечь:\n"
            "1. Описательный заголовок (максимум 100 символов)\n"
            "2. Соответствующий формат URL (используйте example.com домен)\n"
            "3. Краткий фрагмент (2-3 предложения) с ключевой информацией по данной теме\n\n"
            "Отформатируйте свой ответ следующим образом:\n"
            "Заголовок: [title]\n"
            "URL: [url]\n"
            "Snippet: [snippet]"
        )

        try:
            result = self.llm_agent.run(query=prompt)
            response = result.get("response", "")
            
            # Парсим ответ LLM
            title = f"{query.title()} overview"
            url = f"https://search.example.com/{query.replace(' ', '-')}"
            snippet = f"Automated discovery for '{query}' generated by {self.provider_name} at {timestamp}."

            lines = response.split("\n")
            for line in lines:
                line = line.strip()
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip()[:100]
                elif line.lower().startswith("url:"):
                    url = line.split(":", 1)[1].strip()
                elif line.lower().startswith("snippet:"):
                    snippet = line.split(":", 1)[1].strip()

            return WebFinding(
                title=title,
                url=url,
                snippet=snippet,
            )
        except Exception:
            # В случае ошибки используем fallback
            return self._generate_finding_fallback(query, timestamp)

    @staticmethod
    def _generate_finding_fallback(query: str, timestamp: str) -> WebFinding:
        """Простой метод генерации finding без LLM."""
        return WebFinding(
            title=f"{query.title()} overview",
            url=f"https://search.example.com/{query.replace(' ', '-')}",
            snippet=(
                f"Automated discovery for '{query}' generated by knowledge-graph at {timestamp}."
            ),
        )

