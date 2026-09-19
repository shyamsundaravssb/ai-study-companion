import asyncio
import uuid
import sys
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.concept import Concept
from app.models.mastery import Mastery
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.services.quiz_service import generate_quiz_for_project
from app.services.assessment_service import submit_assessment
from app.schemas.assessment import AssessmentSubmitRequest, QuestionSubmit

async def main():
    db = SessionLocal()
    # Find a project
    project = db.query(Project).first()
    if not project:
        print("No projects found.")
        return
        
    print(f"Testing on project: {project.id}")
    
    # 1. Setup exact 3 concepts
    print("\n--- SETTING UP CONCEPTS ---")
    db.query(Mastery).filter(Mastery.project_id == project.id).delete()
    db.query(AssessmentQuestion).filter(AssessmentQuestion.assessment.has(project_id=project.id)).delete(synchronize_session=False)
    db.query(Assessment).filter(Assessment.project_id == project.id).delete()
    db.query(Concept).filter(Concept.project_id == project.id).delete()
    db.commit()
    
    c1 = Concept(project_id=project.id, name="Deep Learning", description="Neural networks") # Low Mastery
    c2 = Concept(project_id=project.id, name="Natural Language Processing", description="NLP") # Low Mastery
    c3 = Concept(project_id=project.id, name="Machine Learning Fundamentals", description="Basic ML concepts") # High Mastery
    c4 = Concept(project_id=project.id, name="Linear Algebra", description="Math") # High Mastery
    c5 = Concept(project_id=project.id, name="Calculus", description="Math") # High Mastery
    c6 = Concept(project_id=project.id, name="Statistics", description="Math") # High Mastery
    c7 = Concept(project_id=project.id, name="Reinforcement Learning", description="RL principles") # Untested
    c8 = Concept(project_id=project.id, name="Computer Vision", description="CV principles") # Untested
    db.add_all([c1, c2, c3, c4, c5, c6, c7, c8])
    db.commit()
    
    # Failing concepts (<0.4) get weight 3.0
    m1 = Mastery(project_id=project.id, concept_id=c1.id, score=0.2)
    m2 = Mastery(project_id=project.id, concept_id=c2.id, score=0.3)
    # Mastered concepts (>=0.8) get weight 0.1
    m3 = Mastery(project_id=project.id, concept_id=c3.id, score=0.9)
    m4 = Mastery(project_id=project.id, concept_id=c4.id, score=0.85)
    m5 = Mastery(project_id=project.id, concept_id=c5.id, score=0.95)
    m6 = Mastery(project_id=project.id, concept_id=c6.id, score=0.9)
    # Untested concepts (c7, c8) get weight 2.0 (no mastery rows created)
    
    db.add_all([m1, m2, m3, m4, m5, m6])
    db.commit()
    
    # Print current mastery state
    print("\n--- CURRENT MASTERY STATE ---")
    concepts = db.query(Concept).filter(Concept.project_id == project.id).all()
    for c in concepts:
        m = db.query(Mastery).filter(Mastery.concept_id == c.id, Mastery.project_id == project.id).first()
        score = m.score if m else "No row / untested"
        print(f"Concept: {c.name} | Mastery: {score}")

    # Generate 3 quizzes to prove consistency and weighting
    for i in range(1, 4):
        print(f"\n--- GENERATING QUIZ {i} ---")
        assessment = await generate_quiz_for_project(project.id)
        assessment = db.query(Assessment).filter(Assessment.id == assessment.id).first()
        
        selected_concepts = set()
        open_ended_count = 0
        mcq_count = 0
        
        for q in assessment.questions:
            selected_concepts.add(q.concept_id)
            if q.type == "open_ended":
                open_ended_count += 1
            elif q.type == "mcq":
                mcq_count += 1
        
        for c in concepts:
            status = "SELECTED" if c.id in selected_concepts else "NOT SELECTED"
            m = db.query(Mastery).filter(Mastery.concept_id == c.id).first()
            score = m.score if m else "untested"
            print(f"- {c.name} (Mastery: {score}): {status}")
            
        print(f"Quiz {i} Distribution: {mcq_count} MCQs, {open_ended_count} Open-Ended")

    # Use the last assessment for grading test
    open_ended = next((q for q in assessment.questions if q.type == "open_ended"), None)
    
    if open_ended:
        print(f"\n--- TEST 2: Submit Weak Answer ---")
        weak_answers = [
            QuestionSubmit(question_id=open_ended.id, answer="I have no idea what this is, maybe it has to do with computers.")
        ]
        weak_res = await submit_assessment(project.id, assessment.id, AssessmentSubmitRequest(answers=weak_answers))
        db.expire_all()
        weak_res = db.query(Assessment).filter(Assessment.id == weak_res.id).first()
        
        for q in weak_res.questions:
            if q.id == open_ended.id:
                print(f"\nQ: {q.question_text}")
                print(f"Score: {q.score}\nFeedback: {q.feedback}")

        print("\n--- TEST 3: Submit Strong Answer ---")
        assessment2 = await generate_quiz_for_project(project.id)
        assessment2 = db.query(Assessment).filter(Assessment.id == assessment2.id).first()
        open_ended2 = next((q for q in assessment2.questions if q.type == "open_ended"), None)
        
        if open_ended2:
            strong_answers = [
                QuestionSubmit(question_id=open_ended2.id, answer="Machine learning involves algorithms that improve automatically through experience and data. It includes supervised learning, unsupervised learning, and reinforcement learning. Models are trained using loss functions and evaluated on accuracy and other metrics while avoiding overfitting.")
            ]
            strong_res = await submit_assessment(project.id, assessment2.id, AssessmentSubmitRequest(answers=strong_answers))
            db.expire_all()
            strong_res = db.query(Assessment).filter(Assessment.id == strong_res.id).first()
            
            for q in strong_res.questions:
                if q.id == open_ended2.id:
                    print(f"\nQ: {q.question_text}")
                    print(f"Score: {q.score}\nFeedback: {q.feedback}")
        else:
            print("Failed to generate an open-ended question in assessment2.")
    else:
        print("Failed to generate an open-ended question across all 3 tests.")

if __name__ == "__main__":
    asyncio.run(main())
