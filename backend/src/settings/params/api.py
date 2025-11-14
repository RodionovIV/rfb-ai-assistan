from enum import StrEnum


class API(StrEnum):
    PREFIX = "/api/v1"
    DIALOG = "/dialog"
    HEALTH = "/health"
    PROJECTS = "/projects"
    PROJECTS_CREATE = "/projects/create"
    PROJECTS_UPLOAD = "/projects/{project_id}/upload"
    PROJECTS_PROCESS = "/projects/{project_id}/process"
    PROJECTS_DETAIL = "/projects/{project_id}"
    PROJECTS_CHAT = "/projects/{project_id}/chat"
