import uuid
from fastapi import APIRouter, Depends
from app.models.project import Project
from app.api.deps import get_project_or_404
from app.schemas.quiz import AssessmentResponse
from app.services.quiz_service import generate_quiz_for_project

router = APIRouter()

@router.post("/generate", response_model=AssessmentResponse)
async def generate_quiz(
    project_id: uuid.UUID,
    project: Project = Depends(get_project_or_404)
):
    """
    Generates an adaptive quiz for a project based on concept mastery.
    """
    return await generate_quiz_for_project(project.id)
