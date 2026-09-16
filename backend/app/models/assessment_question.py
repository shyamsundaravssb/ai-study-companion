import enum
import uuid
from sqlalchemy import Text, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class QuestionType(str, enum.Enum):
    mcq = "mcq"
    open_ended = "open_ended"

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    concept_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("concepts.id", ondelete="SET NULL"))
    question_text: Mapped[str] = mapped_column(Text)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType))
    options = mapped_column(JSONB, nullable=True)
    correct_answer_or_rubric: Mapped[str] = mapped_column(Text)
    user_answer: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)

    assessment = relationship("Assessment", back_populates="questions")

    def __repr__(self) -> str:
        return f"<AssessmentQuestion {self.id}>"
