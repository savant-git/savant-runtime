from __future__ import annotations

import json
from typing import Any, Mapping

from .session_api import session_api


schema = "savant://runtime/urge/session-http/1.0.0"
owner = "exile:urge"

path = "/api/urge/session"
max_body_bytes = 65536

actions = frozenset(
    {
        "start",
        "snapshot",
        "pause",
        "resume",
        "cancel",
        "release",
    }
)


class session_http_error(ValueError):
    pass


class session_http:
    def __init__(
        self,
        *,
        api: session_api,
    ) -> None:
        if not isinstance(api, session_api):
            raise session_http_error(
                "api must be an urge session_api"
            )

        self._api = api

    @staticmethod
    def _response(
        status: int,
        body: Mapping[str, Any],
    ) -> tuple[int, dict[str, str], bytes]:
        encoded = json.dumps(
            body,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return (
            status,
            {
                "Content-Type": (
                    "application/json; charset=utf-8"
                ),
                "Content-Length": str(len(encoded)),
                "Cache-Control": "no-store",
            },
            encoded,
        )

    @staticmethod
    def _error(
        status: int,
        message: str,
    ) -> tuple[int, dict[str, str], bytes]:
        return session_http._response(
            status,
            {
                "ok": False,
                "schema": schema,
                "owner": owner,
                "error": {
                    "type": "session_http_error",
                    "message": message,
                },
            },
        )

    def dispatch(
        self,
        *,
        method: str,
        request_path: str,
        body: bytes,
        authorized: bool = False,
    ) -> (
        tuple[int, dict[str, str], bytes] | None
    ):
        if request_path != path:
            return None

        if not authorized:
            return self._error(
                403,
                "session access denied",
            )

        if method != "POST":
            return self._error(
                405,
                "method not allowed",
            )

        if not isinstance(body, bytes):
            return self._error(
                400,
                "request body must be bytes",
            )

        if len(body) > max_body_bytes:
            return self._error(
                413,
                "request body exceeds limit",
            )

        try:
            request = json.loads(
                body.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return self._error(
                400,
                "invalid json request",
            )

        if not isinstance(request, dict):
            return self._error(
                400,
                "request must be an object",
            )

        action = request.get("action")
        payload = request.get("payload")

        if action not in actions:
            return self._error(
                400,
                "unsupported session action",
            )

        if not isinstance(payload, dict):
            return self._error(
                400,
                "payload must be an object",
            )

        try:
            result = self._api.safe_dispatch(
                action=action,
                payload=payload,
            )
        except Exception:
            return self._error(
                500,
                "session dispatch failed",
            )

        if not result["ok"]:
            return self._response(
                400,
                result,
            )

        try:
            return self._response(
                200,
                result,
            )
        except (
            TypeError,
            ValueError,
        ):
            return self._error(
                500,
                "session response is not serializable",
            )
