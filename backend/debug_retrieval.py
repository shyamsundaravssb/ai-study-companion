import asyncio
import uuid
from app.db.session import SessionLocal
from app.models.material import Material
from app.models.material_chunk import MaterialChunk
from app.ai.providers import embedding_provider
from app.ai.retrieval import retrieve

async def main():
    db = SessionLocal()
    mat = db.query(Material).filter(Material.status == 'ready').first()
    
    if not mat:
        print("No ready materials found. Cannot test.")
        db.close()
        return
        
    print(f"Material: {mat.filename}, ID: {mat.project_id}")
    
    # 1. Print some real chunks content to pick a good query
    chunks = db.query(MaterialChunk).filter_by(material_id=mat.id).limit(3).all()
    print("\n--- CHUNK SAMPLES ---")
    for i, c in enumerate(chunks):
        print(f"Chunk {i}: len={len(c.content)}, text: {c.content[:100]}")
        
    if not chunks:
        print("No chunks found in DB!")
        db.close()
        return
        
    # Pick a query from the first chunk's exact text
    query_text = chunks[0].content[:50]
    print(f"\n--- TESTING QUERY ---")
    print(f"Query: '{query_text}'")
    
    # 2. Check query embedding
    query_emb = await embedding_provider.embed_query(query_text)
    print(f"Query embedding generated: type={type(query_emb)}, length={len(query_emb) if query_emb else 0}")
    
    db.close()
    
    # 3. Test Retrieval
    results = await retrieve(project_id=mat.project_id, query=query_text, top_k=5)
    print(f"\n--- RETRIEVAL RESULTS (Threshold=0.75) ---")
    print(f"Found {len(results)} chunks passing threshold.")
    for r in results:
        print(f"Score: {r.similarity_score:.4f}, File: {r.filename}, Text: {r.text[:50]}...")
        
    # 4. Raw DB query to show all distances regardless of threshold
    db = SessionLocal()
    distance_col = MaterialChunk.embedding.cosine_distance(query_emb).label("distance")
    raw_results = (
        db.query(MaterialChunk, distance_col)
        .filter(MaterialChunk.project_id == mat.project_id)
        .order_by(distance_col)
        .limit(5)
        .all()
    )
    print(f"\n--- RAW DISTANCES (Top 5 regardless of threshold) ---")
    for c, dist in raw_results:
        sim = 1.0 - float(dist)
        print(f"Distance: {dist:.4f} => Similarity: {sim:.4f}, Text: {c.content[:50]}...")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
