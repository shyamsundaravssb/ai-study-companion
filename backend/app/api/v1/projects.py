import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_project_or_404
from app.models.project import Project
from app.schemas.project import ProjectUpdate, ProjectResponse
from app.services import project_service

router = APIRouter()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project: Project = Depends(get_project_or_404)
):
    """
    Returns a Project. The get_project_or_404 dependency handles all authorization.
    """
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_in: ProjectUpdate,
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db)
):
    """
    Updates a Project. The get_project_or_404 dependency handles all authorization.
    """
    return project_service.update_project(db=db, project=project, project_in=project_in)
