from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select

from src.database import Report

from .base import BaseRepository


class ReportRepository(BaseRepository):
    async def get(self, report_id: uuid.UUID) -> Report | None:
        return await self.session.get(Report, report_id)

    async def list_by_project(self, project_id: uuid.UUID) -> Sequence[Report]:
        result = await self.session.execute(
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
        )
        return result.scalars().all()

    async def create(
        self,
        project_id: uuid.UUID,
        title: str,
        content: str,
        context: str | None = None,
    ) -> Report:
        report = Report(
            project_id=project_id,
            title=title,
            content=content,
            context=context,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def delete(self, report_id: uuid.UUID) -> None:
        report = await self.get(report_id)
        if report is not None:
            await self.session.delete(report)
