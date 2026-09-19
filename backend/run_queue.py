import asyncio
import logging
import sys
from app.workers.job_queue import process_jobs

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    print("Running job queue for a few seconds to process pending jobs...")
    task = asyncio.create_task(process_jobs())
    await asyncio.sleep(20)
    task.cancel()
    
if __name__ == "__main__":
    asyncio.run(main())
