import asyncio
import uuid
from app.db.session import SessionLocal
from app.models.material import Material
from app.models.material_chunk import MaterialChunk
from app.ai.retrieval import retrieve
from app.ai.providers import embedding_provider

async def main():
    db = SessionLocal()
    mat = db.query(Material).filter(Material.status == 'ready').first()
    db.close()
    
    if not mat:
        print("No ready materials found. Cannot test.")
        return
        
    print(f"Testing retrieval with project_id={mat.project_id}")
    
    # Bypass threshold for debug
    query_embedding = embedding_provider.embed_query("What is this document about?")
    db = SessionLocal()
    distance_col = MaterialChunk.embedding.cosine_distance(query_embedding).label("distance")
    
    # Test 1: Real project ID
    results = (
        db.query(MaterialChunk, Material, distance_col)
        .join(Material, MaterialChunk.material_id == Material.id)
        .filter(MaterialChunk.project_id == mat.project_id)
        .order_by(distance_col)
        .limit(3)
        .all()
    )
    print(f"Raw query for Real Project ID found {len(results)} chunks")
    for r in results:
        chunk, material, distance = r
        print(f"Distance: {distance}, Score: {1-distance}, File: {material.filename}")
        
    # Test 2: Fake project ID (isolation test)
    fake_project_id = uuid.uuid4()
    results_fake = (
        db.query(MaterialChunk, Material, distance_col)
        .join(Material, MaterialChunk.material_id == Material.id)
        .filter(MaterialChunk.project_id == fake_project_id)
        .order_by(distance_col)
        .limit(3)
        .all()
    )
    print(f"Raw query for Fake Project ID found {len(results_fake)} chunks (Expected 0).")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
