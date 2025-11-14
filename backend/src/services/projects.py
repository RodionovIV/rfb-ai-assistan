from __future__ import annotations

import uuid
from typing import Iterable

from src.database import ContextChunk, File, Project
from src.repositories import (
    ContextChunkRepository,
    FileRepository,
    ProjectRepository,
    VectorIndexRepository,
)
from src.settings.general import config

from .utils import build_embedding


class ProjectService:
    def __init__(self, vector_repo: VectorIndexRepository) -> None:
        self._vector_repo = vector_repo

    async def resolve_project(
        self,
        repository: ProjectRepository,
        identifier: str | None,
    ) -> Project:
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
