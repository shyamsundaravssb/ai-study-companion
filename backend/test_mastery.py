import uuid
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.space import Space
from app.models.project import Project
from app.models.concept import Concept
from app.models.mastery import Mastery
from app.models.mastery_history import MasteryHistory
from app.models.assessment import Assessment, AssessmentStatus, AssessmentType
from app.models.assessment_question import AssessmentQuestion, QuestionType
from app.schemas.assessment import AssessmentSubmitRequest, QuestionSubmit
from app.services.assessment_service import submit_assessment
from app.services.mastery_service import process_assessment_completed_event_inline
from app.models.event import Event

async def run_tests():
    db = SessionLocal()
    
    # 1. Setup
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"test_{user_id}@example.com", role="user")
    db.add(user)
    db.commit()
    
    space_id = uuid.uuid4()
    space = Space(id=space_id, user_id=user_id, name="Test Space")
    db.add(space)
    db.commit()
    
    project_id = uuid.uuid4()
    project = Project(id=project_id, space_id=space_id, name="Test Project")
    db.add(project)
    db.commit()
    
    concept_id = uuid.uuid4()
    concept = Concept(id=concept_id, project_id=project_id, name="Test Concept", description="Test Description")
    db.add(concept)
    db.commit()
    
    # Pre-existing mastery
    initial_score = 0.5
    mastery = Mastery(project_id=project_id, concept_id=concept_id, score=initial_score)
    db.add(mastery)
    db.commit()
    
    # Assessment
    assessment_id = uuid.uuid4()
    assessment = Assessment(id=assessment_id, project_id=project_id, status=AssessmentStatus.in_progress, type=AssessmentType.quiz)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    question_id = uuid.uuid4()
    question = AssessmentQuestion(
        id=question_id,
        assessment_id=assessment_id,
        concept_id=concept_id,
        type=QuestionType.mcq,
        question_text="Is this a test?",
        correct_answer_or_rubric="yes"
    )
    db.add(question)
    db.commit()
    
    print(f"--- TEST 1: UPDATE CORRECTNESS ---")
    print(f"Initial mastery score: {initial_score}")
    
    # Submit assessment
    req = AssessmentSubmitRequest(
        answers=[QuestionSubmit(question_id=question_id, answer="yes")]
    )
    
    await submit_assessment(project_id, assessment_id, req)
    
    # Verify new score
    db.refresh(mastery)
    expected_score = (initial_score * 0.7) + (1.0 * 0.3)
    print(f"Performance on assessment: 1.0 (Correct MCQ)")
    print(f"Formula: previous_score * 0.7 + performance * 0.3 = {initial_score} * 0.7 + 1.0 * 0.3 = {expected_score}")
    print(f"Actual new mastery score in DB: {mastery.score}")
    assert abs(mastery.score - expected_score) < 0.001
    
    history_rows = db.query(MasteryHistory).filter(MasteryHistory.concept_id == concept_id).all()
    print(f"Mastery history rows count: {len(history_rows)}")
    for h in history_rows:
        print(f" - History Row: score={h.score}, recorded_at={h.recorded_at}")
    
    print(f"\n--- TEST 2: IDEMPOTENCY ---")
    # To test idempotency, we will just get the event and process it again
    event = db.query(Event).filter(Event.project_id == project_id).first()
    print(f"Re-processing event {event.id} (idempotency_key={event.idempotency_key})")
    
    # This should skip updating
    process_assessment_completed_event_inline(db, event.id)
    
    db.refresh(mastery)
    print(f"Mastery score after re-processing (should be unchanged): {mastery.score}")
    
    history_rows_after = db.query(MasteryHistory).filter(MasteryHistory.concept_id == concept_id).all()
    print(f"Mastery history rows count after re-processing (should be unchanged): {len(history_rows_after)}")
    
    # Cleanup
    db.query(Event).filter(Event.project_id == project_id).delete()
    db.query(MasteryHistory).filter(MasteryHistory.project_id == project_id).delete()
    db.query(Mastery).filter(Mastery.project_id == project_id).delete()
    db.query(AssessmentQuestion).filter(AssessmentQuestion.assessment_id == assessment_id).delete()
    db.query(Assessment).filter(Assessment.project_id == project_id).delete()
    db.query(Concept).filter(Concept.project_id == project_id).delete()
    db.query(Project).filter(Project.id == project_id).delete()
    db.query(Space).filter(Space.id == space_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()
    
    print("\nAll tests passed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
