from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:
    from src.agents import VectorDocument

import logging

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

# Agents are imported lazily in _generate_report to avoid circular imports
from src.api.projects import MarketMapperOutput, PitchParserOutput, WebScoutOutput
from src.database import (
    ContextChunk,
    File,
    MessageRole,
    Project as ProjectModel,
    get_session,
    redis_client,
    vector_index,
)
from src.repositories import (
    ContextChunkRepository,
    FileRepository,
    MessageRepository,
    ProjectRepository,
    ReportRepository,
    VectorIndexRepository,
)
from src.services.ingestion import IngestionResult, SlideContent, TextIngestionService
from src.services.utils import build_embedding
from src.settings.general import config

logger = logging.getLogger(__name__)


class ProjectNotFoundError(LookupError):
    """Raised when a project identifier does not match a stored project."""

    def __init__(self, project_id: str) -> None:
        super().__init__(f"Project '{project_id}' was not found")
        self.project_id = project_id


@dataclass(slots=True)
class ProjectMessage:
    role: str
    content: str


@dataclass(slots=True)
class ProjectFile:
    path: str
    original_name: str | None = None


@dataclass(slots=True)
class Project:
    id: str
    name: str
    description: str | None
    files: list[ProjectFile] = field(default_factory=list)
    processed: bool = False
    analysis_summary: str | None = None
    context_summary: str | None = None
    rating: int | None = None
    rating_comment: str | None = None
    history: list[ProjectMessage] = field(default_factory=list)


