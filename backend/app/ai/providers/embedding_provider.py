import time
import uuid
import cohere
import logging
from app.core.config import settings
from app.observability.ai_logger import log_ai_usage

logger = logging.getLogger(__name__)

def get_cohere_client():
    return cohere.ClientV2(settings.COHERE_API_KEY)

def get_cohere_async_client():
    return cohere.AsyncClientV2(settings.COHERE_API_KEY)

def embed_document(texts: list[str], project_id: uuid.UUID | None = None) -> list[list[float]]:
    """
    Generate embeddings for documents (index-time) using Cohere's native SDK.
    Synchronous since it runs in the background worker.
    """
    if not texts:
        return []
        
    client = get_cohere_client()
    
    start_time = time.perf_counter()
    success = False
    error_message = None
    prompt_tokens = 0
    model = "embed-v4.0"
    feature = "embed_document"
    
    try:
        response = client.embed(
            texts=texts,
            model=model,
            input_type="search_document",
            embedding_types=["float"],
            output_dimension=1536
        )
        success = True
        
        # Approximate tokens if billed_units not easily accessible
        # Cohere metadata often has response.meta.billed_units.input_tokens
        if hasattr(response, 'meta') and response.meta and hasattr(response.meta, 'billed_units') and response.meta.billed_units:
            prompt_tokens = getattr(response.meta.billed_units, 'input_tokens', 0)
        if not prompt_tokens:
            prompt_tokens = sum(len(t) for t in texts) // 4
            
        return response.embeddings.float_
    except Exception as e:
        error_message = str(e)
        raise
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_ai_usage(
            project_id=project_id,
            model=model,
            feature=feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )

async def embed_query(text: str, project_id: uuid.UUID | None = None) -> list[float]:
    """
    Generate an embedding for a search query (query-time) using Cohere's async SDK.
    """
    if not text.strip():
        return []
        
    client = get_cohere_async_client()
    
    start_time = time.perf_counter()
    success = False
    error_message = None
    prompt_tokens = 0
    model = "embed-v4.0"
    feature = "embed_query"
    
    try:
        response = await client.embed(
            texts=[text],
            model=model,
            input_type="search_query",
            embedding_types=["float"],
            output_dimension=1536
        )
        success = True
        
        if hasattr(response, 'meta') and response.meta and hasattr(response.meta, 'billed_units') and response.meta.billed_units:
            prompt_tokens = getattr(response.meta.billed_units, 'input_tokens', 0)
        if not prompt_tokens:
            prompt_tokens = len(text) // 4
            
        return response.embeddings.float_[0]
    except Exception as e:
        error_message = str(e)
        raise
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_ai_usage(
            project_id=project_id,
            model=model,
            feature=feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )
