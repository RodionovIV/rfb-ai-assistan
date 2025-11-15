#!/usr/bin/env python3
"""
Тестовый скрипт для проверки всех агентов с LangGraph и OpenAI API.

Использование:
    # Из корня проекта backend/
    python -m src.agents.test_agents
    
    # Или напрямую
    python src/agents/test_agents.py
    
    # С указанием API ключа через переменную окружения
    export OPENAI_API_KEY=your-key-here
    python -m src.agents.test_agents

Требования:
    - Установлен OPENAI_API_KEY в переменных окружения (опционально)
    - Установлены зависимости:
      pip install -r requirements-test.txt
      # или из корня backend/
      cd /home/arseniy/rfb-ai-assistan/backend
      pip install -r requirements-test.txt

Что тестируется:
    1. LangGraphAgent - базовый агент с OpenAI
    2. MarketMapperAgent - анализ рынка с LLM
    3. PitchParserAgent - парсинг презентаций с LLM
    4. WebScoutAgent - веб-поиск с LLM
    5. ReportWriterAgent - генерация отчетов с LLM
    6. Fallback режимы - работа без LLM
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


def test_langgraph_agent(api_key: str | None = None) -> bool:
    """Тестирует базовый LangGraphAgent."""
    print("\n" + "=" * 60)
    print("Тест 1: LangGraphAgent")
    print("=" * 60)

    try:
        agent = LangGraphAgent(
            model_name="gpt-4o-mini",
            api_key=api_key,
            system_prompt="You are a helpful assistant. Answer concisely.",
        )

        result = agent.run(query="What is artificial intelligence in one sentence?")
        print(f"✅ Запрос: What is artificial intelligence?")
        print(f"✅ Ответ: {result['response'][:200]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_market_mapper_agent(api_key: str | None = None) -> bool:
    """Тестирует MarketMapperAgent с LLM."""
    print("\n" + "=" * 60)
    print("Тест 2: MarketMapperAgent с LLM")
    print("=" * 60)

    try:
        # Создаем тестовые документы
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

        agent = MarketMapperAgent(
            knowledge_base=documents,
            top_k=2,
            use_llm=True,
            api_key=api_key,
        )

        queries = ["artificial intelligence", "machine learning"]
        result = agent.run(queries=queries)

        print(f"✅ Запросы: {queries}")
        print(f"✅ Найдено insights: {len(result.get('insights', []))}")
        for insight in result.get("insights", []):
            print(f"   - {insight.get('topic')}: {insight.get('summary', '')[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pitch_parser_agent(api_key: str | None = None) -> bool:
    """Тестирует PitchParserAgent с LLM."""
    print("\n" + "=" * 60)
    print("Тест 3: PitchParserAgent с LLM")
    print("=" * 60)

    try:
        # Создаем тестовые слайды
        slides = [
            SlideContent(
                index=0,
                text="Our startup solves the problem of inefficient data processing in healthcare.",
            ),
            SlideContent(
                index=1,
                text="Our solution is an AI-powered platform that automates medical record analysis.",
            ),
            SlideContent(
                index=2,
                text="The healthcare AI market is worth $15 billion and growing at 25% annually.",
            ),
            SlideContent(
                index=3,
                text="Our business model includes subscription fees and per-transaction charges.",
            ),
            SlideContent(
                index=4,
                text="We have 50+ customers and $2M in revenue this year.",
            ),
        ]

        agent = PitchParserAgent(use_llm=True, api_key=api_key)
        result = agent.run(slides=slides)

        print(f"✅ Обработано слайдов: {len(slides)}")
        print(f"✅ Найдено секций: {len(result.get('sections', []))}")
        for section in result.get("sections", []):
            print(f"   - {section.get('name')}: слайды {section.get('slides')}")
            print(f"     Summary: {section.get('summary', '')[:80]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_web_scout_agent(api_key: str | None = None) -> bool:
    """Тестирует WebScoutAgent с LLM."""
    print("\n" + "=" * 60)
    print("Тест 4: WebScoutAgent с LLM")
    print("=" * 60)

    try:
        agent = WebScoutAgent(use_llm=True, api_key=api_key)
        queries = ["artificial intelligence trends", "healthcare technology"]

        result = agent.run(queries=queries)

        print(f"✅ Запросы: {queries}")
        print(f"✅ Найдено findings: {len(result.get('findings', []))}")
        for finding in result.get("findings", []):
            print(f"   - {finding.get('title')}")
            print(f"     URL: {finding.get('url')}")
            print(f"     Snippet: {finding.get('snippet', '')[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_writer_agent(api_key: str | None = None) -> bool:
    """Тестирует ReportWriterAgent с LLM."""
    print("\n" + "=" * 60)
    print("Тест 5: ReportWriterAgent с LLM")
    print("=" * 60)

    try:
        # Создаем тестовые данные через другие агенты
        # Сначала создаем pitch данные
        slides = [SlideContent(index=0, text="Healthcare data processing is inefficient")]
        pitch_agent = PitchParserAgent(use_llm=False)  # Используем без LLM для простоты
        pitch_result = pitch_agent.run(slides=slides)
        
        # Создаем market данные
        documents = [
            VectorDocument(
                text="AI is transforming healthcare diagnostics and improving patient outcomes.",
                metadata={"source": "report-1"},
            )
        ]
        market_agent = MarketMapperAgent(knowledge_base=documents, use_llm=False)
        market_result = market_agent.run(queries=["AI in healthcare"])
        
        # Создаем web данные
        web_agent = WebScoutAgent(use_llm=False)
        web_result = web_agent.run(queries=["healthcare technology"])

        # Импортируем модели для создания объектов
        try:
            from src.api.projects import (
                MarketMapperOutput,
                PitchParserOutput,
                WebScoutOutput,
            )
            pitch = PitchParserOutput(**pitch_result)
            market = MarketMapperOutput(**market_result)
            web = WebScoutOutput(**web_result)
        except ImportError:
            # Если модели не найдены, используем словари напрямую
            # Это работает, так как агенты принимают объекты с атрибутами
            class SimpleObj:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            
            pitch = SimpleObj(**pitch_result)
            market = SimpleObj(**market_result)
            web = SimpleObj(**web_result)

        agent = ReportWriterAgent(use_llm=True, api_key=api_key)
        result = agent.run(
            project_id="test-project-123",
            pitch=pitch,
            market=market,
            web=web,
        )

        print(f"✅ Отчет создан: {result.get('title')}")
        print(f"✅ Executive Summary: {result.get('executive_summary', '')[:200]}...")
        print(f"✅ Рекомендаций: {len(result.get('recommendations', []))}")
        for rec in result.get("recommendations", [])[:3]:
            print(f"   - {rec.get('title')}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_modes() -> bool:
    """Тестирует агенты в режиме fallback (без LLM)."""
    print("\n" + "=" * 60)
    print("Тест 6: Fallback режимы (без LLM)")
    print("=" * 60)

    try:
        # Тестируем MarketMapperAgent без LLM
        documents = [
            VectorDocument(
                text="Test document about AI",
                metadata={"source": "test"},
            )
        ]

        agent = MarketMapperAgent(
            knowledge_base=documents,
            use_llm=False,
        )

        result = agent.run(queries=["AI"])
        print(f"✅ MarketMapperAgent (без LLM): {len(result.get('insights', []))} insights")

        # Тестируем PitchParserAgent без LLM
        slides = [SlideContent(index=0, text="Our solution solves the problem")]
        agent = PitchParserAgent(use_llm=False)
        result = agent.run(slides=slides)
        print(f"✅ PitchParserAgent (без LLM): {len(result.get('sections', []))} sections")

        # Тестируем WebScoutAgent без LLM
        agent = WebScoutAgent(use_llm=False)
        result = agent.run(queries=["test query"])
        print(f"✅ WebScoutAgent (без LLM): {len(result.get('findings', []))} findings")

        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция для запуска всех тестов."""
    print("\n" + "=" * 60)
    print("Тестирование агентов с LangGraph и OpenAI API")
    print("=" * 60)

    # Получаем API ключ
    # api_key = os.getenv("OPENAI_API_KEY")
    api_key = "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"
    if not api_key:
        print("\n⚠️  ВНИМАНИЕ: OPENAI_API_KEY не установлен в переменных окружения.")
        print("   Тесты с LLM будут пропущены, но fallback режимы будут протестированы.")
        print("   Установите OPENAI_API_KEY для полного тестирования.\n")
        use_llm = False
    else:
        print(f"\n✅ OPENAI_API_KEY найден (длина: {len(api_key)} символов)\n")
        use_llm = True

    results = []

    # Тесты с LLM (если доступен API ключ)
    if use_llm:
        results.append(("LangGraphAgent", test_langgraph_agent(api_key)))
        results.append(("MarketMapperAgent", test_market_mapper_agent(api_key)))
        results.append(("PitchParserAgent", test_pitch_parser_agent(api_key)))
        results.append(("WebScoutAgent", test_web_scout_agent(api_key)))
        results.append(("ReportWriterAgent", test_report_writer_agent(api_key)))
    else:
        print("\n⏭️  Пропуск тестов с LLM (нет API ключа)")

    # Тесты fallback режимов (всегда выполняются)
    results.append(("Fallback режимы", test_fallback_modes()))

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")

    print(f"\nВсего тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")

    if passed == total:
        print("\n🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("\n⚠️  Некоторые тесты провалились.")
        return 1


if __name__ == "__main__":
    exit(main())

