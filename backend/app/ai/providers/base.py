from typing import Protocol, Any
from dataclasses import dataclass

@dataclass
class ProviderResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    raw_response: Any = None

class ProviderBase(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        **kwargs: Any
    ) -> ProviderResponse:
        """
        Generate a completion for the given messages.
        
        Args:
            messages: List of message dictionaries, e.g. [{"role": "user", "content": "hello"}]
            model: The model string identifier to use
            **kwargs: Additional provider-specific generation parameters (temperature, max_tokens, etc.)
            
        Returns:
            ProviderResponse containing the generated text and token counts.
        """
        ...