class ProjectsService:
    """High level coordinator for project management operations."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        ingestion_service: TextIngestionService | None = None,
        vector_repo: VectorIndexRepository | None = None,
    ) -> None:
        self._session = session
        self._projects = ProjectRepository(session)
        self._files = FileRepository(session)
        self._chunks = ContextChunkRepository(session)
        self._messages = MessageRepository(session)
        self._reports = ReportRepository(session)
        self._vector_repo = vector_repo or VectorIndexRepository(redis_client, vector_index)
        self._ingestion = ingestion_service or TextIngestionService()
        self._project_service = ProjectService(self._vector_repo)

    async def create_project(self, *, name: str, description: str | None = None) -> Project:
        project = await self._projects.create(name=name, description=description)
        await self._session.commit()
        return await self._build_project(project)

    async def upload_file(self, project_id: str, file: UploadFile) -> tuple[Project, str]:
        project = await self._get_project_or_raise(project_id)
        ingestion = await self._ingestion.ingest(str(project.id), file)
        file_record = await self._project_service.create_file(
            self._files,
            project_id=project.id,
            path=ingestion.stored_path,
            original_name=ingestion.original_filename,
        )

        await self._register_slides(project_id=project.id, file=file_record, ingestion=ingestion)
        await self._session.commit()

        await self._generate_report(project=project, slides=ingestion.slides)
        await self._session.commit()

        project_model = await self._projects.get(project.id)
        assert project_model is not None  # for type checkers
        return await self._build_project(project_model), ingestion.stored_path

    async def process_project(self, project_id: str) -> tuple[Project, str]:
        project = await self._get_project_or_raise(project_id)
        files = await self._files.list_by_project(project.id)
        if not files:
            chunks = await self._chunks.list_by_project(project.id)
            summary = self._summarise_chunks(project.name, chunks)
            await self._reports.create(
                project_id=project.id,
                title=f"Analysis for {project.name}",
                content=summary,
            )
            await self._session.commit()
            return await self.get_project(project_id), summary

        latest_file = files[0]
        try:
            ingestion = await self._ingestion.ingest_from_path(
                project_id=str(project.id),
                path=latest_file.path,
                original_name=latest_file.original_name,
            )
        except FileNotFoundError:
            message = (
                "Загруженный документ не найден на сервере. Загрузите файл повторно для запуска анализа."
            )
            await self._messages.create(
                project_id=project.id,
                role=MessageRole.SYSTEM,
                content=message,
            )
            await self._session.commit()
            return await self.get_project(project_id), message

        summary, _ = await self._generate_report(project=project, slides=ingestion.slides)
        await self._session.commit()
        updated_project = await self.get_project(project_id)
        details = summary or updated_project.analysis_summary or "Анализ завершён"
        return updated_project, details

    async def list_projects(self) -> list[Project]:
        projects = await self._projects.list()
        payload: list[Project] = []
        for project in projects:
            payload.append(await self._build_project(project))
        return payload

    async def get_project(self, project_id: str) -> Project:
        project = await self._get_project_or_raise(project_id)
        return await self._build_project(project)

    async def delete_project(self, project_id: str) -> Project:
        project = await self._get_project_or_raise(project_id)
        project_payload = await self._build_project(project)
        await self._projects.delete(project.id)
        await self._session.commit()
        return project_payload

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Project:
        project = await self._get_project_or_raise(project_id)
        updates: dict[str, str | None] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if updates:
            await self._projects.update(project.id, **updates)
            await self._session.commit()
        updated = await self._projects.get(project.id)
        assert updated is not None
        return await self._build_project(updated)

    async def rate_project(
        self,
        *,
        project_id: str,
        rating: int,
        comment: str | None = None,
    ) -> Project:
        project = await self._get_project_or_raise(project_id)
        normalized_comment = comment.strip() if comment else None
        await self._projects.update(
            project.id,
            rating=rating,
            rating_comment=normalized_comment,
        )
        await self._session.commit()
        updated = await self._projects.get(project.id)
        assert updated is not None
        return await self._build_project(updated)

    async def add_message(
        self,
        *,
        project_id: str,
        message: str,
    ) -> tuple[Project, ProjectMessage, list[ProjectMessage]]:
        project = await self._get_project_or_raise(project_id)
        await self._messages.create(
            project_id=project.id,
            role=MessageRole.USER,
            content=message,
        )

        # Получаем весь доступный контекст
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        embedding = build_embedding(message)
        context_chunks = await self._vector_repo.search_similar(embedding, limit=5)
        context_summary = await self._get_latest_context_summary(project.id)
        print("context_summary", context_summary)
        # Получаем analysis_summary из отчета
        reports = await self._reports.list_by_project(project.id)
        analysis_summary = reports[0].content if reports else None
        
        # Получаем историю сообщений для контекста диалога (исключаем только что добавленное сообщение)
        all_messages = await self._messages.list_by_project(project.id)
        # Исключаем последнее сообщение (только что добавленное сообщение пользователя)
        message_history = all_messages[:-1] if len(all_messages) > 1 else []
        
        # Генерируем ответ с использованием LLM агента
        reply_content = await self._compose_response_with_agent(
            message=message,
            context_chunks=context_chunks,
            context_summary=context_summary,
            analysis_summary=analysis_summary,
            message_history=message_history,
            project_name=project.name,
        )

        await self._messages.create(
            project_id=project.id,
            role=MessageRole.ASSISTANT,
            content=reply_content,
            metadata={
                "related_chunks": [item.get("chunk_id") for item in context_chunks],
                "source": "langgraph-agent",
                "context_summary": context_summary,
            },
        )

        await self._session.commit()
        project_payload = await self.get_project(project_id)
        reply = ProjectMessage(role=MessageRole.ASSISTANT.value, content=reply_content)
        history = project_payload.history
        return project_payload, reply, history

    async def _register_slides(
        self,
        *,
        project_id: uuid.UUID,
        file: File,
        ingestion: IngestionResult,
    ) -> None:
        if not ingestion.slides:
            return
        for slide in ingestion.slides:
            text = slide.text.strip()
            if not text:
                continue
            embedding = build_embedding(text)
            await self._project_service.register_context_chunk(
                self._chunks,
                project_id=project_id,
                file_id=file.id,
                chunk_index=slide.index,
                content=text,
                embedding=embedding,
                metadata={
                    "slide_index": slide.index,
                    "filename": ingestion.original_filename,
                },
            )

    async def _get_project_or_raise(self, project_id: str) -> ProjectModel:
        try:
            identifier = uuid.UUID(project_id)
        except ValueError as exc:  # pragma: no cover - validated via API layer
            raise ProjectNotFoundError(project_id) from exc
        project = await self._projects.get(identifier)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    async def _build_project(self, project: ProjectModel) -> Project:
        files = await self._files.list_by_project(project.id)
        reports = await self._reports.list_by_project(project.id)
        messages = await self._messages.list_by_project(project.id)

        history = [
            ProjectMessage(role=message.role.value, content=message.content)
            for message in messages
        ]

        analysis_summary = reports[0].content if reports else None
        context_summary = reports[0].context if reports else None
        return Project(
            id=str(project.id),
            name=project.name,
            description=project.description,
            files=[ProjectFile(path=file.path, original_name=file.original_name) for file in files],
            processed=bool(reports),
            analysis_summary=analysis_summary,
            context_summary=context_summary,
            rating=project.rating,
            rating_comment=project.rating_comment,
            history=history,
        )

    async def _get_latest_context_summary(self, project_id: uuid.UUID) -> str | None:
        reports = await self._reports.list_by_project(project_id)
        if not reports:
            return None
        return reports[0].context

    async def _generate_report(
        self,
        *,
        project: ProjectModel,
        slides: list[SlideContent],
    ) -> tuple[str | None, str | None]:
        if not slides:
            return None, None

        try:
            # Lazy import to avoid circular dependency
            from src.agents import (
                MarketMapperAgent,
                PitchParserAgent,
                PitchSummarizerAgent,
                ReportWriterAgent,
                WebScoutAgent,
            )

            pitch_summarizer = PitchSummarizerAgent()
            pitch_summary = pitch_summarizer.run(slides=slides)
            print("PITCH SUMMARY", pitch_summary)
            pitch_agent = PitchParserAgent()
            pitch_result = pitch_agent.run(slides=slides)
            pitch_output = PitchParserOutput(**pitch_result)
            queries = self._extract_queries_from_pitch(pitch_output, fallback=project.name)

            knowledge_base = await self._build_vector_documents(project.id)
            market_agent = MarketMapperAgent(knowledge_base=knowledge_base, top_k=3)
            market_result = market_agent.run(queries=queries)
            market_output = MarketMapperOutput(**market_result)

            web_agent = WebScoutAgent(use_real_search=True)
            web_result = web_agent.run(queries=[pitch_summary])#queries[:5])
            web_output = WebScoutOutput(**web_result)

            report_agent = ReportWriterAgent()
            report_result = report_agent.run(
                project_id=str(project.id),
                pitch=pitch_output,
                market=market_output,
                web=web_output,
            )

            context_payload = self._compose_context_payload(market_output, web_output)
            context_value = context_payload or None
            await self._reports.create(
                project_id=project.id,
                title=report_result.get("title", f"Отчет о проекте {project.name}"),
                content=report_result.get("executive_summary", ""),
                context=context_value,
            )

            message_text = self._format_report_message(report_result, context_value)
            await self._messages.create(
                project_id=project.id,
                role=MessageRole.ASSISTANT,
                content=message_text,
                metadata={
                    "source": "report-pipeline",
                    "context_summary": context_value,
                    "recommendations": report_result.get("recommendations", []),
                },
            )

            return report_result.get("executive_summary"), context_value
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to generate report for project %s", project.id)
            failure_message = (
                "Не удалось автоматически сформировать отчёт. Попробуйте повторить попытку позднее."
            )
            await self._messages.create(
                project_id=project.id,
                role=MessageRole.SYSTEM,
                content=failure_message,
                metadata={"error": str(exc)},
            )
            return None, None

    async def _build_vector_documents(self, project_id: uuid.UUID) -> list[VectorDocument]:
        # Lazy import to avoid circular dependency
        from src.agents import VectorDocument

        chunks = await self._chunks.list_by_project(project_id)
        documents: list[VectorDocument] = []
        for chunk in chunks:
            documents.append(
                VectorDocument(
                    text=chunk.content,
                    metadata={
                        "chunk_id": str(chunk.id),
                        "file_id": str(chunk.file_id),
                        "project_id": str(project_id),
                    },
                )
            )
        return documents

    @staticmethod
    def _extract_queries_from_pitch(
        pitch: PitchParserOutput,
        *,
        fallback: str,
    ) -> list[str]:
        queries: list[str] = []
        for section in pitch.sections:
            if section.summary:
                queries.append(section.summary[:300])
            elif section.name:
                queries.append(section.name)
        if not queries:
            queries = [fallback, "market analysis", "competitors"]
        return queries[:8]

    @staticmethod
    def _compose_context_payload(
        market: MarketMapperOutput,
        web: WebScoutOutput,
    ) -> str:
        parts: list[str] = []
        for insight in market.insights:
            sources = ", ".join(insight.sources) if insight.sources else "knowledge-base"
            parts.append(
                f"[Market] {insight.topic}: {insight.summary} (источники: {sources})"
            )
        for finding in web.findings:
            parts.append(
                f"[Web] {finding.title}: {finding.snippet} (source: {finding.url})"
            )
        return "\n\n".join(parts).strip()

    @staticmethod
    def _format_report_message(report_payload: dict, context_payload: str | None) -> str:
        summary = report_payload.get("executive_summary", "")
        recommendations = report_payload.get("recommendations", []) or []
        rec_lines = []
        for recommendation in recommendations:
            title = recommendation.get("title", "Рекомендация")
            rationale = recommendation.get("rationale", "")
            rec_lines.append(f"- {title}: {rationale}")

        message_parts = ["Анализ документа завершён."]
        if summary:
            message_parts.append(summary)
        if rec_lines:
            message_parts.append("Рекомендации:\n" + "\n".join(rec_lines))
        return "\n\n".join(part for part in message_parts if part)

    @staticmethod
    def _summarise_chunks(project_name: str, chunks: Sequence[ContextChunk]) -> str:
        if not chunks:
            return (
                f"No contextual information is available for project '{project_name}'. "
                "Upload a pitch deck to unlock automated insights."
            )
        total_tokens = sum(len(chunk.content.split()) for chunk in chunks)
        return (
            f"Processed {len(chunks)} content chunks (≈{total_tokens} tokens) for project "
            f"'{project_name}'. These insights are now available for retrieval-augmented responses."
        )

    async def _compose_response_with_agent(
        self,
        *,
        message: str,
        context_chunks: list[dict[str, object]],
        context_summary: str | None = None,
        analysis_summary: str | None = None,
        message_history: list = None,
        project_name: str = "",
    ) -> str:
        """Генерирует ответ используя LangGraphAgent с полным контекстом."""
        # Lazy import to avoid circular dependency
        from src.agents import LangGraphAgent
        from langchain_core.messages import HumanMessage, AIMessage

        try:
            # Инициализируем агента
            agent = LangGraphAgent(
                model_name="gpt-4o-mini",
                system_prompt=(
                    "Ты - экспертный AI-ассистент для анализа проектов и презентаций. "
                    "Твоя задача - давать точные, подробные и таргетные ответы на основе предоставленного контекста. "
                    "Используй всю доступную информацию: анализ проекта, найденные документы, историю диалога. "
                    "Будь конкретным и полезным в своих ответах. "
                    "Отвечай на русском языке, если вопрос задан на русском."
                ),
            )

            # Формируем контекст из найденных чанков
            context_text = ""
            if context_chunks:
                context_lines = []
                for i, chunk in enumerate(context_chunks, 1):
                    score = chunk.get('score', 0.0)
                    content = chunk.get('content', '')
                    context_lines.append(f"Документ {i} (релевантность: {score:.2f}):\n{content}")
                context_text = "\n\n".join(context_lines)

            # Формируем полный контекст для промпта
            full_context_parts = []
            
            if analysis_summary:
                full_context_parts.append(f"АНАЛИЗ ПРОЕКТА:\n{analysis_summary}")
            
            if context_summary:
                full_context_parts.append(f"КОНТЕКСТНАЯ СВОДКА:\n{context_summary}")
            
            if context_text:
                full_context_parts.append(f"РЕЛЕВАНТНЫЕ ДОКУМЕНТЫ ИЗ БАЗЫ ЗНАНИЙ:\n{context_text}")
            
            full_context = "\n\n".join(full_context_parts) if full_context_parts else "Контекстная информация отсутствует."

            # Преобразуем историю сообщений в формат для LangGraphAgent
            message_history_formatted = []
            if message_history:
                for msg in message_history[-10:]:  # Берем последние 10 сообщений для контекста
                    if msg.role == MessageRole.USER:
                        message_history_formatted.append(HumanMessage(content=msg.content))
                    elif msg.role == MessageRole.ASSISTANT:
                        message_history_formatted.append(AIMessage(content=msg.content))

            # Формируем финальный промпт с контекстом
            enhanced_query = f"""Вопрос пользователя: {message}
                Доступный контекст:
                {full_context}

                Инструкция: Дай подробный и таргетный ответ на вопрос пользователя, используя всю предоставленную информацию из контекста. 
                - Если в контексте есть релевантная информация, используй её для формирования ответа
                - Будь конкретным и ссылайся на конкретные данные из анализа или документов
                - Если в контексте нет информации для ответа, честно скажи об этом
                - Отвечай на том же языке, на котором задан вопрос"""

            # Генерируем ответ
            result = agent.run(
                query=enhanced_query,
                context={
                    "project_name": project_name,
                    "has_analysis": bool(analysis_summary),
                    "has_context": bool(context_summary),
                    "chunks_count": len(context_chunks),
                },
                message_history=message_history_formatted,
            )

            return result.get("response", "Не удалось сгенерировать ответ.")
            
        except Exception as e:
            logger.exception("Failed to generate response with agent, falling back to simple response")
            # Fallback на простой ответ
            return self._compose_response_simple(
                message,
                context_chunks,
                context_summary=context_summary,
            )

    @staticmethod
    def _compose_response_simple(
        prompt: str,
        context: list[dict[str, object]],
        *,
        context_summary: str | None = None,
    ) -> str:
        """Простой метод генерации ответа без LLM (fallback)."""
        if context:
            context_lines = [
                f"- ({match.get('score', 0.0):.2f}) {match.get('content', '')}"
                for match in context
            ]
            context_block = "\n".join(context_lines)
            response = (
                f"Echo: {prompt}\n\n"
                f"Relevant context based on stored knowledge:\n{context_block}"
            )
        else:
            response = f"Echo: {prompt}"

        if context_summary:
            response += f"\n\nСводка отчёта:\n{context_summary}"
        return response


async def get_projects_service(
    session: AsyncSession = Depends(get_session),
) -> ProjectsService:
    vector_repo = VectorIndexRepository(redis_client, vector_index)
    ingestion_service = TextIngestionService()
    return ProjectsService(
        session,
        ingestion_service=ingestion_service,
        vector_repo=vector_repo,
    )


# Backwards-compatible import for AgentService usage
class ProjectService:
    def __init__(self, vector_repo: VectorIndexRepository) -> None:
        self._vector_repo = vector_repo

    async def resolve_project(
        self,
        repository: ProjectRepository,
        identifier: str | None,
    ) -> ProjectModel:
        if identifier:
            try:
                project_id = uuid.UUID(identifier)
            except ValueError:
                project = await repository.ensure(identifier, description=f"Project {identifier}")
            else:
                project = await repository.get(project_id)
                if project is None:
                    project = await repository.ensure(
                        identifier,
                        description=f"Project {identifier}",
                    )
        else:
            project = await repository.ensure(
                config.project.name,
                description=config.project.description,
            )
        return project

    async def create_file(
        self,
        repository: FileRepository,
        *,
        project_id: uuid.UUID,
        path: str,
        original_name: str | None = None,
        checksum: str | None = None,
    ) -> File:
        return await repository.create(
            project_id=project_id,
            path=path,
            original_name=original_name,
            checksum=checksum,
        )

    async def register_context_chunk(
        self,
        repository: ContextChunkRepository,
        *,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        chunk_index: int,
        content: str,
        embedding: list[float] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ContextChunk:
        await self._vector_repo.ensure_index()
        vector = embedding or build_embedding(content)
        chunk = await repository.create(
            project_id=project_id,
            file_id=file_id,
            chunk_index=chunk_index,
            content=content,
            embedding=vector,
        )
        await self._vector_repo.upsert_chunk(
            chunk_id=chunk.id,
            project_id=project_id,
            file_id=file_id,
            content=content,
            embedding=vector,
            metadata=metadata,
        )
        return chunk

    async def bulk_register_chunks(
        self,
        repository: ContextChunkRepository,
        *,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        chunks: Iterable[tuple[int, str, list[float] | None]],
    ) -> list[ContextChunk]:
        registered: list[ContextChunk] = []
        for chunk_index, content, embedding in chunks:
            registered.append(
                await self.register_context_chunk(
                    repository,
                    project_id=project_id,
                    file_id=file_id,
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
                )
            )
        return registered
