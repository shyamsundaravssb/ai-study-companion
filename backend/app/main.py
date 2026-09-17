from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.api.v1 import spaces, projects, materials
from app.workers.job_queue import process_jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(process_jobs())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="AI Study Companion API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spaces.router, prefix="/api/v1/spaces", tags=["spaces"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(materials.router, prefix="/api/v1/projects", tags=["materials"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
