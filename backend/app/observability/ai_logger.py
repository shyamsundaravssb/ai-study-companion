import time
import uuid
import logging
from typing import Any
from app.db.session import SessionLocal
from app.models.ai_usage import AIUsage
from app.ai.providers.base import ProviderBase, ProviderResponse

logger = logging.getLogger(__name__)

# Placeholder rates (per 1,000 tokens)
# GPT-4o-mini is standard for this tier: $0.150 / 1M input, $0.600 / 1M output -> $0.00015 / 1K, $0.0006 / 1K
# Llama 3.3 70B via Groq: ~$0.59 / 1M input, $0.79 / 1M output -> $0.00059 / 1K, $0.00079 / 1K
# Cohere embed-v4.0: $0.10 / 1M tokens -> $0.0001 / 1K
COST_RATES = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "llama3-70b-8192": {"prompt": 0.00059, "completion": 0.00079},
    # Groq alternative model string naming
    "llama-3.3-70b-versatile": {"prompt": 0.00059, "completion": 0.00079},
    "embed-v4.0": {"prompt": 0.0001, "completion": 0.0},
    "openai/gpt-oss-20b": {"prompt": 0.0, "completion": 0.0},
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    # Find matching rate entry or default to None
    rates = COST_RATES.get(model, None)
    # If not found explicitly, maybe do a substring match
    if rates is None:
        for k, v in COST_RATES.items():
            if k in model.lower():
                rates = v
                break
        
        # If still unmatched after substring match, log a warning and default to 0
        if rates is None:
            logger.warning(f"Unmatched model '{model}' in cost calculation, defaulting to $0.00")
            rates = {"prompt": 0.0, "completion": 0.0}

    cost = (prompt_tokens / 1000.0) * rates["prompt"] + (completion_tokens / 1000.0) * rates["completion"]
    return cost

def log_ai_usage(
    project_id: uuid.UUID | None,
    model: str,
    feature: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    success: bool,
    error_message: str | None
):
    """
    Synchronously log AI usage to the database.
    """
    cost = calculate_cost(model, prompt_tokens, completion_tokens)
    db = SessionLocal()
    try:
        usage_record = AIUsage(
            project_id=project_id,
            model=model,
            feature=feature,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=cost,
            success=success,
            error_message=error_message
        )
        db.add(usage_record)
        db.commit()
    except Exception as log_err:
        logger.error(f"Failed to write ai_usage record: {log_err}")
        db.rollback()
    finally:
        db.close()

async def logged_generate(
    provider: ProviderBase,
    feature: str,
    project_id: uuid.UUID | None,
    messages: list[dict[str, str]],
    model: str,
    **kwargs: Any
) -> ProviderResponse:
    """
    Wraps a provider generate call, measuring latency, tracking tokens and calculating estimated costs.
    Logs the outcome to the `ai_usage` table.
    """
    start_time = time.perf_counter()
    success = False
    error_message = None
    prompt_tokens = 0
    completion_tokens = 0
    
    try:
        response = await provider.generate(messages=messages, model=model, **kwargs)
        success = True
        prompt_tokens = response.prompt_tokens
        completion_tokens = response.completion_tokens
        return response
    except Exception as e:
        error_message = str(e)
        logger.error(f"AI Provider call failed for feature '{feature}': {error_message}")
        raise
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_ai_usage(
            project_id=project_id,
            model=model,
            feature=feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message
        )
