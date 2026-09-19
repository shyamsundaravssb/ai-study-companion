from app.db.session import SessionLocal
from app.models.job import Job

db = SessionLocal()
job = db.query(Job).filter(Job.id == 'c9f57b1d-78c4-4166-bc3c-dff754489053').first()
print(f"Payload: {job.payload}")
