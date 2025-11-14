from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select

from src.database import File

from .base import BaseRepository


class FileRepository(BaseRepository):
    async def get(self, file_id: uuid.UUID) -> File | None:
        return await self.session.get(File, file_id)

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[File]:
        result = await self.session.execute(
            select(File).where(File.project_id == project_id).order_by(File.created_at.desc())
        )
        return result.scalars().all()

    async def create(
        self,
        project_id: uuid.UUID,
        path: str,
        checksum: str | None = None,
    ) -> File:
        file = File(project_id=project_id, path=path, checksum=checksum)
        self.session.add(file)
        await self.session.flush()
        return file

    async def delete(self, file_id: uuid.UUID) -> None:
        file = await self.get(file_id)
        if file is not None:
            await self.session.delete(file)
