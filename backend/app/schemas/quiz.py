import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class QuizQuestionOption(BaseModel):
    text: str

class QuizQuestionGeneration(BaseModel):
    type: Literal["mcq", "open_ended"]
    concept_id: uuid.UUID
    prompt_text: str
    options: Optional[List[QuizQuestionOption]] = None
    correct_option_index: Optional[int] = None
    
class QuizGenerationResponse(BaseModel):
    questions: List[QuizQuestionGeneration]

# API Request/Response Models

class AssessmentQuestionResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    concept_id: Optional[uuid.UUID]
    question_text: str
    type: str
    options: Optional[list] = None
    user_answer: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AssessmentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    questions: List[AssessmentQuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)
