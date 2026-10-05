"""Explicit optional native providers with owned clients, no SDK transport retries or fallback."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from lumis_sdk.runtime.project import ModelSettings

if TYPE_CHECKING:
    from lumis_sdk.runtime.incident_handler import Investigator


@asynccontextmanager
async def configured_investigator(
    settings: ModelSettings, *, timeout: float, retries: int = 2
) -> AsyncIterator["Investigator"]:
    import httpx2

    from lumis_sdk.investigation.agent import PydanticInvestigator

    key = os.environ.get(settings.credential_env)
    if not key:
        raise ValueError("configured investigator credential is absent")
    from pydantic_ai.settings import ModelSettings as AgentModelSettings

    # `thinking` is pydantic-ai's unified setting; OpenRouter maps it to its `reasoning` field.
    thinking = AgentModelSettings()
    if settings.reasoning is not None:
        thinking["thinking"] = settings.reasoning
    async with httpx2.AsyncClient(timeout=timeout, trust_env=False, follow_redirects=False) as http:
        if settings.provider in {"openrouter", "openai"}:
            from openai import AsyncOpenAI
            from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
            from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
            from pydantic_ai.providers.openai import OpenAIProvider
            from pydantic_ai.providers.openrouter import OpenRouterProvider

            async with AsyncOpenAI(
                api_key=key,
                max_retries=0,
                http_client=http,
                base_url="https://openrouter.ai/api/v1"
                if settings.provider == "openrouter"
                else "https://api.openai.com/v1",
            ) as client:
                if settings.provider == "openrouter":
                    routing = OpenRouterModelSettings(
                        openrouter_provider={"allow_fallbacks": False, "require_parameters": True}
                    )
                    if settings.reasoning is not None:
                        routing["thinking"] = settings.reasoning
                    yield PydanticInvestigator(
                        OpenRouterModel(
                            settings.model, provider=OpenRouterProvider(openai_client=client)
                        ),
                        model_settings=routing,
                        retries=retries,
                    )
                else:
                    responses = OpenAIResponsesModelSettings(openai_store=False)
                    if settings.reasoning is not None:
                        responses["thinking"] = settings.reasoning
                    yield PydanticInvestigator(
                        OpenAIResponsesModel(
                            settings.model, provider=OpenAIProvider(openai_client=client)
                        ),
                        model_settings=responses,
                        retries=retries,
                    )
        elif settings.provider == "anthropic":
            from anthropic import AsyncAnthropic
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            async with AsyncAnthropic(api_key=key, max_retries=0, http_client=http) as anthropic:
                yield PydanticInvestigator(
                    AnthropicModel(
                        settings.model, provider=AnthropicProvider(anthropic_client=anthropic)
                    ),
                    model_settings=thinking,
                    retries=retries,
                )
        else:
            from google.genai.types import HttpRetryOptions
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            provider = GoogleProvider(
                api_key=key, http_client=http, retry_options=HttpRetryOptions(attempts=1)
            )
            try:
                yield PydanticInvestigator(
                    GoogleModel(settings.model, provider=provider),
                    model_settings=thinking,
                    retries=retries,
                )
            finally:
                await provider.client.aio.aclose()
                provider.client.close()
