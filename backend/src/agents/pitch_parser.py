from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, Iterable, List

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.api.projects import PitchParserOutput, PitchParserSection, SlideModel
from src.services.ingestion import SlideContent


class PitchParserAgent(Agent):
    name = "pitch_parser"

    def __init__(
        self,
        section_hints: Dict[str, Iterable[str]] | None = None,
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
    ) -> None:
        self.section_hints = section_hints or {
            "problem": ["problem", "pain", "challenge"],
            "solution": ["solution", "product", "platform"],
            "market": ["market", "size", "growth"],
            "business_model": ["business model", "revenue", "pricing"],
            "traction": ["traction", "milestone", "customer"],
            "team": ["team", "founder", "advisor"],
        }
        self.use_llm = use_llm

        # Инициализируем LangGraph агента для улучшенной классификации и summary
        if self.use_llm:
            try:
                self.llm_agent = LangGraphAgent(
                    model_name=model_name,
                    api_key=api_key or os.getenv("OPENAI_API_KEY"),
                    system_prompt=(
                        "You are an expert at analyzing pitch decks and presentations. "
                        "Classify slides into appropriate sections and create concise summaries. "
                        "Identify key information about problems, solutions, market, business model, traction, and team."
                    ),
                )
            except ValueError:
                # Если API ключ не указан, отключаем LLM
                self.use_llm = False
                self.llm_agent = None
        else:
            self.llm_agent = None

    def run(self, *, slides: List[SlideContent]) -> dict:
        slide_models = [SlideModel(index=slide.index, text=slide.text) for slide in slides]
        grouped: Dict[str, List[int]] = defaultdict(list)
        summaries: Dict[str, List[str]] = defaultdict(list)

        # Используем LLM для улучшенной классификации, если доступно
        if self.use_llm and self.llm_agent:
            for slide in slides:
                section = self._classify_slide_with_llm(slide)
                if section:
                    grouped[section].append(slide.index)
                    summaries[section].append(slide.text)
        else:
            # Fallback на простую классификацию по ключевым словам
            for slide in slides:
                text_lower = slide.text.lower()
                for section, keywords in self.section_hints.items():
                    if any(keyword in text_lower for keyword in keywords):
                        grouped[section].append(slide.index)
                        summaries[section].append(slide.text)

        # Генерируем summary для каждой секции
        sections = []
        for section, indices in sorted(grouped.items()):
            section_texts = summaries[section]
            if self.use_llm and self.llm_agent:
                summary = self._generate_summary_with_llm(section, section_texts)
            else:
                summary = " ".join(section_texts)[:500]

            sections.append(
                PitchParserSection(
                    name=section,
                    slides=sorted(indices),
                    summary=summary,
                )
            )

        return PitchParserOutput(slides=slide_models, sections=sections).model_dump()

    def _classify_slide_with_llm(self, slide: SlideContent) -> str | None:
        """Классифицирует слайд используя LLM."""
        if not self.llm_agent:
            return None

        available_sections = ", ".join(self.section_hints.keys())
        prompt = (
            f"Analyze this pitch deck slide and classify it into one of these sections: {available_sections}. "
            f"Return only the section name, nothing else.\n\nSlide text:\n{slide.text}"
        )

        try:
            result = self.llm_agent.run(query=prompt)
            response = result.get("response", "").strip().lower()
            
            # Проверяем, соответствует ли ответ одной из секций
            for section in self.section_hints.keys():
                if section.lower() in response or response in section.lower():
                    return section
        except Exception:
            pass

        return None

    def _generate_summary_with_llm(self, section: str, texts: List[str]) -> str:
        """Генерирует summary для секции используя LLM."""
        if not self.llm_agent or not texts:
            return " ".join(texts)[:500]

        combined_text = "\n\n".join([f"Slide {i+1}:\n{text}" for i, text in enumerate(texts)])
        prompt = (
            f"Create a concise summary (max 500 characters) for the '{section}' section "
            f"based on these slides:\n\n{combined_text}"
        )

        try:
            result = self.llm_agent.run(query=prompt)
            summary = result.get("response", "").strip()
            return summary[:500] if summary else " ".join(texts)[:500]
        except Exception:
            return " ".join(texts)[:500]

