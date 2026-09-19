import uuid
import json
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.models.assessment import Assessment, AssessmentType, AssessmentStatus
from app.models.assessment_question import AssessmentQuestion, QuestionType
from app.ai.graphs.quiz_graph import quiz_app

async def generate_quiz_for_project(project_id: uuid.UUID) -> Assessment:
    db = SessionLocal()
    try:
        # Run graph
        state = {"project_id": project_id, "retry_count": 0}
        
        try:
            result = await quiz_app.ainvoke(state)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
            
        parsed_quiz = result.get("parsed_quiz")
        if not parsed_quiz:
            raise HTTPException(status_code=502, detail="Failed to generate valid assessment output from AI after retries.")
            
        # Create Assessment
        assessment = Assessment(
            project_id=project_id,
            type=AssessmentType.quiz,
            status=AssessmentStatus.in_progress
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        
        # Add Questions
        for q_data in parsed_quiz.get("questions", []):
            question_type = QuestionType.mcq if q_data["type"] == "mcq" else QuestionType.open_ended
            
            options_json = None
            correct_answer = ""
            
            if question_type == QuestionType.mcq:
                options_list = [{"text": o["text"]} for o in q_data.get("options", [])]
                options_json = options_list
                idx = q_data.get("correct_option_index")
                if idx is not None and 0 <= idx < len(options_list):
                    correct_answer = options_list[idx]["text"]
            
            question = AssessmentQuestion(
                assessment_id=assessment.id,
                concept_id=uuid.UUID(str(q_data["concept_id"])),
                question_text=q_data["prompt_text"],
                type=question_type,
                options=options_json,
                correct_answer_or_rubric=correct_answer
            )
            db.add(question)
            
        db.commit()
        db.refresh(assessment)
        return assessment
    finally:
        db.close()
