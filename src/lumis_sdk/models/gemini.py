"""Native Gemini generateContent adapter with header-only credential transport."""

import re
from typing import Any

from lumis_sdk.connectors.http import read_json
from lumis_sdk.models.structured import INSTRUCTIONS, StructuredHypothesisModel


class GeminiHypothesisModel(StructuredHypothesisModel):
    async def _request(self, content: str, schema: dict[str, Any]) -> str:
        model_id = self.model.removeprefix("models/")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", model_id):
            raise ValueError("Gemini requires a simple model ID, not a URL or path")
        payload = await read_json(
            self.client,
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent",
            max_bytes=100000,
            headers={"x-goog-api-key": self._api_key.get_secret_value()},
            json={
                "systemInstruction": {"parts": [{"text": INSTRUCTIONS}]},
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": {
                    "maxOutputTokens": self.max_output_tokens,
                    "candidateCount": 1,
                    "responseFormat": {"text": {"mimeType": "application/json", "schema": schema}},
                },
            },
        )
        if payload.get("promptFeedback", {}).get("blockReason"):
            raise ValueError("model prompt blocked")
        candidates = payload.get("candidates", [])
        if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
            raise ValueError("model response incomplete or ambiguous")
        texts: list[str] = []
        for part in candidates[0].get("content", {}).get("parts", []):
            if part.get("thought") is True:
                continue
            if not isinstance(part.get("text"), str):
                raise ValueError("unexpected model content or tool call")
            texts.append(part["text"])
        if len(texts) != 1:
            raise ValueError("model response must contain one structured output")
        return texts[0]
