"""Thin wrapper around the OpenAI API. The API key never leaves the backend."""

import json
import re

from openai import OpenAI

from ..config import get_settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        key = api_key or settings.openai_api_key
        if not key or key.startswith("sk-..."):
            raise LLMError(
                "OPENAI_API_KEY is not configured. Copy backend/.env.example to "
                "backend/.env and set your key."
            )
        self._client = OpenAI(api_key=key)
        self.model = model or settings.openai_model

    def chat_text(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    def chat_json(self, system: str, user: str, temperature: float = 0.2) -> dict:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model returned invalid JSON: {exc}") from exc

    def chat_code(self, system: str, user: str) -> str:
        """Ask for a python script and strip any markdown fencing."""
        return strip_code_fences(self.chat_text(system, user))


def strip_code_fences(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()
