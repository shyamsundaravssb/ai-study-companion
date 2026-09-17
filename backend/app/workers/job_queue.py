import asyncio
import traceback
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.job import Job, JobStatus
from app.workers.document_processor import process_material

logger = logging.getLogger(__name__)

async def process_jobs():
    logger.info("Starting background job queue processor...")
    while True:
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
                
                try:
                    if job.job_type == "process_material":
                        process_material(db, job.payload["material_id"])
                    else:
                        raise ValueError(f"Unknown job_type: {job.job_type}")
                        
                    job.status = JobStatus.done
                    logger.info(f"Job {job.id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Job {job.id} failed: {e}")
                    traceback.print_exc()
                    job.attempts += 1
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
