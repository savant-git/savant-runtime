from __future__ import annotations

import contextvars
import secrets
from typing import Any
from urllib.parse import urlparse

try:
    from .conversation_transport import (
        request_id,
        session_id,
    )
    from .session_runtime import (
        session_runtime,
    )
except ImportError:
    from conversation_transport import (
        request_id,
        session_id,
    )
    from session_runtime import (
        session_runtime,
    )


schema = (
    "savant://runtime/palaver/"
    "chat-session-bridge/1.0.1"
)

owner = "exile:palaver"

session_header = "X-Palaver-Session-ID"
request_header = "X-Palaver-Request-ID"


class chat_session_bridge_error(
    RuntimeError
):
    pass


_request_context: contextvars.ContextVar[
    dict[str, Any] | None
] = contextvars.ContextVar(
    "palaver_chat_session_context",
    default=None,
)


def _new_request_id() -> str:
    return (
        "palreq_"
        + secrets.token_hex(16)
    )


def _is_chat(
    handler: Any,
) -> bool:
    return (
        urlparse(
            str(
                getattr(
                    handler,
                    "path",
                    "",
                )
            )
        ).path
        == "/api/chat"
    )


def _header(
    handler: Any,
    name: str,
) -> str:
    headers = getattr(
        handler,
        "headers",
        None,
    )

    if headers is None:
        return ""

    return str(
        headers.get(
            name,
            "",
        )
        or ""
    ).strip()


def _completion_payload(
    payload: Any,
    status: int,
) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "status": int(status),
    }

    if not isinstance(
        payload,
        dict,
    ):
        return projected

    for key in (
        "answer",
        "response",
        "error",
        "error_code",
        "retryable",
        "persona_id",
        "effective_persona",
        "provider_owner",
        "conversation_owner",
        "context_receipt",
    ):
        if key in payload:
            projected[key] = (
                payload[key]
            )

    return projected


def install(
    server_module: Any,
    *,
    runtime: session_runtime,
) -> dict[str, Any]:
    if getattr(
        server_module,
        "_palaver_chat_session_bridge_installed",
        False,
    ):
        return {
            "schema": schema,
            "owner": owner,
            "installed": True,
            "already_installed": True,
            "authority_effect": "none",
        }

    original_factory = getattr(
        server_module,
        "make_canonical_handler",
        None,
    )

    if not callable(
        original_factory
    ):
        raise chat_session_bridge_error(
            "canonical handler factory unavailable"
        )

    def chat_session_factory(
        legacy: Any,
    ):
        base_handler = (
            original_factory(
                legacy
            )
        )

        class chat_session_handler(
            base_handler
        ):
            def body_json(
                self,
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                data = super().body_json(
                    *args,
                    **kwargs,
                )

                if not _is_chat(
                    self
                ):
                    return data

                if (
                    _request_context.get()
                    is not None
                ):
                    return data

                raw_session = _header(
                    self,
                    session_header,
                )

                raw_request = _header(
                    self,
                    request_header,
                )

                if raw_session:
                    resolved_session = (
                        session_id(
                            raw_session
                        )
                    )

                    runtime.open(
                        resolved_session
                    )
                else:
                    opened = (
                        runtime.open()
                    )

                    resolved_session = str(
                        opened[
                            "session_id"
                        ]
                    )

                resolved_request = (
                    request_id(
                        raw_request
                    )
                    if raw_request
                    else _new_request_id()
                )

                token = (
                    _request_context.set(
                        {
                            "session_id":
                                resolved_session,
                            "request_id":
                                resolved_request,
                            "terminal":
                                False,
                        }
                    )
                )

                context = (
                    _request_context.get()
                )

                if context is not None:
                    context[
                        "token"
                    ] = token

                runtime.publish(
                    session=
                        resolved_session,
                    request=
                        resolved_request,
                    kind=
                        "request.accepted",
                    payload={
                        "transport":
                            "http",
                        "route":
                            "/api/chat",
                    },
                    dedupe_key=
                        "request.accepted",
                )

                runtime.publish(
                    session=
                        resolved_session,
                    request=
                        resolved_request,
                    kind=
                        "request.started",
                    payload={
                        "transport":
                            "http",
                        "route":
                            "/api/chat",
                    },
                    dedupe_key=
                        "request.started",
                )

                return data

            def send_json(
                self,
                payload: Any,
                status: int = 200,
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                context = (
                    _request_context.get()
                )

                if (
                    context is None
                    or not _is_chat(
                        self
                    )
                ):
                    return super().send_json(
                        payload,
                        status,
                        *args,
                        **kwargs,
                    )

                resolved_session = str(
                    context[
                        "session_id"
                    ]
                )

                resolved_request = str(
                    context[
                        "request_id"
                    ]
                )

                if not bool(
                    context.get(
                        "terminal",
                        False,
                    )
                ):
                    successful = (
                        200 <= int(status) < 400
                        and (
                            not isinstance(
                                payload,
                                dict,
                            )
                            or payload.get(
                                "ok"
                            )
                            is not False
                        )
                    )

                    runtime.publish(
                        session=
                            resolved_session,
                        request=
                            resolved_request,
                        kind=(
                            "response.completed"
                            if successful
                            else "response.failed"
                        ),
                        payload=
                            _completion_payload(
                                payload,
                                int(status),
                            ),
                        dedupe_key=(
                            "response.completed"
                            if successful
                            else "response.failed"
                        ),
                    )

                    context[
                        "terminal"
                    ] = True

                if isinstance(
                    payload,
                    dict,
                ):
                    outgoing = dict(
                        payload
                    )

                    outgoing.setdefault(
                        "session_id",
                        resolved_session,
                    )

                    outgoing.setdefault(
                        "request_id",
                        resolved_request,
                    )

                    outgoing.setdefault(
                        "session_owner",
                        "palaver",
                    )
                else:
                    outgoing = payload

                try:
                    return super().send_json(
                        outgoing,
                        status,
                        *args,
                        **kwargs,
                    )

                finally:
                    token = context.get(
                        "token"
                    )

                    if token is not None:
                        try:
                            _request_context.reset(
                                token
                            )
                        except (
                            LookupError,
                            ValueError,
                        ):
                            _request_context.set(
                                None
                            )

        chat_session_handler.__name__ = (
            "palaver_chat_session_handler"
        )

        return chat_session_handler

    server_module.make_canonical_handler = (
        chat_session_factory
    )

    server_module._palaver_chat_session_bridge_installed = (
        True
    )

    server_module._palaver_chat_session_runtime = (
        runtime
    )

    return {
        "schema": schema,
        "owner": owner,
        "installed": True,
        "already_installed": False,
        "route": "/api/chat",
        "session_header":
            session_header,
        "request_header":
            request_header,
        "events": [
            "request.accepted",
            "request.started",
            "response.completed",
            "response.failed",
        ],
        "persistent_session_projection":
            True,
        "raw_diagnostics_persisted":
            False,
        "conversation_owner":
            "palaver",
        "provider_owner":
            "opus",
        "chat_contract_modified":
            False,
        "authority_effect":
            "none",
    }
