import uuid
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.quiz import AssessmentResponse

class GradingOutput(BaseModel):
    understanding_score: float  # e.g., 0.0 to 1.0
    accuracy_score: float       # e.g., 0.0 to 1.0
    missing_concepts: List[str]
    feedback_text: str

class QuestionSubmit(BaseModel):
    question_id: uuid.UUID
    answer: str

class AssessmentSubmitRequest(BaseModel):
    answers: List[QuestionSubmit]

class AssessmentSubmitResponse(BaseModel):
    assessment: AssessmentResponse
