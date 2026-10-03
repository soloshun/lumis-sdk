"""Four native provider contracts, all mocked; no keys or paid calls are used."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr
from test_operational_intelligence import fixture

from lumis_sdk.core import IncidentContext
from lumis_sdk.models.factory import create_hypothesis_model
from lumis_sdk.models.openrouter import OpenRouterHypothesisModel
from lumis_sdk.runtime.project import ModelSettings

PROVIDERS = ("openrouter", "openai", "anthropic", "gemini")


def context_and_text():
    project, incident, _ = fixture()
    incident = incident.model_copy(update={"symptoms": ("password=must-not-export",)})
    query = project.queries[0].model_copy(update={"parameters": {"credential": "never-export"}})
    context = IncidentContext(
        incident=incident, graph=project.graph, queries=(query, *project.queries[1:])
    )
    text = json.dumps(
        {"hypotheses": [item.model_dump(mode="json") for item in project.rule_hypotheses]}
    )
    return context, text, project.rule_hypotheses


def envelope(provider, text, *, complete=True):
    if provider == "openrouter":
        return {
            "choices": [
                {"finish_reason": "stop" if complete else "length", "message": {"content": text}}
            ]
        }
    if provider == "openai":
        return {
            "status": "completed" if complete else "incomplete",
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                },
            ],
        }
    if provider == "anthropic":
        return {
            "stop_reason": "end_turn" if complete else "max_tokens",
            "content": [{"type": "text", "text": text}],
        }
    return {
        "candidates": [
            {
                "finishReason": "STOP" if complete else "MAX_TOKENS",
                "content": {"parts": [{"text": text}]},
            }
        ]
    }


def invoke(provider, handler, *, max_input_characters=20000, on_model=None):
    context, _, _ = context_and_text()

    async def generate():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = create_hypothesis_model(
                provider=provider,
                model="test-model",
                api_key=SecretStr("private-test-key"),
                client=client,
                max_output_tokens=1000,
                max_input_characters=max_input_characters,
            )
            if on_model is not None:
                on_model(model)
            return await model.generate(context)

    return asyncio.run(generate())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_provider_native_serialization_and_common_validation(provider):
    _, text, hypotheses = context_and_text()
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert "must-not-export" not in request.content.decode()
        assert "never-export" not in request.content.decode()
        assert "private-test-key" not in request.content.decode()
        assert "private-test-key" not in str(request.url)
        assert "tools" not in body
        if provider == "openrouter":
            assert request.url.host == "openrouter.ai"
            assert body["model"] == "test-model"
            assert body["max_tokens"] == 1000
            assert body["provider"] == {"require_parameters": True}
            assert request.headers["authorization"] == "Bearer private-test-key"
        elif provider == "openai":
            assert request.url.path == "/v1/responses"
            assert body["store"] is False
            assert body["max_output_tokens"] == 1000
            assert body["text"]["format"]["strict"] is True
        elif provider == "anthropic":
            assert request.url.path == "/v1/messages"
            assert request.headers["x-api-key"] == "private-test-key"
            assert request.headers["anthropic-version"] == "2023-06-01"
            assert body["max_tokens"] == 1000
            assert "minItems" not in json.dumps(body["output_config"]["format"]["schema"])
        else:
            assert request.url.path.endswith("/test-model:generateContent")
            assert request.headers["x-goog-api-key"] == "private-test-key"
            assert body["generationConfig"]["maxOutputTokens"] == 1000
            assert (
                body["generationConfig"]["responseFormat"]["text"]["mimeType"] == "application/json"
            )
        return httpx.Response(200, json=envelope(provider, text))

    assert invoke(provider, handler) == hypotheses
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("kind", ["incomplete", "invalid-json", "too-few", "unknown-entity"])
def test_native_providers_reject_unusable_or_forged_output(provider, kind):
    _, text, _ = context_and_text()
    batch = json.loads(text)
    if kind == "invalid-json":
        text = "not-json"
    elif kind == "too-few":
        batch["hypotheses"] = batch["hypotheses"][:2]
        text = json.dumps(batch)
    elif kind == "unknown-entity":
        batch["hypotheses"] = [batch["hypotheses"][0] | {"causal_path": ["forged-entity"]}] * 3
        text = json.dumps(batch)
    with pytest.raises(ValueError):
        invoke(
            provider,
            lambda request: httpx.Response(
                200, json=envelope(provider, text, complete=kind != "incomplete")
            ),
        )


@pytest.mark.parametrize("provider", PROVIDERS)
def test_no_hidden_retry_or_fallback_on_provider_error(provider):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": "rate limited"})

    with pytest.raises(httpx.HTTPStatusError):
        invoke(provider, handler)
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
def test_model_budget_is_enforced_before_any_request(provider):
    def forbidden(request):
        pytest.fail("network transport must not be reached")

    with pytest.raises(ValueError, match="character budget"):
        invoke(provider, forbidden, max_input_characters=1)


@pytest.mark.parametrize(
    "provider,env",
    [
        ("openrouter", "OPENROUTER_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
    ],
)
def test_provider_configuration_selects_matching_key_default(provider, env):
    assert ModelSettings(provider=provider, model="test-model").credential_env == env
    assert (
        ModelSettings(
            provider=provider, model="test-model", api_key_env="CUSTOM_KEY"
        ).credential_env
        == "CUSTOM_KEY"
    )


def test_openrouter_is_default_and_unrecognized_providers_are_rejected():
    assert ModelSettings(model="test-model").provider == "openrouter"

    async def construct():
        async with httpx.AsyncClient() as client:
            assert isinstance(
                create_hypothesis_model(
                    model="test-model", api_key=SecretStr("key"), client=client
                ),
                OpenRouterHypothesisModel,
            )
            with pytest.raises(ValueError, match="unsupported"):
                create_hypothesis_model(
                    provider="unknown", model="test-model", api_key=SecretStr("key"), client=client
                )

    asyncio.run(construct())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_one_invalid_candidate_does_not_discard_the_batch(provider):
    _, text, hypotheses = context_and_text()
    batch = json.loads(text)
    batch["hypotheses"][0]["causal_path"] = ["forged-entity"]
    holder = {}

    def capture(model):
        holder["model"] = model

    kept = invoke(
        provider,
        lambda request: httpx.Response(200, json=envelope(provider, json.dumps(batch))),
        on_model=capture,
    )
    assert kept == hypotheses[1:]
    model = holder["model"]
    assert model.rejections and model.rejections[0].startswith("candidate 1:")
    assert "forged-entity" not in " ".join(model.rejections)  # no model-authored text
    assert json.loads(model.last_response) == batch
