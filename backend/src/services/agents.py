from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import MessageRole, async_session_factory, redis_client, vector_index
from src.repositories import MessageRepository, ProjectRepository, VectorIndexRepository

from .projects import ProjectService
from .utils import build_embedding


SessionFactory = Callable[[], AsyncSession]


class AgentService:
    def __init__(
        self,
        *,
        session_factory: SessionFactory = async_session_factory,
        vector_repo: VectorIndexRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._vector_repo = vector_repo or VectorIndexRepository(redis_client, vector_index)
        self._project_service = ProjectService(self._vector_repo)

    async def process_dialog(self, conversation_id: str, content: str) -> dict[str, Any]:
        await self._vector_repo.ensure_index()
        async with self._session_factory() as session:
            project_repo = ProjectRepository(session)
            message_repo = MessageRepository(session)

            project = await self._project_service.resolve_project(project_repo, conversation_id or None)
            user_message = await message_repo.create(
                project_id=project.id,
                role=MessageRole.USER,
                content=content,
            )

            embedding = build_embedding(content)
            context = await self._vector_repo.search_similar(embedding, limit=3)
            response_content = self._compose_response(content, context)

            assistant_message = await message_repo.create(
                project_id=project.id,
                role=MessageRole.ASSISTANT,
                content=response_content,
                metadata={
                    "related_chunks": [item.get("chunk_id") for item in context],
                    "source": "knowledge-base",
                },
            )

            await session.commit()

            project_id = str(project.id)
            user_message_id = str(user_message.id)
            assistant_message_id = str(assistant_message.id)

        return {
            "project_id": project_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "response": response_content,
            "context": context,
        }

    def _compose_response(self, prompt: str, context: list[dict[str, Any]]) -> str:
        if not context:
            return f"Echo: {prompt}"
        context_lines = [
            f"- ({match['score']:.2f}) {match.get('content', '')}"
            for match in context
        ]
        context_block = "\n".join(context_lines)
        return (
            f"Echo: {prompt}\n\n"
            f"Relevant context based on stored knowledge:\n{context_block}"
        )
