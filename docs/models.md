# Model providers

OpenRouter is the default **configured** provider. There is no default model ID,
no automatic model invocation and no cross-provider fallback.
The SDK also includes native OpenAI, Anthropic and Gemini HTTP adapters.

All four implement the same async `HypothesisModel.generate(context)` boundary and return
3–5 locally validated falsifiable candidates. Evaluation and evidence acquisition do not change
when you switch providers. None gains tool or remediation authority.

## YAML selection

```yaml
models:
  model: your-openrouter-model-id
```

Omitting `provider` selects `openrouter`.
For a native provider, specify it and its provider-native model ID:

```yaml
models:
  provider: anthropic
  model: your-anthropic-model-id
  # api_key_env: MY_CUSTOM_MODEL_KEY  # optional override
```

| Provider | Default environment variable | Native interface |
| --- | --- | --- |
| `openrouter` | `OPENROUTER_API_KEY` | Chat Completions / structured response format |
| `openai` | `OPENAI_API_KEY` | Responses / structured text format |
| `anthropic` | `ANTHROPIC_API_KEY` | Messages / structured output format |
| `gemini` | `GEMINI_API_KEY` | generateContent / structured response format |

Model IDs are explicit and passed through; Gemini accepts a simple ID or `models/ID`,
not an arbitrary URL/path. Choose a model that supports the selected native structured-output
interface. OpenRouter's broad catalog does not imply every model supports this contract.

Set credentials using your normal secret-management method. Keys never appear in YAML or
model context. Install the `http` extra. Run `lumis doctor`, then explicitly opt in with
`lumis investigate ... --use-model`. Configuration alone makes no paid request.

## Python composition

```python
import os
import httpx
from pydantic import SecretStr
from lumis_sdk.models.factory import create_hypothesis_model
from lumis_sdk.reasoning import ModelHypothesisSource

async def propose(context):
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        model = create_hypothesis_model(
            provider="openai",
            model="your-openai-model-id",
            api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
            client=client,
            max_input_characters=20000,
            max_output_tokens=3000,
        )
        return await ModelHypothesisSource(model).propose(context)
```

The explicit wrappers are `OpenRouterHypothesisModel`, `OpenAIHypothesisModel`,
`AnthropicHypothesisModel`, `GeminiHypothesisModel` in their corresponding
`lumis_sdk.models.<provider>` modules.
Importing core never imports these optional HTTP modules.

## Shared failure and privacy behavior

Exactly one bounded request is sent to the configured provider. No retries, model probing,
paid fallback or provider switching occurs. Input is redacted and character-limited; response
reads and output tokens are bounded. Provider refusal, truncation, malformed JSON,
incorrect candidate count and invalid graph/query references cannot become trusted candidates.
Runtime source failures are audited and can result in abstention.

Wire schemas use a portable subset of structural JSON Schema; full length/count/range and
semantic constraints remain enforced locally. Native APIs differ in supported schema subsets.
OpenAI requests disable response storage with `store: false`; this is not a guarantee of
zero provider retention. Confirm each provider's current data handling separately.

Native formats were checked against
[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
and [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).
Provider APIs/model availability may change. Tests use mocked HTTP responses; no live-provider
quality, account eligibility or production qualification is claimed.
