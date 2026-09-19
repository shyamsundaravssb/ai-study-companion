from app.db.session import SessionLocal
from app.models.job import Job

db = SessionLocal()
jobs = db.query(Job).order_by(Job.created_at.desc()).limit(5).all()
print("Latest Jobs:")
for job in jobs:
    print(f"ID: {job.id}")
    print(f"Status: {job.status}")
    print(f"Type: {job.job_type}")
    print(f"Attempts: {job.attempts}")
    print(f"Created: {job.created_at}")
    print(f"Updated: {job.updated_at}")
    print("-" * 20)
