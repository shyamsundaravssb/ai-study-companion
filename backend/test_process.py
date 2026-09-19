import logging
import sys
from app.db.session import SessionLocal
from app.workers.document_processor import process_material

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

db = SessionLocal()
print("Starting manual run of stuck job...")
try:
    process_material(db, "3ea7bcfb-52fd-4e7d-a3a2-531a9a89b024")
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
