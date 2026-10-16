#!/usr/bin/env python3

from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from urllib.parse import urlsplit


try:
    from .conversation_envelope import (
        project as project_envelope,
    )
    from .orobouros_bridge import (
        project_for_message,
    )
    from .persona_session_continuity import (
        previous_traits,
        record as record_persona_receipt,
    )
except ImportError:
    from conversation_envelope import (
        project as project_envelope,
    )
    from orobouros_bridge import (
        project_for_message,
    )
    from persona_session_continuity import (
        previous_traits,
        record as record_persona_receipt,
    )


schema = (
    "savant://runtime/palaver/"
    "conversation-execution-bridge/1.0.0"
)

owner = "exile:palaver"

session_header = (
    "X-Palaver-Session-ID"
)

request_header = (
    "X-Palaver-Request-ID"
)


class conversation_execution_bridge_error(
    RuntimeError
):
    pass


_request_projection: ContextVar[
    dict[str, Any] | None
] = ContextVar(
    "palaver_conversation_execution_projection",
    default=None,
)


def _is_chat(
    handler: Any,
) -> bool:
    path = str(
        getattr(
            handler,
            "path",
            "",
        )
        or ""
    )

    return (
        urlsplit(
            path
        ).path
        == "/api/chat"
    )


def _header(
    handler: Any,
    name: str,
) -> str | None:
    headers = getattr(
        handler,
        "headers",
        None,
    )

    if headers is None:
        return None

    getter = getattr(
        headers,
        "get",
        None,
    )

    if not callable(
        getter
    ):
        return None

    value = getter(
        name
    )

    if value is None:
        value = getter(
            name.lower()
        )

    normalized = str(
        value
        or ""
    ).strip()

    return (
        normalized
        or None
    )


def _safe_body(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def _safe_response(
    value: Any,
) -> dict[str, Any] | None:
    if not isinstance(
        value,
        dict,
    ):
        return None

    return dict(
        value
    )


def install(
    server_module: Any,
    *,
    runtime: Any,
) -> dict[str, Any]:
    current_factory = getattr(
        server_module,
        "make_canonical_handler",
        None,
    )

    if not callable(
        current_factory
    ):
        raise (
            conversation_execution_bridge_error(
                "canonical handler factory unavailable"
            )
        )

    store = getattr(
        runtime,
        "store",
        None,
    )

    if store is None:
        raise (
            conversation_execution_bridge_error(
                "session store unavailable"
            )
        )

    if getattr(
        current_factory,
        "_palaver_conversation_execution_bridge",
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

    def make_handler(
        legacy: Any,
    ):
        base_handler = (
            current_factory(
                legacy
            )
        )

        class conversation_execution_handler(
            base_handler
        ):
            def body_json(
                self,
                *args: Any,
                **kwargs: Any,
            ):
                body = super().body_json(
                    *args,
                    **kwargs,
                )

                if not _is_chat(
                    self
                ):
                    return body

                incoming = _safe_body(
                    body
                )

                message = str(
                    incoming.get(
                        "message"
                    )
                    or ""
                )

                if not message.strip():
                    return body

                session_id = _header(
                    self,
                    session_header,
                )

                request_id = _header(
                    self,
                    request_header,
                )

                prior: tuple[
                    str,
                    ...,
                ] = ()

                if session_id:
                    prior = (
                        previous_traits(
                            store,
                            session_id,
                        )
                    )

                persona = (
                    project_for_message(
                        message,
                        previous_traits=
                            prior,
                    )
                )

                envelope = None

                if (
                    session_id
                    and request_id
                ):
                    envelope = (
                        project_envelope(
                            session_id=
                                session_id,
                            request_id=
                                request_id,
                            message=
                                message,
                            persona=
                                persona,
                        )
                    )

                    receipt = persona.get(
                        "composition_receipt"
                    )

                    if isinstance(
                        receipt,
                        dict,
                    ):
                        record_persona_receipt(
                            store,
                            session_id=
                                session_id,
                            request_id=
                                request_id,
                            receipt=
                                receipt,
                        )

                token = (
                    _request_projection.set(
                        {
                            "persona":
                                persona,
                            "envelope":
                                envelope,
                            "session_id":
                                session_id,
                            "request_id":
                                request_id,
                        }
                    )
                )

                setattr(
                    self,
                    "_palaver_conversation_execution_token",
                    token,
                )

                return body

            def send_json(
                self,
                payload: Any,
                *args: Any,
                **kwargs: Any,
            ):
                projection = (
                    _request_projection.get()
                )

                outgoing = _safe_response(
                    payload
                )

                try:
                    if (
                        projection
                        and outgoing
                        is not None
                    ):
                        persona = (
                            projection.get(
                                "persona"
                            )
                        )

                        envelope = (
                            projection.get(
                                "envelope"
                            )
                        )

                        if isinstance(
                            persona,
                            dict,
                        ):
                            receipt = (
                                persona.get(
                                    "composition_receipt"
                                )
                            )

                            if isinstance(
                                receipt,
                                dict,
                            ):
                                outgoing[
                                    "persona_composition"
                                ] = receipt

                            outgoing[
                                "effective_persona"
                            ] = (
                                persona.get(
                                    "persona_id"
                                )
                                or outgoing.get(
                                    "effective_persona"
                                )
                                or "orobouros"
                            )

                            outgoing[
                                "persona_owner"
                            ] = "envoy"

                        if isinstance(
                            envelope,
                            dict,
                        ):
                            outgoing[
                                "conversation_envelope_digest"
                            ] = (
                                envelope.get(
                                    "envelope_digest"
                                )
                            )

                            outgoing[
                                "conversation_projection_only"
                            ] = True

                    return super().send_json(
                        (
                            outgoing
                            if outgoing
                            is not None
                            else payload
                        ),
                        *args,
                        **kwargs,
                    )

                finally:
                    token = getattr(
                        self,
                        "_palaver_conversation_execution_token",
                        None,
                    )

                    if token is not None:
                        try:
                            _request_projection.reset(
                                token
                            )
                        except Exception:
                            pass

                        try:
                            delattr(
                                self,
                                "_palaver_conversation_execution_token",
                            )
                        except Exception:
                            pass

        return (
            conversation_execution_handler
        )

    setattr(
        make_handler,
        "_palaver_conversation_execution_bridge",
        True,
    )

    server_module.make_canonical_handler = (
        make_handler
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
        "conversation_owner":
            "palaver",
        "persona_owner":
            "envoy",
        "provider_owner":
            "opus",
        "persistent_trait_continuity":
            True,
        "session_receipts":
            True,
        "conversation_envelope":
            True,
        "browser_state_authoritative":
            False,
        "palaver_defines_persona":
            False,
        "palaver_executes_provider":
            False,
        "authority_effect":
            "none",
    }
