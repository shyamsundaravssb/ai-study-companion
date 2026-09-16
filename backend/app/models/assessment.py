import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class AssessmentType(str, enum.Enum):
    quiz = "quiz"
    open_ended = "open_ended"

class AssessmentStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"

class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType))
    status: Mapped[AssessmentStatus] = mapped_column(Enum(AssessmentStatus), default=AssessmentStatus.in_progress)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Assessment {self.id}>"
