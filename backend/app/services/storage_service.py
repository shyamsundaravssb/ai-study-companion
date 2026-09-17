import uuid
import tempfile
import os
from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    # Use service role key to bypass RLS in the background worker
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

def upload_material(project_id: uuid.UUID, material_id: uuid.UUID, filename: str, file_content: bytes) -> str:
    supabase = get_supabase_client()
    storage_path = f"{project_id}/{material_id}/{filename}"
    supabase.storage.from_("materials").upload(file=file_content, path=storage_path, file_options={"content-type": "application/pdf"})
    return storage_path

def download_material_to_tempfile(storage_path: str) -> str:
    supabase = get_supabase_client()
    # download returns bytes
    res = supabase.storage.from_("materials").download(storage_path)
    
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, 'wb') as f:
        f.write(res)
        
    return temp_path
