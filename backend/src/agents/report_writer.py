from __future__ import annotations

import os
from typing import Iterable

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.api.projects import (
    MarketMapperOutput,
    PitchParserOutput,
    ReportRecommendation,
    ReportWriterOutput,
    WebScoutOutput,
)


class ReportWriterAgent(Agent):
    name = "report_writer"

    def __init__(
        self,
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
    ) -> None:
        self.use_llm = use_llm

        # Инициализируем LangGraph агента для генерации отчетов
        if self.use_llm:
            try:
                self.llm_agent = LangGraphAgent(
                    model_name=model_name,
                    api_key=api_key or os.getenv("OPENAI_API_KEY"),
                    system_prompt=(
                        "You are an expert business analyst and report writer. "
                        "Create comprehensive, well-structured executive summaries and recommendations "
                        "based on pitch deck analysis, market research, and web findings. "
                        "Be concise, insightful, and actionable."
                    ),
                )
            except ValueError:
                # Если API ключ не указан, отключаем LLM
                self.use_llm = False
                self.llm_agent = None
        else:
            self.llm_agent = None

    def run(
        self,
        *,
        project_id: str,
        pitch: PitchParserOutput,
        market: MarketMapperOutput,
        web: WebScoutOutput,
    ) -> dict:
        recommendations = self._build_recommendations(market, pitch, web)
        appendix = {
            "pitch_sections": [section.model_dump() for section in pitch.sections],
            "market_insights": [insight.model_dump() for insight in market.insights],
            "web_findings": [finding.model_dump() for finding in web.findings],
        }
        output = ReportWriterOutput(
            title=f"Project {project_id} research report",
            executive_summary=self._compose_summary(pitch=pitch, market=market, web=web),
            recommendations=recommendations,
            appendix=appendix,
        )
        return output.model_dump()

    def _compose_summary(
        self, *, pitch: PitchParserOutput, market: MarketMapperOutput, web: WebScoutOutput
    ) -> str:
        """Создает executive summary используя LLM или простой метод."""
        if self.use_llm and self.llm_agent:
            # Формируем контекст для LLM
            pitch_info = "\n".join(
                [f"- {section.name}: {section.summary[:200]}" for section in pitch.sections]
            ) or "No pitch sections identified"

            market_info = "\n".join(
                [f"- {insight.topic}: {insight.summary[:200]}" for insight in market.insights]
            ) or "No market insights"

            web_info = "\n".join(
                [f"- {finding.title}: {finding.snippet[:200]}" for finding in web.findings]
            ) or "No web findings"

            prompt = (
                "Create a comprehensive executive summary (2-3 paragraphs) for a business research report "
                "based on the following information:\n\n"
                f"Pitch Deck Sections:\n{pitch_info}\n\n"
                f"Market Insights:\n{market_info}\n\n"
                f"Web Findings:\n{web_info}\n\n"
                "Provide a clear, concise summary that highlights key findings and insights."
            )

            try:
                result = self.llm_agent.run(query=prompt)
                return result.get("response", self._fallback_summary(pitch, market, web))
            except Exception:
                return self._fallback_summary(pitch, market, web)
        else:
            return self._fallback_summary(pitch, market, web)

    @staticmethod
    def _fallback_summary(
        pitch: PitchParserOutput, market: MarketMapperOutput, web: WebScoutOutput
    ) -> str:
        """Простой метод создания summary без LLM."""
        pitch_sections = ", ".join(section.name for section in pitch.sections) or "No sections identified"
        market_topics = ", ".join(insight.topic for insight in market.insights) or "No market insights"
        web_sources = ", ".join(finding.title for finding in web.findings) or "No web findings"
        return (
            "The pitch deck analysis covered the following sections: "
            f"{pitch_sections}. Market research highlighted {market_topics}. Web scouting captured "
            f"signals from: {web_sources}."
        )

    def _build_recommendations(
        self,
        market: MarketMapperOutput,
        pitch: PitchParserOutput,
        web: WebScoutOutput,
    ) -> Iterable[ReportRecommendation]:
        """Создает рекомендации используя LLM или простой метод."""
        if not market.insights:
            return []

        if self.use_llm and self.llm_agent:
            # Используем LLM для генерации более качественных рекомендаций
            market_topics = ", ".join(insight.topic for insight in market.insights)
            prompt = (
                f"Based on market research topics: {market_topics}, "
                "generate 3-5 actionable recommendations for further research or analysis. "
                "For each recommendation, provide a title and a brief rationale (1-2 sentences). "
                "Format: Title: [title]\nRationale: [rationale]\n\n"
            )

            try:
                result = self.llm_agent.run(query=prompt)
                response = result.get("response", "")
                return self._parse_llm_recommendations(response, market)
            except Exception:
                pass

        # Fallback на простой метод
        recommendations = []
        for insight in market.insights:
            recommendation = ReportRecommendation(
                title=f"Deep dive into {insight.topic}",
                rationale=f"Top sources: {', '.join(insight.sources) if insight.sources else 'knowledge-base'}",
            )
            recommendations.append(recommendation)
        return recommendations

    @staticmethod
    def _parse_llm_recommendations(
        llm_response: str, market: MarketMapperOutput
    ) -> list[ReportRecommendation]:
        """Парсит рекомендации из ответа LLM."""
        recommendations = []
        lines = llm_response.split("\n")
        current_title = None
        current_rationale = []

        for line in lines:
            line = line.strip()
            if not line:
                if current_title and current_rationale:
                    recommendations.append(
                        ReportRecommendation(
                            title=current_title,
                            rationale=" ".join(current_rationale),
                        )
                    )
                    current_title = None
                    current_rationale = []
                continue

            if line.lower().startswith("title:"):
                if current_title and current_rationale:
                    recommendations.append(
                        ReportRecommendation(
                            title=current_title,
                            rationale=" ".join(current_rationale),
                        )
                    )
                current_title = line.split(":", 1)[1].strip()
                current_rationale = []
            elif line.lower().startswith("rationale:"):
                current_rationale.append(line.split(":", 1)[1].strip())
            elif current_rationale:
                current_rationale.append(line)

        if current_title and current_rationale:
            recommendations.append(
                ReportRecommendation(
                    title=current_title,
                    rationale=" ".join(current_rationale),
                )
            )

        # Если не удалось распарсить, используем fallback
        if not recommendations:
            for insight in market.insights:
                recommendations.append(
                    ReportRecommendation(
                        title=f"Deep dive into {insight.topic}",
                        rationale=f"Top sources: {', '.join(insight.sources) if insight.sources else 'knowledge-base'}",
                    )
                )

        return recommendations

