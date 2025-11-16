from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, Iterable, List

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.api.projects import PitchParserOutput, PitchParserSection, SlideModel
from src.services.ingestion import SlideContent

from src.agents.prompts.prompt_pitch_summarizer import BASE_PROMPT, SUMMARY_PROMPT

class PitchSummarizerAgent(Agent):
    name = "pitch_summarizer"

    def __init__(
        self,
        section_hints: Dict[str, Iterable[str]] | None = None,
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
    ) -> None:

        self.use_llm = use_llm

        self.llm_agent = LangGraphAgent(
            model_name=model_name,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            system_prompt=(BASE_PROMPT),
        )

    def run(self, *, slides: List[SlideContent]) -> dict:

        full_text = ""
        for slide in slides:
            full_text += slide.text + "\n"
         
        summary = self._generate_summary_with_llm(full_text)

        # Генерируем summary для каждой секции
        # sections = []
        # for section, indices in sorted(grouped.items()):
        #     section_texts = summaries[section]
        #     summary = self._generate_summary_with_llm(section, section_texts)

        #     sections.append(
        #         PitchParserSection(
        #             name=section,
        #             slides=sorted(indices),
        #             summary=summary,
        #         )
        #     )

        return summary # PitchParserOutput(slides=slide_models, sections=sections).model_dump()

    def _generate_summary_with_llm(self, full_text: str) -> str:
        """Генерирует summary для секции используя LLM."""
        if not self.llm_agent or not full_text:
            return full_text[:1000]

        # combined_text = "\n\n".join([f"Slide {i+1}:\n{text}" for i, text in enumerate(texts)])
        prompt = (
            SUMMARY_PROMPT.format(full_text=full_text)
        )

        try:
            result = self.llm_agent.run(query=prompt)
            summary = result.get("response", "").strip()
            return summary[:1000] if summary else full_text[:1000]
        except Exception:
            return full_text[:1000]

