from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from src.agents.base import Agent
from src.api.projects import PitchParserOutput, PitchParserSection, SlideModel
from src.services.ingestion import SlideContent


class PitchParserAgent(Agent):
    name = "pitch_parser"

    def __init__(self, section_hints: Dict[str, Iterable[str]] | None = None) -> None:
        self.section_hints = section_hints or {
            "problem": ["problem", "pain", "challenge"],
            "solution": ["solution", "product", "platform"],
            "market": ["market", "size", "growth"],
            "business_model": ["business model", "revenue", "pricing"],
            "traction": ["traction", "milestone", "customer"],
            "team": ["team", "founder", "advisor"],
        }

    def run(self, *, slides: List[SlideContent]) -> dict:
        slide_models = [SlideModel(index=slide.index, text=slide.text) for slide in slides]
        grouped: Dict[str, List[int]] = defaultdict(list)
        summaries: Dict[str, List[str]] = defaultdict(list)

        for slide in slides:
            text_lower = slide.text.lower()
            for section, keywords in self.section_hints.items():
                if any(keyword in text_lower for keyword in keywords):
                    grouped[section].append(slide.index)
                    summaries[section].append(slide.text)

        sections = [
            PitchParserSection(
                name=section,
                slides=sorted(indices),
                summary=" ".join(summaries[section])[:500],
            )
            for section, indices in sorted(grouped.items())
        ]

        return PitchParserOutput(slides=slide_models, sections=sections).model_dump()

