import uuid
import asyncio
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.material import Material
from app.models.concept import Concept
from app.ai.graphs.quiz_graph import quiz_app

async def main():
    db = SessionLocal()
    
    # Get the specific material for poverty and inequality
    material = db.query(Material).filter_by(id="8f06adac-b190-45af-9021-f22ad3643600").first()
    if not material:
        print("Test material not found!")
        return
        
    project_id = material.project_id
    
    concepts = db.query(Concept).filter_by(project_id=project_id).all()
    if not concepts:
        print(f"No concepts found for Project {project_id}! Need to run extraction first.")
        return
        
    print(f"Testing with Project: {project_id}")
    print(f"Found {len(concepts)} concepts for this project:")
    for c in concepts:
        print(f" - {c.name}")
        
    db.close()
    
    print(f"\nGenerating quiz for Project {project_id}...")
    try:
        final_state = await quiz_app.ainvoke({"project_id": str(project_id)})
        
        print("\n--- Generated Quiz ---")
        for q in final_state.get("parsed_quiz", {}).get("questions", []):
            print(f"[{q['type']}] Concept: {q['concept_id']}")
            print(f"Q: {q['prompt_text']}")
            if q['type'] == 'mcq':
                for i, opt in enumerate(q['options']):
                    print(f"  {i}: {opt['text']}")
                print(f"Correct: {q['correct_option_index']}")
            print("")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
