from __future__ import annotations

import inspect
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

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
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="messages")


engine: AsyncEngine = create_async_engine(config.database.dsn, echo=config.database.echo)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


redis_client = redis_async.from_url(
    config.redis.url,
    decode_responses=config.redis.decode_responses,
)


VECTOR_INDEX_SCHEMA = IndexSchema.from_dict(
    {
        "name": config.vector_index.name,
        "prefix": config.vector_index.prefix,
        "storage_type": "hash",
        "fields": [
            {"name": "chunk_id", "type": "tag"},
            {"name": "project_id", "type": "tag"},
            {"name": "file_id", "type": "tag"},
            {"name": "content", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": config.vector_index.dimension,
                    "distance_metric": config.vector_index.distance_metric,
                    "algorithm": config.vector_index.algorithm,
                },
            },
        ],
    }
)
vector_index = SearchIndex(schema=VECTOR_INDEX_SCHEMA, redis_client=redis_client)


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
