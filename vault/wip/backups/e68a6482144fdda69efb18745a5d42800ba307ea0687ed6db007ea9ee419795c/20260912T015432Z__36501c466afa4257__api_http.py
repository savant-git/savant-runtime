from __future__ import annotations

import json
import time
import uuid
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any, Mapping

from .api_request import (
    ApiAuthenticationError,
    ApiRequestError,
    execute_authenticated_text,
)


SCHEMA = (
    "savant://runtime/opus/"
    "api/http/1.0.0"
)

OWNER = "exile:opus"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

CHAT_COMPLETIONS_PATH = (
    "/v1/chat/completions"
)


class ApiHttpError(
    RuntimeError
):
    def __init__(
        self,
        status: int,
        message: str,
        error_type: str,
    ) -> None:
        super().__init__(
            message
        )

        self.status = status
        self.message = message
        self.error_type = error_type


def _error_body(
    message: str,
    error_type: str,
) -> dict[str, Any]:
    return {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": None,
        }
    }


def bearer_secret(
    authorization: str | None,
) -> str:
    value = str(
        authorization or ""
    ).strip()

    prefix = "Bearer "

    if not value.startswith(
        prefix
    ):
        raise ApiHttpError(
            401,
            "missing or invalid bearer token",
            "authentication_error",
        )

    secret = value[
        len(
            prefix
        ):
    ].strip()

    if not secret:
        raise ApiHttpError(
            401,
            "missing or invalid bearer token",
            "authentication_error",
        )

    return secret


def _choice_message(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    choices = result.get(
        "choices"
    )

    if (
        isinstance(
            choices,
            list,
        )
        and choices
        and isinstance(
            choices[0],
            Mapping,
        )
    ):
        message = choices[
            0
        ].get(
            "message"
        )

        if isinstance(
            message,
            Mapping,
        ):
            return dict(
                message
            )

    message = result.get(
        "message"
    )

    if isinstance(
        message,
        Mapping,
    ):
        return dict(
            message
        )

    content = result.get(
        "content"
    )

    if content is None:
        content = result.get(
            "text"
        )

    if content is None:
        content = result.get(
            "output"
        )

    if content is None:
        raise ApiHttpError(
            502,
            "opus provider result contains "
            "no compatible text output",
            "provider_response_error",
        )

    return {
        "role": "assistant",
        "content": str(
            content
        ),
    }


def openai_chat_response(
    result: Mapping[str, Any],
    *,
    requested_model: str | None = None,
) -> dict[str, Any]:
    lineage = result.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        Mapping,
    ):
        lineage = {}

    model = (
        lineage.get(
            "model"
        )
        or result.get(
            "model"
        )
        or requested_model
        or "opus:auto"
    )

    usage = result.get(
        "usage"
    )

    if not isinstance(
        usage,
        Mapping,
    ):
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    return {
        "id": str(
            result.get(
                "id"
            )
            or (
                "chatcmpl-"
                + uuid.uuid4().hex
            )
        ),
        "object": "chat.completion",
        "created": int(
            time.time()
        ),
        "model": str(
            model
        ),
        "choices": [
            {
                "index": 0,
                "message": _choice_message(
                    result
                ),
                "finish_reason": result.get(
                    "finish_reason",
                    "stop",
                ),
            }
        ],
        "usage": dict(
            usage
        ),
        "opus": {
            "schema": SCHEMA,
            "owner": OWNER,
            "route": lineage.get(
                "route",
                "text_inference_route",
            ),
            "provider": lineage.get(
                "provider"
            ),
            "authority_effect": "none",
        },
    }


def dispatch_chat_completion(
    *,
    authorization: str | None,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    secret = bearer_secret(
        authorization
    )

    try:
        result = (
            execute_authenticated_text(
                secret=secret,
                payload=payload,
            )
        )

    except ApiAuthenticationError as exc:
        raise ApiHttpError(
            401,
            str(
                exc
            ),
            "authentication_error",
        ) from exc

    except ApiRequestError as exc:
        raise ApiHttpError(
            400,
            str(
                exc
            ),
            "invalid_request_error",
        ) from exc

    return openai_chat_response(
        result,
        requested_model=str(
            payload.get(
                "model"
            )
            or "opus:auto"
        ),
    )


class OpusApiHandler(
    BaseHTTPRequestHandler
):
    server_version = "opus-api/1.0"

    def _json(
        self,
        status: int,
        body: Mapping[str, Any],
    ) -> None:
        encoded = json.dumps(
            body,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    encoded
                )
            ),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            encoded
        )

    def do_GET(
        self,
    ) -> None:
        if self.path == "/health":
            self._json(
                200,
                {
                    "status": "ok",
                    "owner": OWNER,
                    "authority_effect": "none",
                },
            )

            return

        self._json(
            404,
            _error_body(
                "not found",
                "not_found_error",
            ),
        )

    def do_POST(
        self,
    ) -> None:
        if self.path != CHAT_COMPLETIONS_PATH:
            self._json(
                404,
                _error_body(
                    "not found",
                    "not_found_error",
                ),
            )

            return

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if content_length <= 0:
                raise ApiHttpError(
                    400,
                    "request body is required",
                    "invalid_request_error",
                )

            raw = self.rfile.read(
                content_length
            )

            try:
                payload = json.loads(
                    raw.decode(
                        "utf-8"
                    )
                )

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise ApiHttpError(
                    400,
                    "request body must be valid json",
                    "invalid_request_error",
                ) from exc

            if not isinstance(
                payload,
                dict,
            ):
                raise ApiHttpError(
                    400,
                    "request body must be a json object",
                    "invalid_request_error",
                )

            response = (
                dispatch_chat_completion(
                    authorization=(
                        self.headers.get(
                            "Authorization"
                        )
                    ),
                    payload=payload,
                )
            )

            self._json(
                200,
                response,
            )

        except ApiHttpError as exc:
            self._json(
                exc.status,
                _error_body(
                    exc.message,
                    exc.error_type,
                ),
            )

        except Exception:
            self._json(
                500,
                _error_body(
                    "internal opus api error",
                    "internal_error",
                ),
            )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return


def serve(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    server = ThreadingHTTPServer(
        (
            host,
            port,
        ),
        OpusApiHandler,
    )

    server.serve_forever()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
