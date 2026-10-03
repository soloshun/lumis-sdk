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
    settings: ModelSettings, *, timeout: float
) -> AsyncIterator["Investigator"]:
    import httpx2

    from lumis_sdk.investigation.agent import PydanticInvestigator

    key = os.environ.get(settings.credential_env)
    if not key:
        raise ValueError("configured investigator credential is absent")
    async with httpx2.AsyncClient(timeout=timeout, trust_env=False, follow_redirects=False) as http:
        if settings.provider in {"openrouter", "openai"}:
            from openai import AsyncOpenAI
            from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
            from pydantic_ai.models.openrouter import OpenRouterModel
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
                    yield PydanticInvestigator(
                        OpenRouterModel(
                            settings.model, provider=OpenRouterProvider(openai_client=client)
                        ),
                        model_settings={
                            "extra_body": {
                                "provider": {"allow_fallbacks": False, "require_parameters": True}
                            }
                        },
                    )
                else:
                    yield PydanticInvestigator(
                        OpenAIResponsesModel(
                            settings.model, provider=OpenAIProvider(openai_client=client)
                        ),
                        model_settings=OpenAIResponsesModelSettings(openai_store=False),
                    )
        elif settings.provider == "anthropic":
            from anthropic import AsyncAnthropic
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            async with AsyncAnthropic(api_key=key, max_retries=0, http_client=http) as anthropic:
                yield PydanticInvestigator(
                    AnthropicModel(
                        settings.model, provider=AnthropicProvider(anthropic_client=anthropic)
                    )
                )
        else:
            from google.genai.types import HttpRetryOptions
            from pydantic_ai.models.google import GoogleModel
            from pydantic_ai.providers.google import GoogleProvider

            provider = GoogleProvider(
                api_key=key, http_client=http, retry_options=HttpRetryOptions(attempts=1)
            )
            try:
                yield PydanticInvestigator(GoogleModel(settings.model, provider=provider))
            finally:
                await provider.client.aio.aclose()
                provider.client.close()
