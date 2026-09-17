import uuid
from typing import NamedTuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.material_chunk import MaterialChunk
from app.models.material import Material
from app.ai.providers import embedding_provider

SIMILARITY_THRESHOLD = 0.75
DEFAULT_TOP_K = 5

@dataclass
class RetrievedChunk:
    text: str
    page_number: int
    filename: str
    similarity_score: float

async def retrieve(project_id: uuid.UUID, query: str, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
    """
    Retrieves the top-k most relevant chunks for a given query, scoped to a project.
    
    Args:
        project_id: The UUID of the project to scope retrieval to (data isolation).
        query: The search query string.
        top_k: Maximum number of chunks to return.
        
    Returns:
        A list of RetrievedChunk objects that meet the similarity threshold.
        Returns an empty list if no chunks are found or none meet the threshold.
    """
    if not query.strip():
        return []
        
    query_embedding = await embedding_provider.embed_query(query, project_id=project_id)
    if not query_embedding:
        return []

    db = SessionLocal()
    try:
        # cosine_distance in pgvector returns (1 - cosine_similarity).
        # So we want distance to be minimum, and we can calculate similarity as 1 - distance.
        distance_col = MaterialChunk.embedding.cosine_distance(query_embedding).label("distance")
        
        results = (
            db.query(MaterialChunk, Material, distance_col)
            .join(Material, MaterialChunk.material_id == Material.id)
            .filter(MaterialChunk.project_id == project_id)
            .order_by(distance_col)
            .limit(top_k)
            .all()
        )
        
        retrieved = []
        for chunk, material, distance in results:
            similarity = 1.0 - float(distance)
            if similarity >= SIMILARITY_THRESHOLD:
                retrieved.append(
                    RetrievedChunk(
                        text=chunk.content,
                        page_number=chunk.page_number,
                        filename=material.filename,
                        similarity_score=similarity
                    )
                )
                
        return retrieved
    finally:
        db.close()
