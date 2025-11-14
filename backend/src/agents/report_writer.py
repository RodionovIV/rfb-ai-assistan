from __future__ import annotations

from typing import Iterable

from src.agents.base import Agent
from src.api.projects import (
    MarketMapperOutput,
    PitchParserOutput,
    ReportRecommendation,
    ReportWriterOutput,
    WebScoutOutput,
)


class ReportWriterAgent(Agent):
    name = "report_writer"

    def run(
        self,
        *,
        project_id: str,
        pitch: PitchParserOutput,
        market: MarketMapperOutput,
        web: WebScoutOutput,
    ) -> dict:
        recommendations = self._build_recommendations(market)
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

    @staticmethod
    def _compose_summary(
        *, pitch: PitchParserOutput, market: MarketMapperOutput, web: WebScoutOutput
    ) -> str:
        pitch_sections = ", ".join(section.name for section in pitch.sections) or "No sections identified"
        market_topics = ", ".join(insight.topic for insight in market.insights) or "No market insights"
        web_sources = ", ".join(finding.title for finding in web.findings) or "No web findings"
        return (
            "The pitch deck analysis covered the following sections: "
            f"{pitch_sections}. Market research highlighted {market_topics}. Web scouting captured "
            f"signals from: {web_sources}."
        )

    @staticmethod
    def _build_recommendations(market: MarketMapperOutput) -> Iterable[ReportRecommendation]:
        if not market.insights:
            return []
        recommendations = []
        for insight in market.insights:
            recommendation = ReportRecommendation(
                title=f"Deep dive into {insight.topic}",
                rationale=f"Top sources: {', '.join(insight.sources) if insight.sources else 'knowledge-base'}",
            )
            recommendations.append(recommendation)
        return recommendations

