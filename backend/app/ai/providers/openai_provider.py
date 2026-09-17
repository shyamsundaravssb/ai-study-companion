from typing import Any
import os
import logging
from app.core.config import settings
from app.ai.providers.base import ProviderBase, ProviderResponse

logger = logging.getLogger(__name__)

class OpenAIProvider(ProviderBase):
    def __init__(self):
        # We import here to avoid failing at import-time if the user hasn't installed openai yet,
        # since OPENAI_API_KEY isn't available yet anyway.
        try:
            from openai import AsyncOpenAI
            api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
            self.client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            logger.warning("openai package not installed. OpenAIProvider will fail if called.")
            self.client = None

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any
    ) -> ProviderResponse:
        """
        Generate completion using OpenAI API.
        Untested pending OPENAI_API_KEY.
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized (missing package).")
            
        response = await self.client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
        
        text = response.choices[0].message.content or ""
        
        prompt_tokens = 0
        completion_tokens = 0
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

        return ProviderResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response=response
        )
