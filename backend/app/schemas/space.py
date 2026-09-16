import uuid
from datetime import datetime
from pydantic import BaseModel

class SpaceBase(BaseModel):
    name: str
    description: str | None = None

class SpaceCreate(SpaceBase):
    pass

class SpaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class SpaceResponse(SpaceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
