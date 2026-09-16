import uuid
from sqlalchemy.orm import Session
from app.models.space import Space
from app.schemas.space import SpaceCreate, SpaceUpdate

def create_space(db: Session, space_in: SpaceCreate, user_id: uuid.UUID) -> Space:
    space = Space(
        user_id=user_id,
        name=space_in.name,
        description=space_in.description
    )
    db.add(space)
    db.commit()
    db.refresh(space)
    return space

def get_spaces_by_user(db: Session, user_id: uuid.UUID) -> list[Space]:
    return db.query(Space).filter(Space.user_id == user_id).all()

def get_space(db: Session, space_id: uuid.UUID, user_id: uuid.UUID) -> Space | None:
    return db.query(Space).filter(Space.id == space_id, Space.user_id == user_id).first()

def update_space(db: Session, space: Space, space_in: SpaceUpdate) -> Space:
    update_data = space_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(space, field, value)
    db.commit()
    db.refresh(space)
    return space
