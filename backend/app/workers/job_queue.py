import asyncio
import traceback
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.job import Job, JobStatus
from app.workers.document_processor import process_material

logger = logging.getLogger(__name__)

import time

async def process_jobs():
    logger.info("Starting background job queue processor...")
    
    last_watchdog_time = 0
    WATCHDOG_INTERVAL_SECONDS = 300  # Run watchdog every 5 minutes
        
    while True:
        current_time = time.monotonic()
        
        # FIX 3: Stale-job watchdog runs periodically every WATCHDOG_INTERVAL_SECONDS
        if current_time - last_watchdog_time >= WATCHDOG_INTERVAL_SECONDS:
            try:
                db = SessionLocal()
                # 10 minutes threshold is generous enough for a 35-page PDF which takes ~1-2 mins max
                logger.info(f"Running stale-job watchdog check...")
                stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
                stale_jobs = db.query(Job).filter(
                    Job.status == JobStatus.processing,
                    Job.updated_at < stale_threshold
                ).all()
                
                for stale_job in stale_jobs:
                    logger.warning(f"Reclaiming stale job {stale_job.id}")
                    stale_job.attempts += 1
                    stale_job.error = "Stale/orphaned job reclaimed by watchdog"
                    if stale_job.attempts >= stale_job.max_attempts:
                        stale_job.status = JobStatus.failed
                    else:
                        stale_job.status = JobStatus.queued
                db.commit()
                db.close()
                last_watchdog_time = current_time
            except Exception as e:
                logger.error(f"Watchdog failed: {e}")
                
        try:
            db = SessionLocal()
            try:
                # Use SELECT ... FOR UPDATE SKIP LOCKED
                job = db.query(Job).filter(Job.status == JobStatus.queued)\
                    .order_by(Job.created_at.asc())\
                    .with_for_update(skip_locked=True)\
                    .first()
                    
                if not job:
                    db.commit()
                    db.close()
                    await asyncio.sleep(2)
                    continue
                    
                job.status = JobStatus.processing
                db.commit()
                
                logger.info(f"Picked up job {job.id} of type {job.job_type}")
                
                job_id = job.id
                try:
                    if job.job_type == "process_material":
                        process_material(db, job.payload["material_id"])
                    else:
                        raise ValueError(f"Unknown job_type: {job.job_type}")
                        
                    # Need to refetch since process_material commits
                    job = db.query(Job).filter_by(id=job_id).first()
                    if job:
                        job.status = JobStatus.done
                        job.error = None
                        logger.info(f"Job {job.id} completed successfully")
                        db.commit()
                    
                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}")
                    traceback.print_exc()
                    
                    try:
                        db.rollback()
                    except Exception:
                        pass
                        
                    job = db.query(Job).filter_by(id=job_id).first()
                    if job:
                        job.attempts += 1
                        job.error = str(e)[:1000]
                        if job.attempts >= job.max_attempts:
                            job.status = JobStatus.failed
                            logger.error(f"Job {job.id} permanently failed after {job.attempts} attempts")
                        else:
                            job.status = JobStatus.queued
                            logger.info(f"Job {job.id} queued for retry (attempt {job.attempts}/{job.max_attempts})")
                            
                        db.commit()
                
            finally:
                db.close()
                
        except asyncio.CancelledError:
            logger.info("Job queue processor cancelled")
            break
        except Exception as e:
            logger.error(f"Error in job queue loop: {e}")
            await asyncio.sleep(5)
