import uuid
import asyncio
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.material import Material
from app.models.concept import Concept
from app.models.mastery import Mastery
from app.workers.document_processor import process_material
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
material = db.query(Material).filter_by(id="8f06adac-b190-45af-9021-f22ad3643600").first()
print(f"Testing with Material {material.id} in Project {material.project_id}")

print("--- Deleting existing Concepts to force extraction ---")
db.query(Mastery).filter_by(project_id=material.project_id).delete()
db.query(Concept).filter_by(project_id=material.project_id).delete()
db.commit()

print("--- Running process_material (First pass) ---")
process_material(db, str(material.id))

print("--- Extracted Concepts ---")
concepts = db.query(Concept).filter_by(project_id=material.project_id).all()
for c in concepts:
    print(f"- {c.name}: {c.description}")

print("\n--- Running process_material (Second pass for idempotency) ---")
count1 = db.query(Concept).filter_by(project_id=material.project_id).count()
process_material(db, str(material.id))
count2 = db.query(Concept).filter_by(project_id=material.project_id).count()
print(f"Concepts: {count2} (Diff: {count2 - count1})")
