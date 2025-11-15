from __future__ import annotations

import os
from typing import Any, Dict, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base import Agent


class AgentState(TypedDict):
    """Состояние агента в графе LangGraph."""
    messages: list[HumanMessage | AIMessage | SystemMessage]
    context: Dict[str, Any]


class LangGraphAgent(Agent):
    """Агент на основе LangGraph с использованием OpenAI API."""

    name = "langgraph_agent"

    def __init__(
        self,
        *,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        api_key: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """
        Инициализация LangGraph агента.

        Args:
            model_name: Название модели OpenAI
            temperature: Температура для генерации (0.0-1.0)
            api_key: API ключ OpenAI (если не указан, берется из переменной окружения OPENAI_API_KEY)
            system_prompt: Системный промпт для агента
        """
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable"
            )

        self.system_prompt = system_prompt or (
            "You are a helpful AI assistant that provides accurate and detailed responses. "
            "Use the provided context to answer questions when available."
        )

        # Инициализация LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=self.api_key,
        )

        # Создание графа
        self.graph = self._build_graph()

    def _build_graph(self):
        """Строит граф состояний для агента."""
        workflow = StateGraph(AgentState)

        # Добавляем узел агента
        workflow.add_node("agent", self._agent_node)

        # Определяем поток
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)

        return workflow.compile()

    def _agent_node(self, state: AgentState) -> AgentState:
        """
        Узел агента, который обрабатывает сообщения.

        Args:
            state: Текущее состояние агента

        Returns:
            Обновленное состояние
        """
        messages = state.get("messages", [])
        context = state.get("context", {})

        # Формируем системное сообщение с контекстом
        system_content = self.system_prompt
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            system_content += f"\n\nContext:\n{context_str}"

        # Создаем список сообщений с системным промптом
        full_messages = [SystemMessage(content=system_content)] + messages

        # Вызываем LLM
        response = self.llm.invoke(full_messages)

        # Обновляем состояние
        return {
            "messages": messages + [response],
            "context": context,
        }

    def run(
        self,
        *,
        query: str,
        context: Dict[str, Any] | None = None,
        message_history: list[HumanMessage | AIMessage] | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Выполняет логику агента и возвращает результат.

        Args:
            query: Запрос пользователя
            context: Дополнительный контекст для агента
            message_history: История предыдущих сообщений для поддержания контекста диалога
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с результатом работы агента
        """
        # Формируем список сообщений с историей
        messages = list(message_history) if message_history else []
        messages.append(HumanMessage(content=query))

        # Инициализируем состояние
        initial_state: AgentState = {
            "messages": messages,
            "context": context or {},
        }

        # Запускаем граф
        try:
            result = self.graph.invoke(initial_state)
            
            # Извлекаем последний ответ от агента
            result_messages = result.get("messages", [])
            if result_messages and isinstance(result_messages[-1], AIMessage):
                response_content = result_messages[-1].content
            else:
                response_content = "Не удалось получить ответ от агента."

            return {
                "response": response_content,
                "query": query,
                "context": result.get("context", {}),
                "messages_count": len(result_messages),
            }
        except Exception as e:
            raise RuntimeError(f"Ошибка при выполнении агента: {str(e)}") from e

    async def arun(
        self,
        *,
        query: str,
        context: Dict[str, Any] | None = None,
        message_history: list[HumanMessage | AIMessage] | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Асинхронная версия run.

        Args:
            query: Запрос пользователя
            context: Дополнительный контекст для агента
            message_history: История предыдущих сообщений для поддержания контекста диалога
            **kwargs: Дополнительные параметры

        Returns:
            Словарь с результатом работы агента
        """
        # Формируем список сообщений с историей
        messages = list(message_history) if message_history else []
        messages.append(HumanMessage(content=query))

        initial_state: AgentState = {
            "messages": messages,
            "context": context or {},
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            
            result_messages = result.get("messages", [])
            if result_messages and isinstance(result_messages[-1], AIMessage):
                response_content = result_messages[-1].content
            else:
                response_content = "Не удалось получить ответ от агента."

            return {
                "response": response_content,
                "query": query,
                "context": result.get("context", {}),
                "messages_count": len(result_messages),
            }
        except Exception as e:
            raise RuntimeError(f"Ошибка при выполнении агента: {str(e)}") from e

