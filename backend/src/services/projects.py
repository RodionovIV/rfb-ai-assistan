from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Tuple
from uuid import uuid4

from fastapi import UploadFile


class ProjectNotFoundError(Exception):
    """Raised when the requested project does not exist."""


@dataclass
class ProjectMessage:
    role: str
    content: str


@dataclass
class Project:
    id: str
    name: str
    description: str | None = None
    files: List[str] = field(default_factory=list)
    processed: bool = False
    analysis_summary: str | None = None
    history: List[ProjectMessage] = field(default_factory=list)


class ProjectsService:
    """In-memory projects service with simple file persistence."""

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._projects: Dict[str, Project] = {}

    def create_project(self, name: str, description: str | None = None) -> Project:
        project_id = uuid4().hex
        project = Project(id=project_id, name=name, description=description)
        self._projects[project_id] = project
        (self._storage_dir / project_id).mkdir(parents=True, exist_ok=True)
        return project

    def list_projects(self) -> List[Project]:
        return list(self._projects.values())

    def get_project(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ProjectNotFoundError(project_id) from exc

    def delete_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        del self._projects[project_id]
        project_dir = self._storage_dir / project_id
        if project_dir.exists():
            rmtree(project_dir)
        return project

    def upload_file(self, project_id: str, file: UploadFile) -> Tuple[Project, Path]:
        project = self.get_project(project_id)
        project_dir = self._storage_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        target_path = project_dir / file.filename
        file.file.seek(0)
        with target_path.open("wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
        file.file.close()

        if file.filename not in project.files:
            project.files.append(file.filename)
        return project, target_path

    def process_project(self, project_id: str) -> Tuple[Project, str]:
        project = self.get_project(project_id)
        summary = self._generate_summary(project)
        project.processed = True
        project.analysis_summary = summary
        return project, summary

    def add_message(self, project_id: str, message: str) -> Tuple[Project, ProjectMessage, List[ProjectMessage]]:
        project = self.get_project(project_id)
        user_entry = ProjectMessage(role="user", content=message)
        assistant_entry = ProjectMessage(role="assistant", content=self._build_reply(project, message))
        project.history.extend([user_entry, assistant_entry])
        return project, assistant_entry, list(project.history)

    @staticmethod
    def serialize_project(project: Project) -> Dict:
        return asdict(project)

    def _generate_summary(self, project: Project) -> str:
        if not project.files:
            return "No files uploaded yet."
        file_list = ", ".join(project.files)
        return f"Processed {len(project.files)} file(s): {file_list}."

    def _build_reply(self, project: Project, message: str) -> str:
        context = project.analysis_summary or "analysis is not available yet"
        return (
            "Project '{name}' heard: '{message}'. Last analysis summary: {summary}."
        ).format(name=project.name, message=message, summary=context)


@lru_cache()
def get_projects_service() -> ProjectsService:
    base_dir = Path(__file__).resolve().parents[2] / "data" / "projects"
    return ProjectsService(base_dir)
