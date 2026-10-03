"""Native Anthropic Messages API adapter, no tool-use authority."""

from typing import Any

from lumis_sdk.connectors.http import read_json
from lumis_sdk.models.structured import INSTRUCTIONS, StructuredHypothesisModel


class AnthropicHypothesisModel(StructuredHypothesisModel):
    async def _request(self, content: str, schema: dict[str, Any]) -> str:
        payload = await read_json(
            self.client,
            "POST",
            "https://api.anthropic.com/v1/messages",
            max_bytes=100000,
            headers={
                "x-api-key": self._api_key.get_secret_value(),
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_output_tokens,
                "system": INSTRUCTIONS,
                "messages": [{"role": "user", "content": content}],
                "output_config": {"format": {"type": "json_schema", "schema": schema}},
            },
        )
        if payload.get("stop_reason") != "end_turn":
            raise ValueError("model response incomplete or refused")
        blocks = payload.get("content", [])
        if len(blocks) != 1 or blocks[0].get("type") != "text":
            raise ValueError("unexpected model content or tool call")
        text = blocks[0].get("text")
        if not isinstance(text, str):
            raise ValueError("model content must be JSON text")
        return text
