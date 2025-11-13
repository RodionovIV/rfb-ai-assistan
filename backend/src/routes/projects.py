from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import Body, File, HTTPException, UploadFile, status

from src.agents import (
    MarketMapperAgent,
    PitchParserAgent,
    ReportWriterAgent,
    VectorDocument,
    WebScoutAgent,
)
from src.api.projects import (
    MarketMapperOutput,
    PitchParserOutput,
    ProjectProcessPayload,
    ProjectProcessResponse,
    ReportWriterOutput,
    WebScoutOutput,
)
from src.routes.router import base_router
from src.services.ingestion import TextIngestionService, UnsupportedFileFormatError
from src.settings.params.api import API


INGESTION_SERVICE = TextIngestionService()
PITCH_PARSER_AGENT = PitchParserAgent()
MARKET_MAPPER_AGENT = MarketMapperAgent(
    knowledge_base=[
        VectorDocument(
            text="The climate technology market is growing at a 24% CAGR across energy storage and carbon capture.",
            metadata={"source": "climate-report-2024"},
        ),
        VectorDocument(
            text="Enterprise SaaS platforms rely on subscription revenue and annual contract value expansion strategies.",
            metadata={"source": "saas-benchmark"},
        ),
        VectorDocument(
            text="Investments in emerging markets highlight rising competition among regional venture firms.",
            metadata={"source": "emerging-markets-brief"},
        ),
    ]
)
WEB_SCOUT_AGENT = WebScoutAgent()
REPORT_WRITER_AGENT = ReportWriterAgent()


def _build_market_queries(
    payload: ProjectProcessPayload | None, pitch: PitchParserOutput
) -> List[str]:
    if payload and payload.focus_keywords:
        return payload.focus_keywords
    summaries = [section.summary for section in pitch.sections if section.summary]
    return summaries or ["market overview"]


def _build_web_queries(payload: ProjectProcessPayload | None, market: MarketMapperOutput) -> List[str]:
    if payload and payload.focus_keywords:
        return payload.focus_keywords
    return [insight.topic for insight in market.insights] or ["industry trends"]


@base_router.post(API.PROJECT_PROCESS, response_model=ProjectProcessResponse)
async def process_project(
    project_id: str,
    document: UploadFile = File(..., description="Pitch deck document (PDF or PPTX)"),
    payload: ProjectProcessPayload | None = Body(default=None),
) -> ProjectProcessResponse:
    try:
        ingestion_result = await INGESTION_SERVICE.ingest(project_id=project_id, upload=document)
    except UnsupportedFileFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    pitch_data = PITCH_PARSER_AGENT.run(slides=ingestion_result.slides)
    pitch_model = PitchParserOutput.model_validate(pitch_data)

    market_queries = _build_market_queries(payload, pitch_model)
    market_data = MARKET_MAPPER_AGENT.run(queries=market_queries)
    market_model = MarketMapperOutput.model_validate(market_data)

    web_queries = _build_web_queries(payload, market_model)
    web_data = WEB_SCOUT_AGENT.run(queries=web_queries)
    web_model = WebScoutOutput.model_validate(web_data)

    report_data = REPORT_WRITER_AGENT.run(
        project_id=project_id,
        pitch=pitch_model,
        market=market_model,
        web=web_model,
    )
    report_model = ReportWriterOutput.model_validate(report_data)

    response = ProjectProcessResponse(
        project_id=project_id,
        document_path=ingestion_result.stored_path,
        slides_processed=len(ingestion_result.slides),
        pitch=pitch_model,
        market=market_model,
        web=web_model,
        report=report_model,
    )

    report_path = _persist_report(response=response)
    return response.model_copy(update={"report_path": report_path})


def _persist_report(response: ProjectProcessResponse) -> str:
    project_dir = Path(response.document_path).parent
    project_dir.mkdir(parents=True, exist_ok=True)
    report_path = project_dir / "report.json"
    payload = response.model_copy(update={"report_path": str(report_path)})
    report_path.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False)
    )
    return str(report_path)

