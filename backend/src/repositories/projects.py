from __future__ import annotations

import uuid
from typing import Iterable, Sequence

from sqlalchemy import select

from src.database import Project

from .base import BaseRepository


class ProjectRepository(BaseRepository):
    async def list(self) -> Sequence[Project]:
        result = await self.session.execute(select(Project).order_by(Project.created_at.desc()))
        return result.scalars().all()

    async def get(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def get_by_name(self, name: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.name == name))
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None = None) -> Project:
        project = Project(name=name, description=description)
        self.session.add(project)
        await self.session.flush()
        return project

    async def ensure(self, name: str, description: str | None = None) -> Project:
        project = await self.get_by_name(name)
        if project is not None:
            return project
        return await self.create(name=name, description=description)

    async def delete(self, project_id: uuid.UUID) -> None:
        project = await self.get(project_id)
        if project is not None:
            await self.session.delete(project)

    async def update(
        self,
        project_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        rating: int | None = None,
        rating_comment: str | None = None,
    ) -> Project | None:
        project = await self.get(project_id)
        if project is None:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if rating is not None:
            project.rating = rating
        if rating_comment is not None:
            project.rating_comment = rating_comment
        await self.session.flush()
        return project

    async def bulk_create(self, projects: Iterable[tuple[str, str | None]]) -> list[Project]:
        created: list[Project] = []
        for name, description in projects:
            created.append(await self.create(name=name, description=description))
        return created
