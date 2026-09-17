import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_project_or_404
from app.models.project import Project
from app.schemas.material import MaterialResponse
from app.services import material_service, storage_service

router = APIRouter()

@router.post("/{project_id}/materials", response_model=MaterialResponse, status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    file_bytes = await file.read()
    
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")
        
    material_id = uuid.uuid4()
    
    try:
        storage_path = storage_service.upload_material(
            project_id=project.id,
            material_id=material_id,
            filename=file.filename or "upload.pdf",
            file_content=file_bytes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to storage: {str(e)}")
        
    material = material_service.create_material_and_job(
        db=db,
        project_id=project.id,
        material_id=material_id,
        filename=file.filename or "upload.pdf",
        storage_path=storage_path
    )
    
    return material

@router.get("/{project_id}/materials", response_model=list[MaterialResponse])
def get_materials(
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db)
):
    return material_service.get_materials_by_project(db=db, project_id=project.id)
