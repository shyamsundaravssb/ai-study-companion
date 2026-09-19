import uuid
import asyncio
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.material import Material, MaterialStatus
from app.models.concept import Concept
from app.workers.document_processor import process_material
import app.ai.concept_extraction
import logging

logging.basicConfig(level=logging.INFO)

# Temporarily break the Groq provider to simulate failure
import app.ai.providers.groq_provider
class BrokenProvider:
    async def generate(self, *args, **kwargs):
        raise RuntimeError("Simulated LLM Failure")

app.ai.concept_extraction.groq_provider_instance = BrokenProvider()

db = SessionLocal()
material = db.query(Material).filter_by(id="8d4d4800-8a17-4552-8860-5ff46906cdc3").first()
print(f"Testing failure isolation with Material {material.id}")

process_material(db, str(material.id))

db.refresh(material)
print(f"Material Status after failed extraction: {material.status.value}")
