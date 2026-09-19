import asyncio
import uuid
from supabase import create_client, Client
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.space import Space
from app.models.project import Project
import httpx

async def test_isolation():
    print("Initializing Supabase client...")
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    
    email = f"test_isolation_{uuid.uuid4().hex[:8]}@example.com"
    password = "Password123!"
    
    print(f"Creating new user: {email}")
    auth_res = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    
    # Sign in to get JWT token
    print("Signing in to get token...")
    session_res = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    token = session_res.session.access_token
    user_id = uuid.UUID(session_res.user.id)
    
    print(f"User ID: {user_id}")
    print(f"Token acquired. Length: {len(token)}")
    
    db = SessionLocal()
    
    # 1. Create Space and Project B in the DB directly
    try:
        user_record = User(id=user_id, email=email, role=UserRole.user)
        db.add(user_record)
        db.commit()
        
        space = Space(id=uuid.uuid4(), user_id=user_id, name="Test Space")
        db.add(space)
        db.commit()
        
        project_b = Project(id=uuid.uuid4(), space_id=space.id, name="Project B")
        db.add(project_b)
        db.commit()
        print(f"Created Project B: {project_b.id}")
    except Exception as e:
        print(f"Error setting up DB: {e}")
        db.rollback()
    
    # The user requested to query project A: 1aa16abc-a80d-4385-9f67-c1a9ffd03406
    project_a_id = "1aa16abc-a80d-4385-9f67-c1a9ffd03406"
    
    print(f"\n--- TESTING ISOLATION FOR PROJECT A: {project_a_id} ---")
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "http://127.0.0.1:8000"
    
    endpoints = [
        f"/api/v1/projects/{project_a_id}/materials",
        f"/api/v1/projects/{project_a_id}/tutor/conversations"
    ]
    
    async with httpx.AsyncClient() as client:
        for ep in endpoints:
            print(f"\nGET {ep}")
            resp = await client.get(f"{base_url}{ep}", headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
            
    print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_isolation())
