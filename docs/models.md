# Model providers

OpenRouter is the default **configured** provider. There is no default model ID,
no automatic model invocation and no cross-provider fallback.
The SDK also includes native OpenAI, Anthropic and Gemini HTTP adapters.

## Recommended tool-using investigator

Install the agent extra for `YamlProject.handle_incident(use_agent=True)` / `lumis incident --use-agent`.
One Pydantic AI agent uses native OpenRouter/OpenAI Responses/Anthropic/Gemini provider interfaces,
with an optional Bedrock Converse integration, typed output and named inspection/probe tools.
Explicit credentials and a tool-capable model ID are required.
OpenRouter IDs must use upstream-provider/model form. No configuration-time paid requests,
cross-provider fallback or native SDK transport retries occur.
OpenRouter routing fallback is disabled and required parameter support requested.
OpenAI response storage is explicitly disabled; provider retention policy still applies.

Per-run request, tool-attempt, output-token and context/output-character limits are enforced.
Read [incident investigation](incident-investigation.md) for authority, evidence and privacy
limits. Importing the core does not import Pydantic AI or HTTP clients.
The provider factories are tested offline; live function/schema support, privacy, costs and
model-quality qualification remain separate. No universal "any model" compatibility is claimed.

The wiring follows [Pydantic AI tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) and
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling);
tool authorization and final support remain application-owned.

## Candidate-only baseline adapters

All four baseline adapters implement the async `HypothesisModel.generate(context)` boundary and return
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
Candidates are judged individually: an invalid one is dropped and its reason (schema location and
error type, or the SDK's own validation message; never model text) is kept on the adapter's
`rejections` and traced by the runtime, while valid ones proceed. The raw answer text of the last
call is available as `last_response` for evaluation. Response reads are capped by
`max_response_bytes` (default 1 MB; reasoning models return their reasoning with the answer).
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

## AWS Bedrock investigator

Install `pip install 'lumis-sdk[agent,bedrock]'`. The investigator uses Pydantic AI's
[`BedrockConverseModel` and `BedrockProvider`](https://pydantic.dev/docs/ai/models/bedrock/),
not a separate hand-written inference adapter. The SDK supplies an owned boto3 client only
to enforce transport timeouts, one transport attempt and cleanup.

```yaml
models:
  provider: bedrock
  model: YOUR_CONVERSE_TOOL_CAPABLE_MODEL_OR_INFERENCE_PROFILE_ID
  aws_region: us-east-1
```

Credentials come from AWS's standard credential chain: for example an authenticated local
profile selected with `AWS_PROFILE`, or an execution role. No AWS keys belong in YAML.
`api_key_env`, `reasoning` and Anthropic-only cache settings are rejected for this provider.
`aws_region` is optional if the region is supplied by AWS configuration.
Credential resolution may use AWS credential services; it does not invoke a model.
`lumis doctor` checks the optional dependency without probing AWS credentials or model access.
Bedrock is supported by `handle_incident(use_agent=True)` / `investigate_incident`, not the
older candidate-only `investigate(use_model=True)` path.

Live qualification is operator-controlled and can incur charges:

1. Authenticate through your usual AWS profile/role; confirm the account and region.
2. Verify access to a Converse-compatible, tool-capable model or inference profile. Grant only
   the required Bedrock invocation permissions; cross-region profiles need destination access.
3. Run `lumis doctor --project lumis.yaml`, then a synthetic, non-sensitive incident with
   `lumis incident --project lumis.yaml --incident incident.json --use-agent --format markdown`.
4. Check the saved JSON report's stop reason, bounded request/token counts, receipts and cited
   evidence. Repeat with missing evidence and a no-fault control; neither may become confirmation.
5. Record the model/profile ID, region, SDK version, cost and outcome. Offline construction
   tests alone do not qualify live schema support, IAM, model quality or production use.

## Stable prompt prefix and Anthropic caching

Agent instructions, tool definitions and the scoped catalog are stable within a run. New tool
results are appended after the initial incident context; changing incidents/catalogs may invalidate
the prefix. Provider caching is an explicit opt-in, not a guaranteed saving:

```yaml
models:
  provider: anthropic
  model: YOUR_TOOL_CAPABLE_MODEL_ID
  cache_instructions: 5m
  cache_tool_definitions: true
```

The settings map to Pydantic AI's `anthropic_cache_instructions` and
`anthropic_cache_tool_definitions`; each accepts `true`, `false`, `5m` or `1h`.
Other providers reject these settings rather than silently ignoring them.
The report records provider-reported `cache_read_tokens` and `cache_write_tokens` (zero if absent).
`report.metrics.cache_read_share` is cached-read tokens divided by input tokens, or zero when the
denominator is zero; it is a Python convenience property, not an additional JSON field.
Model-specific cache minimums, TTL, billing and provider support must be checked before a live run.
Offline tests validate wiring and accounting, not cache hit rates or cost reductions.

## Integration adoption

Prefer Pydantic AI's model/provider integrations for the tool-using investigator. Additional
providers under consideration are Groq, Mistral, Cohere, xAI, Hugging Face and Cerebras.
They are **not yet selectable in SDK YAML**: each needs an optional dependency, explicit credential
handling, bounded transport ownership, offline wire/tool tests and separate live qualification.
Installing a Pydantic AI extra alone does not constitute SDK support.

MCP tool servers and DBOS workflow execution are separate integration proposals, not model
providers. They are not enabled by this maintenance work; remote tool authority and durable
execution need their own design and safety review. The SDK remains independently installable.
