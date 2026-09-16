from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import verify_jwt_token
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.space import Space
import uuid

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Verifies the JWT token and returns the current user.
    Creates a new user record on first login if it doesn't exist.
    """
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format in token")
        
    email = payload.get("email", "")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Sync on first login
        user = User(
            id=user_id,
            email=email,
            role=UserRole.user
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user

def get_project_or_404(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Project:
    """
    Single choke point for Project-level data isolation.
    Returns the Project if it exists AND is owned by the current user.
    Raises 404 otherwise to avoid leaking existence.
    """
    project = db.query(Project).join(Space).filter(
        Project.id == project_id,
        Space.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return project
