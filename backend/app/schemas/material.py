import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.material import MaterialStatus

class MaterialBase(BaseModel):
    filename: str

class MaterialResponse(MaterialBase):
    id: uuid.UUID
    project_id: uuid.UUID
    status: MaterialStatus
    page_count: int | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}
