import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceUpdate, SpaceResponse
from app.schemas.project import ProjectResponse, ProjectCreate
from app.services import space_service, project_service

router = APIRouter()

@router.post("/", response_model=SpaceResponse, status_code=201)
def create_space(
    space_in: SpaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return space_service.create_space(db=db, space_in=space_in, user_id=current_user.id)

@router.get("/", response_model=list[SpaceResponse])
def get_spaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return space_service.get_spaces_by_user(db=db, user_id=current_user.id)

@router.get("/{space_id}", response_model=SpaceResponse)
def get_space(
    space_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    space = space_service.get_space(db=db, space_id=space_id, user_id=current_user.id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space

@router.patch("/{space_id}", response_model=SpaceResponse)
def update_space(
    space_id: uuid.UUID,
    space_in: SpaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    space = space_service.get_space(db=db, space_id=space_id, user_id=current_user.id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space_service.update_space(db=db, space=space, space_in=space_in)

@router.get("/{space_id}/projects", response_model=list[ProjectResponse])
def get_space_projects(
    space_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify space ownership
    space = space_service.get_space(db=db, space_id=space_id, user_id=current_user.id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return project_service.get_projects_by_space(db=db, space_id=space_id)

@router.post("/{space_id}/projects", response_model=ProjectResponse, status_code=201)
def create_project_in_space(
    space_id: uuid.UUID,
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify space ownership
    space = space_service.get_space(db=db, space_id=space_id, user_id=current_user.id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return project_service.create_project(db=db, project_in=project_in, space_id=space_id)
