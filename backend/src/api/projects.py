from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SlideModel(BaseModel):
    index: int
    text: str = ""


class PitchParserSection(BaseModel):
    name: str
    slides: List[int] = Field(default_factory=list)
    summary: str = ""


class PitchParserOutput(BaseModel):
    slides: List[SlideModel] = Field(default_factory=list)
    sections: List[PitchParserSection] = Field(default_factory=list)


class MarketInsight(BaseModel):
    topic: str
    summary: str
    sources: List[str] = Field(default_factory=list)


class MarketMapperOutput(BaseModel):
    insights: List[MarketInsight] = Field(default_factory=list)


class WebFinding(BaseModel):
    title: str
    url: str
    snippet: str = ""


class WebScoutOutput(BaseModel):
    findings: List[WebFinding] = Field(default_factory=list)


class ReportRecommendation(BaseModel):
    title: str
    rationale: str


class ReportWriterOutput(BaseModel):
    title: str
    executive_summary: str
    recommendations: List[ReportRecommendation] = Field(default_factory=list)
    appendix: Dict[str, Any] = Field(default_factory=dict)


class ProjectProcessResponse(BaseModel):
    project_id: str
    document_path: str
    slides_processed: int
    pitch: PitchParserOutput
    market: MarketMapperOutput
    web: WebScoutOutput
    report: ReportWriterOutput
    report_path: Optional[str] = None


class ProjectProcessPayload(BaseModel):
    notes: Optional[str] = None
    focus_keywords: List[str] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "notes": "Prioritize climate-tech investors",
                "focus_keywords": ["climate", "sustainability"],
            }
        }
    }

