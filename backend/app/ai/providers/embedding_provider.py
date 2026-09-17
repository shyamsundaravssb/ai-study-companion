import cohere
from app.core.config import settings

def get_cohere_client():
    return cohere.ClientV2(settings.COHERE_API_KEY)

def embed_documents(texts: list[str], input_type: str = "search_document") -> list[list[float]]:
    """
    Generate embeddings using Cohere's native SDK.
    NOTE: When Day 2 builds the Tutor's retrieval step, 
    the caller must use `input_type="search_query"`.
    """
    if not texts:
        return []
        
    client = get_cohere_client()
    
    response = client.embed(
        texts=texts,
        model="embed-v4.0",
        input_type=input_type,
        embedding_types=["float"],
        output_dimension=1536
    )
    
    # V2 SDK response structure
    return response.embeddings.float_
