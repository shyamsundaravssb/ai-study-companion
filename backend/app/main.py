from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import spaces, projects

app = FastAPI(title="AI Study Companion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spaces.router, prefix="/api/v1/spaces", tags=["spaces"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
