"""OpenRouter is the default configured provider, not a hidden fallback."""

from typing import Any

from lumis_sdk.connectors.http import read_json
from lumis_sdk.models.structured import INSTRUCTIONS, StructuredHypothesisModel


class OpenRouterHypothesisModel(StructuredHypothesisModel):
    async def _request(self, content: str, schema: dict[str, Any]) -> str:
        payload = await read_json(
            self.client,
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            max_bytes=self.max_response_bytes,
            headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
            json={
                "model": self.model,
                "max_tokens": self.max_output_tokens,
                "provider": {"require_parameters": True},
                "messages": [
                    {"role": "system", "content": INSTRUCTIONS},
                    {"role": "user", "content": content},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "lumis_hypotheses",
                        "strict": True,
                        "schema": schema,
                    },
                },
            },
        )
        choices = payload.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ValueError("model response incomplete or ambiguous")
        message = choices[0]["message"]
        if message.get("refusal") or message.get("tool_calls"):
            raise ValueError("model refusal or unexpected tool call")
        text = message.get("content")
        if not isinstance(text, str):
            raise ValueError("model content must be JSON text")
        return text
