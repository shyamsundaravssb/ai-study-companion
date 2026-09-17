import asyncio
import uuid
from app.db.session import SessionLocal
from app.models.material import Material
from app.models.ai_usage import AIUsage
from app.ai.retrieval import retrieve

async def main():
    db = SessionLocal()
    mat = db.query(Material).filter(Material.status == 'ready').first()
    db.close()
    
    if not mat:
        print("No ready materials found. Cannot test.")
        return
        
    print(f"Testing retrieval with project_id={mat.project_id}")
    
    # Test 1: Real project ID
    results = await retrieve(project_id=mat.project_id, query="What is this document about?")
    print(f"Test 1 (Real Project ID): Found {len(results)} chunks.")
    if results:
        print(f"Top chunk score: {results[0].similarity_score}, filename: {results[0].filename}")
        
    # Test 2: Fake project ID (isolation test)
    fake_project_id = uuid.uuid4()
    results_fake = await retrieve(project_id=fake_project_id, query="What is this document about?")
    print(f"Test 2 (Fake Project ID): Found {len(results_fake)} chunks (Expected 0).")

    # Test 3: Check ai_usage
    db = SessionLocal()
    usages = db.query(AIUsage).filter(AIUsage.feature == 'embed_query').order_by(AIUsage.created_at.desc()).limit(2).all()
    print(f"Found {len(usages)} AI usage records for 'embed_query'")
    for u in usages:
        print(f"Usage: project_id={u.project_id}, prompt_tokens={u.prompt_tokens}, latency_ms={u.latency_ms}, success={u.success}")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
