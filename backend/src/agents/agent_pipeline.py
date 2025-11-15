#!/usr/bin/env python3
"""
Использование:
    # Из корня проекта backend/
    python -m src.agents.test_agents
    
    # Или напрямую
    python src/agents/test_agents.py
    
    # С указанием API ключа через переменную окружения
    export OPENAI_API_KEY=your-key-here
    python -m src.agents.test_agents
"""

from __future__ import annotations

import os
import sys
from typing import List

# Добавляем путь к корню проекта backend/ (где находится src/)
_script_dir = os.path.dirname(os.path.abspath(__file__))
# test_agents.py находится в backend/src/agents/, поэтому ../.. ведет к backend/
_backend_dir = os.path.abspath(os.path.join(_script_dir, "../.."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from src.agents import (
    LangGraphAgent,
    MarketMapperAgent,
    PitchParserAgent,
    ReportWriterAgent,
    VectorDocument,
    WebScoutAgent,
)
from src.services.ingestion import SlideContent

from src.api.projects import (
    MarketMapperOutput,
    PitchParserOutput,
    WebScoutOutput,
)

# api_key = os.getenv("OPENAI_API_KEY")
api_key = "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"


def run_langgraph_agent(query, prompt):
    try:
        agent = LangGraphAgent(
            model_name="gpt-4o-mini",
            api_key=api_key,
            system_prompt=prompt,
        )

        result = agent.run(query=query)
        print(query)
        print(f"Ответ: {result['response']}")
        return result['response']
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def run_market_mapper_agent(documents, queries):
    try:
        agent = MarketMapperAgent(
            knowledge_base=documents,
            top_k=2,
            use_llm=True,
            api_key=api_key,
        )

        queries = ["artificial intelligence", "machine learning"]
        result = agent.run(queries=queries)

        print(f"Запросы: {queries}")
        print(f"Найдено insights: {len(result.get('insights', []))}")
        for insight in result.get("insights", []):
            print(f"   - {insight.get('topic')}: {insight.get('summary', '')}...")
        
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_pitch_parser_agent(raw_slides):
    try:
        slides = []
        idx = 0
        for raw_slide in raw_slides:
            slides.append(SlideContent(index=idx, text=raw_slide))
            idx += 1

        agent = PitchParserAgent(use_llm=True, api_key=api_key)
        result = agent.run(slides=slides)

        print(f"Обработано слайдов: {len(slides)}")
        print(f"Найдено секций: {len(result.get('sections', []))}")
        for section in result.get("sections", []):
            print(f"   - {section.get('name')}: слайды {section.get('slides')}")
            print(f"     Summary: {section.get('summary', '')}...")
        
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_web_scout_agent(queries):
    try:
        agent = WebScoutAgent(use_llm=True, api_key=api_key)
        result = agent.run(queries=queries)

        print(f"Запросы: {queries}")
        print(f"Найдено findings: {len(result.get('findings', []))}")
        for finding in result.get("findings", []):
            print(f"   - {finding.get('title')}")
            print(f"     URL: {finding.get('url')}")
            print(f"     Snippet: {finding.get('snippet', '')}...")
        
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_report_writer_agent(project_id, pitch_result, market_result, web_result):
    try:
            
        pitch = PitchParserOutput(**pitch_result)
        market = MarketMapperOutput(**market_result)
        web = WebScoutOutput(**web_result)

        agent = ReportWriterAgent(use_llm=True, api_key=api_key)
        result = agent.run(
            project_id=project_id,
            pitch=pitch,
            market=market,
            web=web,
        )

        print(f"Отчет создан: {result.get('title')}")
        print(f"Executive Summary: {result.get('executive_summary', '')}...")
        print(f"Рекомендаций: {len(result.get('recommendations', []))}")
        for rec in result.get("recommendations", []):
            print(f"   - {rec.get('title')}")
        
        return result
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


def split_markdown_by_slides(md_text: str):
    if "Слайд" in md_text:
        parts = md_text.split("Слайд")
    elif "Slide" in md_text:
        parts = md_text.split("Slide")
    else:
        exit(-1)
        print("Can't parse md")
    
    slides = []
    for part in parts:
        cleaned = part.strip()
        if cleaned:
            if not cleaned.startswith("Слайд"):
                cleaned = "Слайд " + cleaned
            slides.append(cleaned)
    
    return slides

def main():
    md_path = "/home/arseniy/rfb-ai-assistan/data/aurora-desk.md"
    with open(md_path, 'r') as f:
        md_content = f.read()
    slides = split_markdown_by_slides(md_content)


    # query = "What is artificial intelligence in one sentence?"
    # prompt = "You are a helpful assistant. Answer concisely."
    # answer = run_langgraph_agent(query, prompt)

    pitch_data = run_pitch_parser_agent(slides)

    queries = []
    for sec_res in pitch_data['sections']:
        queries.append(sec_res['summary'])

    web_data = run_web_scout_agent(queries)

    documents = [
        VectorDocument(
            text="Artificial intelligence is transforming healthcare with diagnostic tools.",
            metadata={"source": "healthcare-report-2024"},
        ),
        VectorDocument(
            text="AI market is expected to grow 25% annually over the next 5 years.",
            metadata={"source": "market-analysis"},
        ),
        VectorDocument(
            text="Machine learning algorithms are being used in autonomous vehicles.",
            metadata={"source": "tech-news"},
        ),
    ]

    market_data = run_market_mapper_agent(documents, queries)
    
    report = run_report_writer_agent("test-project-123", pitch_data, market_data, web_data)

if __name__ == "__main__":
    exit(main())

