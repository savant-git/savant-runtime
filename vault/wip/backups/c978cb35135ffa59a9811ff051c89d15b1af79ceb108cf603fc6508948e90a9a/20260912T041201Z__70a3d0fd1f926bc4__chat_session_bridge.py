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
    "chat-session-bridge/1.0.0"
)

owner = "exile:palaver"

session_header = (
    "X-Palaver-Session-ID"
)

request_header = (
    "X-Palaver-Request-ID"
)


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
        + secrets.token_hex(
            16
        )
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


def _resolve_identity(
    handler: Any,
) -> tuple[
    str,
    str,
]:
    supplied_session = _header(
        handler,
        session_header,
    )

    supplied_request = _header(
        handler,
        request_header,
    )

    resolved_session = (
        session_id(
            supplied_session
        )
        if supplied_session
        else ""
    )

    resolved_request = (
        request_id(
            supplied_request
        )
        if supplied_request
        else _new_request_id()
    )

    return (
        resolved_session,
        resolved_request,
    )


def _response_status(
    handler: Any,
    fallback: int,
) -> int:
    status = getattr(
        handler,
        "_palaver_response_status",
        None,
    )

    if isinstance(
        status,
        int,
    ):
        return status

    return fallback


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
            "schema":
                schema,
            "owner":
                owner,
            "installed":
                True,
            "already_installed":
                True,
            "authority_effect":
                "none",
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
        original_body_json = getattr(
            legacy,
            "body_json",
            None,
        )

        original_send_json = getattr(
            legacy,
            "send_json",
            None,
        )

        if not callable(
            original_body_json
        ):
            raise chat_session_bridge_error(
                "legacy body_json unavailable"
            )

        if not callable(
            original_send_json
        ):
            raise chat_session_bridge_error(
                "legacy send_json unavailable"
            )

        def bridged_body_json(
            handler: Any,
        ) -> Any:
            data = original_body_json(
                handler
            )

            if not _is_chat(
                handler
            ):
                return data

            context = (
                _request_context.get()
            )

            if context is not None:
                return data

            resolved_session, resolved_request = (
                _resolve_identity(
                    handler
                )
            )

            if not resolved_session:
                opened = runtime.open()

                resolved_session = (
                    opened[
                        "session_id"
                    ]
                )
            else:
                runtime.open(
                    resolved_session
                )

            token = _request_context.set(
                {
                    "session_id":
                        resolved_session,
                    "request_id":
                        resolved_request,
                    "terminal":
                        False,
                }
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

        def bridged_send_json(
            handler: Any,
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
                    handler
                )
            ):
                return original_send_json(
                    handler,
                    payload,
                    status,
                    *args,
                    **kwargs,
                )

            resolved_session = (
                context[
                    "session_id"
                ]
            )

            resolved_request = (
                context[
                    "request_id"
                ]
            )

            terminal = bool(
                context.get(
                    "terminal",
                    False,
                )
            )

            if not terminal:
                successful = (
                    200
                    <= int(
                        status
                    )
                    < 400
                    and isinstance(
                        payload,
                        dict,
                    )
                    and payload.get(
                        "ok"
                    )
                    is not False
                )

                if successful:
                    runtime.publish(
                        session=
                            resolved_session,
                        request=
                            resolved_request,
                        kind=
                            "response.completed",
                        payload={
                            "status":
                                int(
                                    status
                                ),
                            "response":
                                payload,
                        },
                        dedupe_key=
                            "response.completed",
                    )
                else:
                    error_code = (
                        payload.get(
                            "error_code"
                        )
                        if isinstance(
                            payload,
                            dict,
                        )
                        else None
                    )

                    retryable = (
                        bool(
                            payload.get(
                                "retryable",
                                False,
                            )
                        )
                        if isinstance(
                            payload,
                            dict,
                        )
                        else False
                    )

                    runtime.publish(
                        session=
                            resolved_session,
                        request=
                            resolved_request,
                        kind=
                            "response.failed",
                        payload={
                            "status":
                                int(
                                    status
                                ),
                            "error_code":
                                error_code,
                            "retryable":
                                retryable,
                        },
                        dedupe_key=
                            "response.failed",
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
                return original_send_json(
                    handler,
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

        legacy.body_json = (
            bridged_body_json
        )

        legacy.send_json = (
            bridged_send_json
        )

        try:
            handler_class = (
                original_factory(
                    legacy
                )
            )

        finally:
            legacy.body_json = (
                original_body_json
            )

            legacy.send_json = (
                original_send_json
            )

        return handler_class

    chat_session_factory.__name__ = (
        "make_chat_session_canonical_handler"
    )

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
        "schema":
            schema,
        "owner":
            owner,
        "installed":
            True,
        "already_installed":
            False,
        "route":
            "/api/chat",
        "session_header":
            session_header,
        "request_header":
            request_header,
        "generated_session_identity":
            True,
        "generated_request_identity":
            True,
        "events": [
            "request.accepted",
            "request.started",
            "response.completed",
            "response.failed",
        ],
        "conversation_owner":
            "palaver",
        "provider_owner":
            "opus",
        "provider_execution_modified":
            False,
        "chat_contract_modified":
            False,
        "authority_effect":
            "none",
    }
