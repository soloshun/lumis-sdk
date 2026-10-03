"""Native OpenAI Responses API adapter with locally enforced candidate invariants."""

from typing import Any

from lumis_sdk.connectors.http import read_json
from lumis_sdk.models.structured import INSTRUCTIONS, StructuredHypothesisModel


class OpenAIHypothesisModel(StructuredHypothesisModel):
    async def _request(self, content: str, schema: dict[str, Any]) -> str:
        payload = await read_json(
            self.client,
            "POST",
            "https://api.openai.com/v1/responses",
            max_bytes=100000,
            headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
            json={
                "model": self.model,
                "max_output_tokens": self.max_output_tokens,
                "store": False,
                "input": [
                    {"role": "system", "content": INSTRUCTIONS},
                    {"role": "user", "content": content},
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "lumis_hypotheses",
                        "strict": True,
                        "schema": schema,
                    }
                },
            },
        )
        if payload.get("status") != "completed" or payload.get("error"):
            raise ValueError("model response incomplete or failed")
        texts: list[str] = []
        for item in payload.get("output", []):
            if item.get("type") == "reasoning":
                continue
            if item.get("type") != "message" or item.get("role") != "assistant":
                raise ValueError("unexpected model output item")
            for block in item.get("content", []):
                if block.get("type") != "output_text" or not isinstance(block.get("text"), str):
                    raise ValueError("model refused or returned unexpected content")
                texts.append(block["text"])
        if len(texts) != 1:
            raise ValueError("model response must contain one structured output")
        return texts[0]
