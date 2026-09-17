from typing import Any
import os
from groq import AsyncGroq
from app.core.config import settings
from app.ai.providers.base import ProviderBase, ProviderResponse

class GroqProvider(ProviderBase):
    def __init__(self):
        # We assume GROQ_API_KEY is available in settings.
        api_key = settings.GROQ_API_KEY
        if not api_key:
            # Fallback to env var if not in settings explicitly (though it should be)
            api_key = os.environ.get("GROQ_API_KEY", "")
        self.client = AsyncGroq(api_key=api_key)

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any
    ) -> ProviderResponse:
        """
        Generate completion using Groq API.
        """
        response = await self.client.chat.completions.create(
            messages=messages,
            model=model,
            **kwargs
        )
        
        text = response.choices[0].message.content or ""
        
        # Token counts might be absent if stream=True, but we assume stream=False for this base interface
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
