
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any


class provider_transport_error(RuntimeError):
    pass


class provider_transport:
    def __init__(
        self,
        *,
        timeout_seconds: float = 90.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout must be positive")

        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _credential(name: str) -> str:
        if not isinstance(name, str) or not name:
            raise provider_transport_error(
                "credential variable is required"
            )

        value = os.environ.get(name)

        if not value:
            raise provider_transport_error(
                "provider credential is not configured"
            )

        return value

    @staticmethod
    def _content(response: Mapping[str, Any]) -> str:
        choices = response.get("choices")

        if not isinstance(choices, list) or not choices:
            raise provider_transport_error(
                "provider returned no choices"
            )

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            return "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, Mapping)
                and item.get("type") == "text"
            ).strip()

        raise provider_transport_error(
            "provider returned unsupported content"
        )

    def _invoke(
        self,
        *,
        endpoint: str,
        credential_variable: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> dict[str, Any]:
        if not endpoint.startswith("https://"):
            raise provider_transport_error(
                "provider endpoint must use HTTPS"
            )

        if not model.strip():
            raise provider_transport_error(
                "provider model is required"
            )

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        body = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": (
                    "Bearer "
                    + self._credential(
                        credential_variable
                    )
                ),
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as connection:
                raw = connection.read(16 * 1024 * 1024)

        except urllib.error.HTTPError as exc:
            raise provider_transport_error(
                f"provider returned HTTP {exc.code}"
            ) from None

        except urllib.error.URLError as exc:
            raise provider_transport_error(
                "provider connection failed"
            ) from None

        try:
            response = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise provider_transport_error(
                "provider returned invalid JSON"
            ) from exc

        if not isinstance(response, Mapping):
            raise provider_transport_error(
                "provider returned invalid response"
            )

        text = self._content(response)

        if not text:
            raise provider_transport_error(
                "provider returned empty text"
            )

        usage = response.get("usage", {})

        if not isinstance(usage, Mapping):
            usage = {}

        return {
            "result": text,
            "response_id": response.get("id"),
            "model": response.get("model", model),
            "finish_reason": response["choices"][0].get(
                "finish_reason"
            ),
            "usage": dict(usage),
        }

    async def invoke(
        self,
        *,
        endpoint: str,
        credential_variable: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._invoke,
            endpoint=endpoint,
            credential_variable=credential_variable,
            model=model,
            messages=messages,
            temperature=temperature,
        )
