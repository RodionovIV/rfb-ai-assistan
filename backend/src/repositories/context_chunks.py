from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select

from src.database import ContextChunk

from .base import BaseRepository


class ContextChunkRepository(BaseRepository):
    async def get(self, chunk_id: uuid.UUID) -> ContextChunk | None:
        return await self.session.get(ContextChunk, chunk_id)

    async def list_by_file(self, file_id: uuid.UUID) -> Sequence[ContextChunk]:
        result = await self.session.execute(
            select(ContextChunk)
            .where(ContextChunk.file_id == file_id)
            .order_by(ContextChunk.chunk_index.asc())
        )
        return result.scalars().all()

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[ContextChunk]:
        result = await self.session.execute(
            select(ContextChunk)
            .where(ContextChunk.project_id == project_id)
            .order_by(ContextChunk.chunk_index.asc())
        )
        return result.scalars().all()

    async def create(
        self,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        chunk_index: int,
        content: str,
        embedding: list[float],
    ) -> ContextChunk:
        chunk = ContextChunk(
            project_id=project_id,
            file_id=file_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def delete(self, chunk_id: uuid.UUID) -> None:
        chunk = await self.get(chunk_id)
        if chunk is not None:
            await self.session.delete(chunk)
