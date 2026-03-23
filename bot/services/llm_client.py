from __future__ import annotations

import json

import httpx


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    async def create_chat_completion(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            reason = exc.response.reason_phrase or "HTTP error"
            raise LLMError(f"HTTP {status_code} {reason}.") from exc
        except httpx.ConnectError as exc:
            raise LLMError(
                f"connection refused ({self._base_url}). Check that Qwen Code API is running."
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"request timed out while calling {self._base_url}/chat/completions."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(str(exc)) from exc

        data = response.json()
        if not isinstance(data, dict):
            raise LLMError("LLM returned an invalid response.")
        return data

    @staticmethod
    def extract_message(response: dict[str, object]) -> dict[str, object]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError("LLM response does not contain choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMError("LLM response choice has an invalid format.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LLMError("LLM response does not contain a message.")
        return message

    @staticmethod
    def tool_call_arguments(tool_call: dict[str, object]) -> dict[str, object]:
        function_payload = tool_call.get("function")
        if not isinstance(function_payload, dict):
            return {}

        raw_arguments = function_payload.get("arguments", "{}")
        if not isinstance(raw_arguments, str):
            return {}
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
        return {}
