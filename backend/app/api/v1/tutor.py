import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_project_or_404
from app.models.project import Project
from app.schemas.tutor import ConversationResponse, MessageCreate, MessageResponse
from app.services.tutor_service import TutorService

router = APIRouter()

@router.post("/projects/{project_id}/tutor/conversations", response_model=ConversationResponse)
def create_conversation(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_or_404)
):
    """
    Creates a new tutor conversation for the project.
    """
    conv = TutorService.create_conversation(db, project_id=project.id)
    return conv

@router.get("/projects/{project_id}/tutor/conversations/{conv_id}", response_model=ConversationResponse)
def get_conversation(
    project_id: uuid.UUID,
    conv_id: uuid.UUID,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_or_404)
):
    """
    Gets conversation history.
    """
    conv = TutorService.get_conversation(db, project.id, conv_id)
    return conv

@router.post("/projects/{project_id}/tutor/conversations/{conv_id}/messages", response_model=MessageResponse)
async def chat_message(
    project_id: uuid.UUID,
    conv_id: uuid.UUID,
    msg_in: MessageCreate,
    db: Session = Depends(get_db),
    project: Project = Depends(get_project_or_404)
):
    """
    Sends a message to the AI tutor and returns the response.
    """
    assistant_msg = await TutorService.chat_in_conversation(
        db=db,
        project_id=project.id,
        conv_id=conv_id,
        user_message=msg_in.content
    )
    return assistant_msg
