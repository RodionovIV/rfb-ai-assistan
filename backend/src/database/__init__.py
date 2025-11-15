from __future__ import annotations

import inspect
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from typing import Any

from redis import Redis as RedisSync
from redis import asyncio as redis_async
from redis.exceptions import ResponseError
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.settings.general import config


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list["File"]] = relationship("File", back_populates="project", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="project", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="project", cascade="all, delete-orphan")


class File(Base, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="files")
    context_chunks: Mapped[list["ContextChunk"]] = relationship(
        "ContextChunk", back_populates="file", cascade="all, delete-orphan"
    )


class ContextChunk(Base, TimestampMixin):
    __tablename__ = "context_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSONB, nullable=False)

    file: Mapped[File] = relationship("File", back_populates="context_chunks")
    project: Mapped[Project] = relationship("Project")


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[Project] = relationship("Project", back_populates="reports")


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    project: Mapped[Project] = relationship("Project", back_populates="messages")


engine: AsyncEngine = create_async_engine(config.database.dsn, echo=config.database.echo)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


redis_client = redis_async.from_url(
    config.redis.url,
    decode_responses=config.redis.decode_responses,
)

# ``redisvl`` still performs synchronous operations when creating indexes,
# particularly when calling ``SearchIndex.exists`` which internally invokes
# ``FT._LIST`` without awaiting the coroutine returned by an asynchronous
# Redis client. To keep the rest of the application asynchronous while letting
# ``SearchIndex`` function correctly, we provide it with a dedicated
# synchronous Redis connection.
def _patch_sync_redis_for_search_index(client: RedisSync) -> RedisSync:
    """Ensure redisvl can fall back to ``FT.LIST`` when ``FT._LIST`` is missing."""

    original_execute_command = client.execute_command

    def execute_command_with_compat(*args: Any, **kwargs: Any):  # type: ignore[override]
        command = args[0] if args else None
        try:
            return original_execute_command(*args, **kwargs)
        except ResponseError as exc:
            if (
                isinstance(command, str)
                and command.upper() == "FT._LIST"
                and "unknown command" in str(exc).lower()
            ):
                return original_execute_command("FT.LIST", *args[1:], **kwargs)
            raise

    client.execute_command = execute_command_with_compat  # type: ignore[assignment]
    return client


redis_sync_client = _patch_sync_redis_for_search_index(
    RedisSync.from_url(
        config.redis.url,
        decode_responses=config.redis.decode_responses,
    )
)


_VECTOR_INDEX_NAME = config.vector_index.name or "context-chunks-index"
_VECTOR_INDEX_PREFIX = config.vector_index.prefix or "chunk"
_VECTOR_INDEX_DIMENSION = config.vector_index.dimension or 1536
_VECTOR_INDEX_DISTANCE = config.vector_index.distance_metric or "cosine"
_VECTOR_INDEX_ALGORITHM = config.vector_index.algorithm or "HNSW"
VECTOR_INDEX_SCHEMA = IndexSchema.from_dict(
    {
        "index": {
            "name": _VECTOR_INDEX_NAME,
            "prefix": [_VECTOR_INDEX_PREFIX],
            "storage_type": "hash",
        },
        "fields": [
            {"name": "chunk_id", "type": "tag"},
            {"name": "project_id", "type": "tag"},
            {"name": "file_id", "type": "tag"},
            {"name": "content", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": _VECTOR_INDEX_DIMENSION,
                    "distance_metric": _VECTOR_INDEX_DISTANCE,
                    "algorithm": _VECTOR_INDEX_ALGORITHM,
                },
            },
        ],
    }
)
vector_index = SearchIndex(schema=VECTOR_INDEX_SCHEMA, redis_client=redis_sync_client)


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_vector_index(overwrite: bool = False) -> None:
    try:
        result = vector_index.create(overwrite=overwrite)
        if inspect.isawaitable(result):
            await result  # type: ignore[misc]
    except ResponseError as exc:  # pragma: no cover - requires Redis server
        if overwrite:
            raise
        message = str(exc).lower()
        if "exists" not in message:
            raise


__all__ = [
    "AsyncSession",
    "ContextChunk",
    "File",
    "Message",
    "MessageRole",
    "Project",
    "Report",
    "async_session_factory",
    "engine",
    "get_session",
    "init_models",
    "init_vector_index",
    "redis_client",
    "vector_index",
]
