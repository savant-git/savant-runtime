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
    "api/http/1.1.0"
)

OWNER = "exile:opus"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

CHAT_COMPLETIONS_PATH = (
    "/v1/chat/completions"
)

MAX_REQUEST_BYTES = (
    4 * 1024 * 1024
)

MAX_AUTHORIZATION_BYTES = 8192

JSON_CONTENT_TYPES = frozenset(
    {
        "application/json",
    }
)


class ApiHttpError(
    RuntimeError
):
    def __init__(
        self,
        status: int,
        message: str,
        error_type: str,
        *,
        code: str | None = None,
    ) -> None:
        super().__init__(
            message
        )

        self.status = status
        self.message = message
        self.error_type = error_type
        self.code = code


def _error_body(
    message: str,
    error_type: str,
    *,
    code: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    body = {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": code,
        }
    }

    if request_id:
        body[
            "opus"
        ] = {
            "request_id": request_id,
            "authority_effect": "none",
        }

    return body


def _request_id(
    supplied: str | None,
) -> str:
    value = str(
        supplied or ""
    ).strip()

    if (
        value
        and len(value) <= 128
        and all(
            character.isalnum()
            or character
            in "-_.:"
            for character in value
        )
    ):
        return value

    return (
        "opusreq_"
        + uuid.uuid4().hex
    )


def _content_type(
    value: str | None,
) -> str:
    return str(
        value or ""
    ).split(
        ";",
        1,
    )[0].strip().lower()


def bearer_secret(
    authorization: str | None,
) -> str:
    value = str(
        authorization or ""
    ).strip()

    if len(
        value.encode(
            "utf-8"
        )
    ) > MAX_AUTHORIZATION_BYTES:
        raise ApiHttpError(
            401,
            "missing or invalid bearer token",
            "authentication_error",
            code="invalid_api_key",
        )

    prefix = "Bearer "

    if not value.startswith(
        prefix
    ):
        raise ApiHttpError(
            401,
            "missing or invalid bearer token",
            "authentication_error",
            code="invalid_api_key",
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
            code="invalid_api_key",
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
            code="invalid_provider_response",
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
    request_id: str | None = None,
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

    opus_projection = {
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
    }

    if request_id:
        opus_projection[
            "request_id"
        ] = request_id

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
        "opus": opus_projection,
    }


def dispatch_chat_completion(
    *,
    authorization: str | None,
    payload: Mapping[str, Any],
    request_id: str | None = None,
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
            code="invalid_api_key",
        ) from exc

    except ApiRequestError as exc:
        raise ApiHttpError(
            400,
            str(
                exc
            ),
            "invalid_request_error",
            code="invalid_request",
        ) from exc

    return openai_chat_response(
        result,
        requested_model=str(
            payload.get(
                "model"
            )
            or "opus:auto"
        ),
        request_id=request_id,
    )


class OpusApiHandler(
    BaseHTTPRequestHandler
):
    server_version = "opus-api/1.1"

    protocol_version = "HTTP/1.1"

    def _json(
        self,
        status: int,
        body: Mapping[str, Any],
        *,
        request_id: str | None = None,
    ) -> None:
        encoded = json.dumps(
            body,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
            allow_nan=False,
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
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

        self.send_header(
            "Pragma",
            "no-cache",
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )

        self.send_header(
            "Referrer-Policy",
            "no-referrer",
        )

        if request_id:
            self.send_header(
                "X-Request-ID",
                request_id,
            )

        self.end_headers()

        self.wfile.write(
            encoded
        )

    def _current_request_id(
        self,
    ) -> str:
        return _request_id(
            self.headers.get(
                "X-Request-ID"
            )
        )

    def do_GET(
        self,
    ) -> None:
        request_id = (
            self._current_request_id()
        )

        if self.path == "/health":
            self._json(
                200,
                {
                    "status": "ok",
                    "owner": OWNER,
                    "authority_effect": "none",
                    "request_id": request_id,
                },
                request_id=request_id,
            )

            return

        self._json(
            404,
            _error_body(
                "not found",
                "not_found_error",
                code="not_found",
                request_id=request_id,
            ),
            request_id=request_id,
        )

    def do_POST(
        self,
    ) -> None:
        request_id = (
            self._current_request_id()
        )

        if self.path != CHAT_COMPLETIONS_PATH:
            self._json(
                404,
                _error_body(
                    "not found",
                    "not_found_error",
                    code="not_found",
                    request_id=request_id,
                ),
                request_id=request_id,
            )

            return

        try:
            content_type = _content_type(
                self.headers.get(
                    "Content-Type"
                )
            )

            if (
                content_type
                not in JSON_CONTENT_TYPES
            ):
                raise ApiHttpError(
                    415,
                    "content type must be "
                    "application/json",
                    "invalid_request_error",
                    code="unsupported_media_type",
                )

            raw_content_length = (
                self.headers.get(
                    "Content-Length"
                )
            )

            if raw_content_length is None:
                raise ApiHttpError(
                    411,
                    "content length is required",
                    "invalid_request_error",
                    code="length_required",
                )

            try:
                content_length = int(
                    raw_content_length
                )

            except (
                TypeError,
                ValueError,
            ) as exc:
                raise ApiHttpError(
                    400,
                    "invalid content length",
                    "invalid_request_error",
                    code="invalid_content_length",
                ) from exc

            if content_length <= 0:
                raise ApiHttpError(
                    400,
                    "request body is required",
                    "invalid_request_error",
                    code="empty_request_body",
                )

            if (
                content_length
                > MAX_REQUEST_BYTES
            ):
                raise ApiHttpError(
                    413,
                    "request body exceeds "
                    "maximum size",
                    "invalid_request_error",
                    code="request_too_large",
                )

            raw = self.rfile.read(
                content_length
            )

            if len(
                raw
            ) != content_length:
                raise ApiHttpError(
                    400,
                    "incomplete request body",
                    "invalid_request_error",
                    code="incomplete_request_body",
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
                    code="invalid_json",
                ) from exc

            if not isinstance(
                payload,
                dict,
            ):
                raise ApiHttpError(
                    400,
                    "request body must be a json object",
                    "invalid_request_error",
                    code="invalid_request_object",
                )

            response = (
                dispatch_chat_completion(
                    authorization=(
                        self.headers.get(
                            "Authorization"
                        )
                    ),
                    payload=payload,
                    request_id=request_id,
                )
            )

            self._json(
                200,
                response,
                request_id=request_id,
            )

        except ApiHttpError as exc:
            self._json(
                exc.status,
                _error_body(
                    exc.message,
                    exc.error_type,
                    code=exc.code,
                    request_id=request_id,
                ),
                request_id=request_id,
            )

        except Exception:
            self._json(
                500,
                _error_body(
                    "internal opus api error",
                    "internal_error",
                    code="internal_error",
                    request_id=request_id,
                ),
                request_id=request_id,
            )

    def log_message(
        self,
        format: str,
        *args: Any,
    ) -> None:
        return


class OpusApiServer(
    ThreadingHTTPServer
):
    daemon_threads = True

    allow_reuse_address = True


def serve(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    server = OpusApiServer(
        (
            host,
            port,
        ),
        OpusApiHandler,
    )

    try:
        server.serve_forever()

    finally:
        server.server_close()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
