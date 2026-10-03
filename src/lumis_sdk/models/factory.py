"""Explicit provider selection; no probing, retry or cross-provider fallback."""

import httpx
from pydantic import SecretStr

from lumis_sdk.models.anthropic import AnthropicHypothesisModel
from lumis_sdk.models.gemini import GeminiHypothesisModel
from lumis_sdk.models.openai import OpenAIHypothesisModel
from lumis_sdk.models.openrouter import OpenRouterHypothesisModel
from lumis_sdk.models.structured import StructuredHypothesisModel

PROVIDERS: dict[str, type[StructuredHypothesisModel]] = {
    "openrouter": OpenRouterHypothesisModel,
    "openai": OpenAIHypothesisModel,
    "anthropic": AnthropicHypothesisModel,
    "gemini": GeminiHypothesisModel,
}


def create_hypothesis_model(
    *,
    model: str,
    api_key: SecretStr,
    client: httpx.AsyncClient,
    provider: str = "openrouter",
    max_input_characters: int = 20000,
    max_output_tokens: int = 3000,
) -> StructuredHypothesisModel:
    """Default the configured provider to OpenRouter; an explicit model/key is still required."""
    if provider not in PROVIDERS:
        raise ValueError("unsupported model provider")
    return PROVIDERS[provider](
        model=model,
        api_key=api_key,
        client=client,
        max_input_characters=max_input_characters,
        max_output_tokens=max_output_tokens,
    )
