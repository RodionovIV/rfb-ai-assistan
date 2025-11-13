from enum import StrEnum


class API(StrEnum):
    PREFIX = "/api/v1"
    DIALOG = "/dialog"
    HEALTH = "/health"
    PROJECT_PROCESS = "/projects/{project_id}/process"