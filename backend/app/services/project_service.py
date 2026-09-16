import uuid
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

def create_project(db: Session, project_in: ProjectCreate, space_id: uuid.UUID) -> Project:
    project = Project(
        space_id=space_id,
        name=project_in.name,
        description=project_in.description,
        learning_goal=project_in.learning_goal
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def get_projects_by_space(db: Session, space_id: uuid.UUID) -> list[Project]:
    return db.query(Project).filter(Project.space_id == space_id).all()

def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project
