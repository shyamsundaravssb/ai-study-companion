import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_project_or_404, get_db
from app.models.project import Project
from app.models.assessment import Assessment
from app.schemas.assessment import AssessmentSubmitRequest, AssessmentSubmitResponse
from app.schemas.quiz import AssessmentResponse
from app.services.assessment_service import submit_assessment

router = APIRouter()

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    project_id: uuid.UUID,
    assessment_id: uuid.UUID,
    project: Project = Depends(get_project_or_404),
    db: Session = Depends(get_db)
):
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.project_id == project_id
    ).first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    return assessment

@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
async def submit_assessment_route(
    project_id: uuid.UUID,
    assessment_id: uuid.UUID,
    request: AssessmentSubmitRequest,
    project: Project = Depends(get_project_or_404)
):
    assessment = await submit_assessment(project.id, assessment_id, request)
    return AssessmentSubmitResponse(assessment=assessment)
