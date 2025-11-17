from __future__ import annotations

import os, re
from datetime import datetime
from typing import Iterable, List

# try:
from duckduckgo_search import DDGS
DDGS_AVAILABLE = True
# except ImportError:
#     DDGS_AVAILABLE = False

from openai import OpenAI

from src.agents.base import Agent
from src.agents.langgraph_agent import LangGraphAgent
from src.api.projects import WebFinding, WebScoutOutput

from src.agents.prompts.prompt_web_scouter import BASE_PROMPT, BASE_PROMPT2, SUMMARY_PROMPT

class WebScoutAgent(Agent):
    name = "web_scout"

    def __init__(
        self,
        provider_name: str = "duckduckgo",
        use_llm: bool = True,
        api_key: str | None = None,
        model_name: str = "gpt-4.1-mini",
        use_real_search: bool = True,
    ) -> None:
        self.provider_name = provider_name
        self.use_llm = use_llm
        self.use_real_search = True # use_real_search and DDGS_AVAILABLE

        # Инициализируем LangGraph агента для обработки результатов поиска
        # if self.use_llm:
        #     try:
        self.llm_agent = LangGraphAgent(
            model_name=model_name,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            system_prompt=(BASE_PROMPT),
        )
        #     except ValueError:
        #         # Если API ключ не указан, отключаем LLM
        #         self.use_llm = False
        #         self.llm_agent = None
        # else:
        #     self.llm_agent = None

    def run(self, *, queries: Iterable[str]) -> dict:
        findings: List[WebFinding] = []
        
        for query in queries:
            # Выполняем реальный поиск в интернете
            search_results = self._perform_web_search_openai(query)
            print("BBBBB", search_results)
            # if search_results:
            # Обрабатываем результаты поиска
            for result in search_results:  # Берем топ-5 результата
                finding = self._process_search_result(result, query)
                # print("BBBBB", result)
                if finding:
                    findings.append(finding)
            # else:
            #     # Если поиск не дал результатов, используем fallback
            #     finding = self._generate_finding_fallback(query, datetime.utcnow().isoformat())
            #     findings.append(finding)
    
        return WebScoutOutput(findings=findings).model_dump()

    def _perform_web_search(self, query: str, max_results: int = 10) -> List[dict]:
        """Выполняет реальный поиск в интернете используя DuckDuckGo."""
        # if not DDGS_AVAILABLE:
        #     return []
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as e:
            print(f"Ошибка при поиске в интернете: {e}")
            return []

    def _perform_web_search_openai(self, query: str, max_results: int = 10) -> List[dict]:
        """Выполняет реальный поиск в интернете используя OpenAI Web Search."""
        try:
            client = OpenAI(api_key=self.llm_agent.api_key)
            
            response = client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "web_search_preview"}],
                input=BASE_PROMPT2.format(query=query)
            )
            
            print("SEACH ENGINE OUT:", response.output_text)
            # Извлекаем результаты из ответа
            # return self._extract_search_results(response)
            return self._parse_openai_structured_response(text=response.output_text, max_results=7)
            
        except Exception as e:
            print(f"Ошибка при поиске через OpenAI: {e}")
            return []

    def _parse_openai_structured_response(self, text: str, max_results: int) -> List[dict]:
        """Парсит структурированный ответ OpenAI на отдельные результаты поиска."""
        results = []
        
        # Разделяем текст по нумерованным пунктам
        items = re.split(r'\n\d+\.', text)
        
        for item in items[1:]:  # Пропускаем первый элемент (введение)
            if len(results) >= max_results:
                break
                
            # Извлекаем название (в ** **)
            title_match = re.search(r'\*\*([^*]+)\*\*', item)
            if not title_match:
                continue
                
            title = title_match.group(1).strip()
            
            # Извлекаем URL
            url_match = re.search(r'https?://[^\s)\]]+', item)
            url = url_match.group(0) if url_match else ""
            
            # Извлекаем описание (текст между названием и URL)
            description = item.replace(f"**{title}**", "").strip()
            if url_match:
                description = description.replace(url_match.group(0), "").strip()
            
            # Очищаем описание от скобок и лишних символов
            description = re.sub(r'[\[\(].*?[\]\)]', '', description).strip()
            
            results.append({
                "title": title,
                "href": url,
                "body": description
            })
        
        return results

    def _process_search_result(self, result: dict, query: str) -> WebFinding | None:
        """Обрабатывает результат поиска и создает WebFinding."""
        try:
            title = result.get("title", "").strip()
            url = result.get("href", "").strip()
            body = result.get("body", "").strip()
            
            # Если заголовок пустой, создаем из URL
            if not title and url:
                title = self._extract_domain_from_url(url)
            
            if not title:
                title = f"Результат по: {query}"
            
            # Создаем snippet
            snippet = body[:400] + "..." if len(body) > 400 else body
            
            return WebFinding(
                title=title[:100],
                url=url,
                snippet=snippet,
            )
            
        except Exception as e:
            print(f"Ошибка при обработке результата поиска: {e}")
            return None

    def _extract_domain_from_url(self, url: str) -> str:
        """Извлекает домен из URL для использования как заголовка."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace("www.", "").split(".")[0].title()
        except:
            return "Web Source"

    def _extract_search_results(self, response) -> List[dict]:
        """Извлекает структурированные результаты поиска из ответа OpenAI."""
        results = []
        
        # Основной ответ модели
        if response.output_text:
            results.append({
                "title": "AI Summary",
                "href": "",
                "body": response.output_text
            })
        
        # Извлекаем источники с цитатами
        if (hasattr(response, 'context') and 
            hasattr(response.context, 'citations') and 
            response.context.citations):
            
            for citation in response.context.citations:
                results.append({
                    "title": self._extract_title_from_citation(citation),
                    "href": getattr(citation, 'url', ''),
                    "body": getattr(citation, 'content', '')[:500]  # Ограничиваем длину
                })
        
        return results

    def _extract_title_from_citation(self, citation) -> str:
        """Извлекает заголовок из цитаты."""
        if hasattr(citation, 'title') and citation.title:
            return citation.title
        elif hasattr(citation, 'url') and citation.url:
            # Извлекаем домен как заголовок
            from urllib.parse import urlparse
            domain = urlparse(citation.url).netloc
            return f"Source from {domain}"
        else:
            return "Web Source"


    def _perform_web_search_bing(self, query: str, max_results: int = 10) -> List[dict]:
        """Выполняет реальный поиск в интернете используя Bing Search."""
        try:
            # Добавляем небольшую задержку чтобы избежать лимитов
            time.sleep(0.5)
            
            subscription_key = "YOUR_BING_API_KEY"  # Замените на ваш ключ
            search_url = "https://api.bing.microsoft.com/v7.0/search"
            
            headers = {"Ocp-Apim-Subscription-Key": subscription_key}
            params = {
                "q": query,
                "count": max_results,
                "mkt": "ru-RU",
                "responseFilter": "Webpages"
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json()
            
            # Преобразуем в тот же формат что и DDGS
            formatted_results = []
            if "webPages" in search_results and "value" in search_results["webPages"]:
                for item in search_results["webPages"]["value"]:
                    formatted_results.append({
                        "title": item.get("name", ""),
                        "href": item.get("url", ""),
                        "body": item.get("snippet", "")
                    })
            
            return formatted_results
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при поиске: {e}")
            return []
        except ValueError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return []
        except Exception as e:
            print(f"Неожиданная ошибка при поиске: {e}")
            return []

    def _process_search_result_old(self, result: dict, query: str) -> WebFinding | None:
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
        # if not self.llm_agent:
        #     return content[:300]
        
        prompt = (
            SUMMARY_PROMPT.format(query=query, content=content[:1000])
        )
        
        try:
            result = self.llm_agent.run(query=prompt)
            return result.get("response", content[:300])
        except Exception:
            return content[:300]
