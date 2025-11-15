from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select

from src.database import Message, MessageRole

from .base import BaseRepository


class MessageRepository(BaseRepository):
    async def get(self, message_id: uuid.UUID) -> Message | None:
        return await self.session.get(Message, message_id)

    async def list_by_project(self, project_id: uuid.UUID, limit: int = 50) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.project_id == project_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create(
        self,
        project_id: uuid.UUID,
        role: MessageRole,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> Message:
        message = Message(
            project_id=project_id,
            role=role,
            content=content,
            metadata_=metadata,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def delete(self, message_id: uuid.UUID) -> None:
        message = await self.get(message_id)
        if message is not None:
            await self.session.delete(message)
