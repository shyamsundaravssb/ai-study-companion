import asyncio
import uuid
import sys
import logging
from datetime import datetime, timezone, timedelta
from app.db.session import SessionLocal
from app.models.job import Job, JobStatus
from app.models.material import Material, MaterialStatus
from app.workers.job_queue import process_jobs

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def run_verifications():
    db = SessionLocal()
    
    # ---------------------------------------------------------
    # TEST 4 / 1: Unblock the previously stuck job
    # ---------------------------------------------------------
    print("\n--- TEST 1: Unblocking stuck job ---")
    material_id_stuck = "3ea7bcfb-52fd-4e7d-a3a2-531a9a89b024"
    stuck_job = db.query(Job).filter(Job.payload["material_id"].as_string() == material_id_stuck).first()
    
    if stuck_job:
        stuck_job.status = JobStatus.queued
        stuck_job.attempts = 0
        db.commit()
        print(f"Reset job {stuck_job.id} to queued.")
    
    # ---------------------------------------------------------
    # TEST 2: Simulate a new failure
    # ---------------------------------------------------------
    print("\n--- TEST 2: Simulate failure ---")
    fail_material = Material(
        id=uuid.uuid4(),
        project_id="1aa16abc-a80d-4385-9f67-c1a9ffd03406", # valid project id
        filename="fake.pdf",
        storage_path="fake/path/does_not_exist.pdf", # will fail download
        status=MaterialStatus.queued
    )
    db.add(fail_material)
    
    fail_job = Job(
        id=uuid.uuid4(),
        job_type="process_material",
        payload={"material_id": str(fail_material.id)},
        status=JobStatus.queued
    )
    db.add(fail_job)
    db.commit()
    print(f"Created fake failing job {fail_job.id}")
    
    # ---------------------------------------------------------
    # TEST 3: Simulate a stale job
    # ---------------------------------------------------------
    print("\n--- TEST 3: Simulate stale job ---")
    stale_job = Job(
        id=uuid.uuid4(),
        job_type="process_material",
        payload={"material_id": "dummy"},
        status=JobStatus.processing,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=25)
    )
    db.add(stale_job)
    db.commit()
    print(f"Created stale job {stale_job.id}")
    
    # Run watchdog manually to see Test 3 results
    print("\n[Running Watchdog]")
    
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
    stale_jobs = db.query(Job).filter(
        Job.status == JobStatus.processing,
        Job.updated_at < stale_threshold
    ).all()
    
    for sj in stale_jobs:
        print(f"Watchdog found stale job {sj.id}")
        sj.attempts += 1
        sj.error = "Stale/orphaned job reclaimed by watchdog"
        if sj.attempts >= sj.max_attempts:
            sj.status = JobStatus.failed
        else:
            sj.status = JobStatus.queued
    db.commit()
    
    # Check stale job status
    db.refresh(stale_job)
    print(f"Stale job {stale_job.id} is now {stale_job.status} (attempts: {stale_job.attempts}, error: {stale_job.error})")
    
    db.close()
    
if __name__ == "__main__":
    asyncio.run(run_verifications())
