from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProjectCreateRequest(BaseModel):
    """Schema for project creation requests."""

    name: str = Field(..., description="Human readable project name")
    description: Optional[str] = Field(
        default=None,
        description="Optional project description or context",
    )


class ProjectUpdateRequest(BaseModel):
    """Schema for project update requests."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(
        ...,
        alias="id",
        description="Identifier of the project to update",
    )
    name: Optional[str] = Field(
        default=None,
        description="Updated project name",
    )
    description: Optional[str] = Field(
        default=None,
        description="Updated project description",
    )


class ProjectFile(BaseModel):
    """Metadata about a stored project file."""

    path: str = Field(..., description="Path of the stored file on the server")
    original_name: Optional[str] = Field(
        default=None,
        description="Original filename provided by the user during upload",
    )


class ProjectResponse(BaseModel):
    """Representation of project metadata returned to clients."""

    id: str
    name: str
    description: Optional[str] = None
    files: List[ProjectFile] = Field(default_factory=list)
    processed: bool = False
    analysis_summary: Optional[str] = None
    context_summary: Optional[str] = None
    rating: Optional[int] = Field(default=None, description="User submitted rating from 1 to 5")
    rating_comment: Optional[str] = Field(
        default=None,
        description="Optional textual feedback submitted with the rating",
    )
    history: List["ProjectMessage"] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    """List response wrapper for projects collection."""

    projects: List[ProjectResponse]


class ProjectFileUploadResponse(BaseModel):
    """Response returned after uploading a file to a project."""

    project: ProjectResponse
    filename: str
    stored_path: str
    original_name: Optional[str] = Field(
        default=None,
        description="Original filename persisted with the project",
    )


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


class ProjectRateRequest(BaseModel):
    """Schema for submitting a user rating for a project."""

    rating: int = Field(..., ge=1, le=5, description="Rating value from 1 to 5")
    comment: Optional[str] = Field(
        default=None,
        description="Optional feedback describing the rating",
        max_length=2000,
    )


# Models for agent outputs


class MarketInsight(BaseModel):
    """Market insight from market mapper agent."""

    topic: str
    summary: str
    sources: List[str] = Field(default_factory=list)


class MarketMapperOutput(BaseModel):
    """Output from market mapper agent."""

    insights: List[MarketInsight] = Field(default_factory=list)


class SlideModel(BaseModel):
    """Model representing a slide from a pitch deck."""

    index: int
    text: str


class PitchParserSection(BaseModel):
    """Section identified in a pitch deck."""

    name: str
    slides: List[int] = Field(default_factory=list)
    summary: str = ""


class PitchParserOutput(BaseModel):
    """Output from pitch parser agent."""

    slides: List[SlideModel] = Field(default_factory=list)
    sections: List[PitchParserSection] = Field(default_factory=list)


class WebFinding(BaseModel):
    """Web finding from web scout agent."""

    title: str
    url: str
    snippet: str


class WebScoutOutput(BaseModel):
    """Output from web scout agent."""

    findings: List[WebFinding] = Field(default_factory=list)


class ReportRecommendation(BaseModel):
    """Recommendation in a report."""

    title: str
    rationale: str


class ReportWriterOutput(BaseModel):
    """Output from report writer agent."""

    title: str
    executive_summary: str
    recommendations: List[ReportRecommendation] = Field(default_factory=list)
    appendix: dict = Field(default_factory=dict)


ProjectResponse.model_rebuild()
