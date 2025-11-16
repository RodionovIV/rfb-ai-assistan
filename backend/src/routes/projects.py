from __future__ import annotations

from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.projects import (
    ProjectChatRequest,
    ProjectChatResponse,
    ProjectCreateRequest,
    ProjectFileUploadResponse,
    ProjectListResponse,
    ProjectMessage,
    ProjectProcessResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from src.routes.router import base_router
from src.settings.params.api import API
from src.services.projects import (
    ProjectNotFoundError,
    Project as ServiceProject,
    ProjectMessage as ServiceProjectMessage,
    ProjectsService,
    get_projects_service,
)

router = APIRouter(prefix=API.PROJECTS, tags=["projects"])


def _to_message(message: ServiceProjectMessage) -> ProjectMessage:
    return ProjectMessage(**asdict(message))


def _to_response(project: ServiceProject) -> ProjectResponse:
    payload = asdict(project)
    payload["history"] = [_to_message(msg) for msg in project.history]
    return ProjectResponse(**payload)


@router.post("/create", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectResponse:
    project = await service.create_project(name=request.name, description=request.description)
    return _to_response(project)


@router.post("/update", response_model=ProjectResponse)
async def update_project(
    request: ProjectUpdateRequest,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectResponse:
    if request.name is None and request.description is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided",
        )
    try:
        project = await service.update_project(
            project_id=request.project_id,
            name=request.name,
            description=request.description,
        )
    except ProjectNotFoundError as exc:  # pragma: no cover - FastAPI handles raising
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return _to_response(project)


@router.post("/{project_id}/upload", response_model=ProjectFileUploadResponse)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectFileUploadResponse:
    try:
        project, stored_path = await service.upload_file(project_id=project_id, file=file)
    except ProjectNotFoundError as exc:  # pragma: no cover - FastAPI handles raising
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return ProjectFileUploadResponse(
        project=_to_response(project),
        filename=file.filename,
        stored_path=str(stored_path),
        original_name=file.filename,
    )


@router.post("/{project_id}/process", response_model=ProjectProcessResponse)
async def process_project(
    project_id: str,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectProcessResponse:
    try:
        project, summary = await service.process_project(project_id=project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return ProjectProcessResponse(project_id=project.id, status="processed", details=summary)


@router.get("", response_model=ProjectListResponse)
async def list_projects(service: ProjectsService = Depends(get_projects_service)) -> ProjectListResponse:
    projects = await service.list_projects()
    return ProjectListResponse(projects=[_to_response(project) for project in projects])


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectResponse:
    try:
        project = await service.get_project(project_id=project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return _to_response(project)


@router.delete("/{project_id}", response_model=ProjectResponse)
async def delete_project(
    project_id: str,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectResponse:
    try:
        project = await service.delete_project(project_id=project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    return _to_response(project)


@router.post("/{project_id}/chat", response_model=ProjectChatResponse)
async def project_chat(
    project_id: str,
    request: ProjectChatRequest,
    service: ProjectsService = Depends(get_projects_service),
) -> ProjectChatResponse:
    try:
        project, reply, history = await service.add_message(project_id=project_id, message=request.message)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc

    reply_model = _to_message(reply)
    history_models: List[ProjectMessage] = [_to_message(message) for message in history]

    return ProjectChatResponse(project=_to_response(project), reply=reply_model, history=history_models)


base_router.include_router(router)
