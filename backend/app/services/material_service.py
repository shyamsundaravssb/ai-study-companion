import uuid
from sqlalchemy.orm import Session
from app.models.material import Material, MaterialStatus
from app.models.job import Job, JobStatus

def create_material_and_job(
    db: Session, 
    project_id: uuid.UUID, 
    material_id: uuid.UUID,
    filename: str, 
    storage_path: str
) -> Material:
    material = Material(
        id=material_id,
        project_id=project_id,
        filename=filename,
        storage_path=storage_path,
        status=MaterialStatus.queued
    )
    db.add(material)
    db.flush()

    job = Job(
        job_type="process_material",
        payload={"material_id": str(material.id)},
        status=JobStatus.queued
    )
    db.add(job)
    db.commit()
    db.refresh(material)
    return material

def get_materials_by_project(db: Session, project_id: uuid.UUID) -> list[Material]:
    return db.query(Material).filter(Material.project_id == project_id).order_by(Material.uploaded_at.desc()).all()
