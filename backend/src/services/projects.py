from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.services.ingestion import IngestionResult, TextIngestionService
from src.services.utils import build_embedding
from src.settings.general import config


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
class Project:
    id: str
    name: str
    description: str | None
    files: list[str] = field(default_factory=list)
    processed: bool = False
    analysis_summary: str | None = None
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
        )

        await self._register_slides(project_id=project.id, file=file_record, ingestion=ingestion)
        await self._session.commit()

        project_model = await self._projects.get(project.id)
        assert project_model is not None  # for type checkers
        return await self._build_project(project_model), ingestion.stored_path

    async def process_project(self, project_id: str) -> tuple[Project, str]:
        project = await self._get_project_or_raise(project_id)
        chunks = await self._chunks.list_by_project(project.id)
        summary = self._summarise_chunks(project.name, chunks)
        await self._reports.create(
            project_id=project.id,
            title=f"Analysis for {project.name}",
            content=summary,
        )
        await self._session.commit()
        return await self.get_project(project_id), summary

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

        embedding = build_embedding(message)
        context = await self._vector_repo.search_similar(embedding, limit=3)
        reply_content = self._compose_response(message, context)

        await self._messages.create(
            project_id=project.id,
            role=MessageRole.ASSISTANT,
            content=reply_content,
            metadata={
                "related_chunks": [item.get("chunk_id") for item in context],
                "source": "knowledge-base",
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
        return Project(
            id=str(project.id),
            name=project.name,
            description=project.description,
            files=[file.path for file in files],
            processed=bool(reports),
            analysis_summary=analysis_summary,
            history=history,
        )

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

    @staticmethod
    def _compose_response(prompt: str, context: list[dict[str, object]]) -> str:
        if not context:
            return f"Echo: {prompt}"
        context_lines = [
            f"- ({match.get('score', 0.0):.2f}) {match.get('content', '')}"
            for match in context
        ]
        context_block = "\n".join(context_lines)
        return (
            f"Echo: {prompt}\n\n"
            f"Relevant context based on stored knowledge:\n{context_block}"
        )


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
        checksum: str | None = None,
    ) -> File:
        return await repository.create(project_id=project_id, path=path, checksum=checksum)

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
