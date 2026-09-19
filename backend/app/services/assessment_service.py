import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentStatus
from app.models.assessment_question import QuestionType
from app.models.project import Project
from app.models.event import Event
from app.schemas.assessment import AssessmentSubmitRequest
from app.ai.graphs.grading_graph import grading_app
from app.services.mastery_service import process_assessment_completed_event_inline

async def submit_assessment(project_id: uuid.UUID, assessment_id: uuid.UUID, request: AssessmentSubmitRequest) -> Assessment:
    db = SessionLocal()
    try:
        assessment = db.query(Assessment).filter(
            Assessment.id == assessment_id, 
            Assessment.project_id == project_id
        ).first()
        
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
            
        if assessment.status == AssessmentStatus.completed:
            raise HTTPException(status_code=400, detail="Assessment already completed")
            
        answer_map = {str(ans.question_id): ans.answer for ans in request.answers}
        
        for question in assessment.questions:
            user_answer = answer_map.get(str(question.id))
            if not user_answer:
                continue
                
            question.user_answer = user_answer
            
            if question.type == QuestionType.mcq:
                # Deterministic grading
                is_correct = user_answer.strip().lower() == question.correct_answer_or_rubric.strip().lower()
                question.score = 1.0 if is_correct else 0.0
                question.feedback = "Correct" if is_correct else f"Incorrect. The correct answer was: {question.correct_answer_or_rubric}"
            else:
                # Open-ended grading via LLM
                state = {
                    "project_id": project_id,
                    "question_text": question.question_text,
                    "user_answer": user_answer,
                    "concept_id": question.concept_id,
                    "retry_count": 0
                }
                
                try:
                    result = await grading_app.ainvoke(state)
                except RuntimeError as e:
                    raise HTTPException(status_code=502, detail=str(e))
                    
                parsed = result.get("parsed_grading")
                if not parsed:
                    raise HTTPException(status_code=502, detail="Failed to generate valid grading output from AI after retries.")
                    
                question.score = parsed.get("understanding_score", 0.0) # Using understanding as main score, accuracy can be averaged or documented
                
                feedback = parsed.get("feedback_text", "")
                missing = parsed.get("missing_concepts", [])
                if missing:
                    feedback += f"\n\nMissing concepts: {', '.join(missing)}"
                    
                question.feedback = feedback
                
        assessment.status = AssessmentStatus.completed
        assessment.completed_at = datetime.now(timezone.utc)
        
        # Calculate concept results
        concept_results = {}
        for question in assessment.questions:
            if question.score is not None:
                concept_id_str = str(question.concept_id)
                if concept_id_str not in concept_results:
                    concept_results[concept_id_str] = []
                concept_results[concept_id_str].append(question.score)
                
        # Average the scores per concept
        averaged_results = {
            cid: sum(scores) / len(scores) 
            for cid, scores in concept_results.items()
        }
        
        payload = {
            "project_id": str(project_id),
            "assessment_id": str(assessment_id),
            "concept_results": averaged_results
        }
        
        project = db.query(Project).filter(Project.id == project_id).first()
        
        event = Event(
            project_id=project_id,
            user_id=project.space.user_id if project and project.space else None,
            event_type="assessment_completed",
            payload=payload,
            idempotency_key=f"assessment_completed_{assessment_id}"
        )
        db.add(event)
        
        db.commit()
        db.refresh(assessment)
        db.refresh(event)
        
        # Process mastery updates inline using the event we just created
        process_assessment_completed_event_inline(db, event.id)
        
        return assessment
        
    finally:
        db.close()
