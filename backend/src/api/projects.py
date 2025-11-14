from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    """Schema for project creation requests."""

    name: str = Field(..., description="Human readable project name")
    description: Optional[str] = Field(
        default=None,
        description="Optional project description or context",
    )


class ProjectResponse(BaseModel):
    """Representation of project metadata returned to clients."""

    id: str
    name: str
    description: Optional[str] = None
    files: List[str] = Field(default_factory=list)
    processed: bool = False
    analysis_summary: Optional[str] = None
    history: List["ProjectMessage"] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    """List response wrapper for projects collection."""

    projects: List[ProjectResponse]


class ProjectFileUploadResponse(BaseModel):
    """Response returned after uploading a file to a project."""

    project: ProjectResponse
    filename: str
    stored_path: str


class ProjectProcessResponse(BaseModel):
    """Response returned after a project processing request."""

    project_id: str
    status: str
    details: str


class ProjectChatRequest(BaseModel):
    """Schema for chat messages sent by the user."""

    message: str


class ProjectMessage(BaseModel):
    """Single chat message entry."""

    role: str = Field(..., description="Role of the author of the message, e.g. user or assistant")
    content: str


class ProjectChatResponse(BaseModel):
    """Response returned after interacting with the project chat assistant."""

    project: ProjectResponse
    reply: ProjectMessage
    history: List[ProjectMessage]


ProjectResponse.model_rebuild()
