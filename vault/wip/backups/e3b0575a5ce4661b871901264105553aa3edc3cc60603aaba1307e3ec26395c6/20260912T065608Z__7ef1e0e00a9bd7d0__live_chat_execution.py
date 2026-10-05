#!/usr/bin/env python3

from __future__ import annotations

from contextvars import ContextVar
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping
from urllib.parse import urlparse


schema = (
    "savant://runtime/palaver/"
    "live-chat-execution/1.0.1"
)

owner = "exile:palaver"
provider_owner = "exile:opus"
persona_owner = "exile:envoy"
authority_effect = "none"


runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/palaver/runtime"
)

integration_path = (
    runtime_root
    / "chat_execution_integration.py"
)

module_name = (
    "savant_palaver_chat_execution_integration"
)


_EXECUTION_CONTEXT: ContextVar[
    Any | None
] = ContextVar(
    "palaver_live_chat_execution_context",
    default=None,
)

_REQUEST_ENVELOPE: ContextVar[
    dict[str, str] | None
] = ContextVar(
    "palaver_live_chat_request_envelope",
    default=None,
)


class live_chat_execution_error(
    RuntimeError
):
    pass


def _load_integration():
    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    if not integration_path.is_file():
        raise live_chat_execution_error(
            "chat execution integration is missing"
        )

    specification = (
        importlib.util.spec_from_file_location(
            module_name,
            integration_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise live_chat_execution_error(
            "chat execution integration "
            "could not be loaded"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        module_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            module_name,
            None,
        )
        raise

    return module


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _headers_request_id(
    handler: Any,
) -> str:
    headers = getattr(
        handler,
        "headers",
        None,
    )

    if headers is None:
        return ""

    for name in (
        "X-Palaver-Request-ID",
        "X-Request-ID",
    ):
        value = _text(
            headers.get(
                name
            )
        )

        if value:
            return value

    return ""


def _handler_path(
    handler: Any,
) -> str:
    return urlparse(
        _text(
            getattr(
                handler,
                "path",
                "",
            )
        )
    ).path


def _capture_request_envelope(
    handler: Any,
    payload: Any,
) -> None:
    if (
        _handler_path(
            handler
        )
        != "/api/chat"
    ):
        return

    if not isinstance(
        payload,
        Mapping,
    ):
        _REQUEST_ENVELOPE.set(
            None
        )
        return

    session_id = _text(
        payload.get(
            "session_id"
        )
    )

    request_id = (
        _headers_request_id(
            handler
        )
    )

    _REQUEST_ENVELOPE.set(
        {
            "session_id":
                session_id,
            "request_id":
                request_id,
        }
    )


def _install_body_capture(
    legacy: ModuleType,
) -> None:
    original = getattr(
        legacy,
        "body_json",
        None,
    )

    if not callable(
        original
    ):
        raise live_chat_execution_error(
            "legacy body_json callable is missing"
        )

    if getattr(
        original,
        "_palaver_live_execution_capture",
        False,
    ):
        return

    def body_json_with_capture(
        handler: Any,
    ):
        payload = original(
            handler
        )

        _capture_request_envelope(
            handler,
            payload,
        )

        return payload

    body_json_with_capture.__name__ = (
        getattr(
            original,
            "__name__",
            "body_json",
        )
    )

    body_json_with_capture.__doc__ = (
        getattr(
            original,
            "__doc__",
            None,
        )
    )

    body_json_with_capture._palaver_live_execution_capture = (
        True
    )

    body_json_with_capture._palaver_original_body_json = (
        original
    )

    legacy.body_json = (
        body_json_with_capture
    )


def _persona_projection(
    legacy: ModuleType,
    persona_id: str,
    message: str,
) -> dict[str, Any]:
    projector = getattr(
        legacy,
        "palaver_envoy_project_persona",
        None,
    )

    if not callable(
        projector
    ):
        return {}

    try:
        projection = projector(
            persona_id
        )

    except TypeError:
        projection = projector(
            persona_id,
            signals=(),
        )

    if not isinstance(
        projection,
        Mapping,
    ):
        return {}

    return dict(
        projection
    )


def _active_traits(
    projection: Mapping[
        str,
        Any,
    ],
) -> tuple[str, ...]:
    traits = (
        projection.get(
            "traits"
        )
        or projection.get(
            "active_traits"
        )
        or ()
    )

    values: set[str] = set()

    for item in traits:
        if isinstance(
            item,
            Mapping,
        ):
            trait_id = _text(
                item.get(
                    "id"
                )
                or item.get(
                    "trait_id"
                )
            )

        else:
            trait_id = _text(
                item
            )

        if trait_id:
            values.add(
                trait_id
            )

    return tuple(
        sorted(
            values
        )
    )


def current_context():
    return (
        _EXECUTION_CONTEXT.get()
    )


def current_request_envelope(
) -> dict[str, str]:
    envelope = (
        _REQUEST_ENVELOPE.get()
    )

    return dict(
        envelope
        or {}
    )


def install(
    legacy: ModuleType,
    *,
    selected_persona: callable,
) -> dict[str, Any]:
    _install_body_capture(
        legacy
    )

    original_chat = getattr(
        legacy,
        "chat",
        None,
    )

    if not callable(
        original_chat
    ):
        raise live_chat_execution_error(
            "legacy chat callable is missing"
        )

    if getattr(
        original_chat,
        "_palaver_live_execution",
        False,
    ):
        return {
            "schema":
                schema,
            "installed":
                True,
            "already_installed":
                True,
            "owner":
                owner,
            "authority_effect":
                authority_effect,
        }

    integration = (
        _load_integration()
    )

    def chat_with_execution(
        message: str,
        *args: Any,
        **kwargs: Any,
    ):
        persona_id = _text(
            selected_persona()
        )

        projection = (
            _persona_projection(
                legacy,
                persona_id,
                message,
            )
        )

        envelope = (
            current_request_envelope()
        )

        composition_digest = _text(
            projection.get(
                "composition_digest"
            )
            or projection.get(
                "composition_id"
            )
        )

        context = integration.begin(
            message=
                message,
            session_id=
                _text(
                    envelope.get(
                        "session_id"
                    )
                ),
            request_id=(
                _text(
                    envelope.get(
                        "request_id"
                    )
                )
                or None
            ),
            persona_id=
                persona_id,
            persona_composition_digest=
                composition_digest,
            active_traits=
                _active_traits(
                    projection
                ),
        )

        token = (
            _EXECUTION_CONTEXT.set(
                context
            )
        )

        try:
            result = original_chat(
                message,
                *args,
                **kwargs,
            )

            if not isinstance(
                result,
                Mapping,
            ):
                integration.fail(
                    context=
                        context,
                    error_code=
                        "invalid_chat_result",
                )

                return result

            return integration.complete(
                context=
                    context,
                result=
                    result,
                metadata={
                    "live_chat_wrapper":
                        schema,
                    "request_identity_source":
                        (
                            "header"
                            if _text(
                                envelope.get(
                                    "request_id"
                                )
                            )
                            else (
                                "compatibility_projection"
                            )
                        ),
                    "session_identity_source":
                        (
                            "contract_payload"
                            if _text(
                                envelope.get(
                                    "session_id"
                                )
                            )
                            else "unavailable"
                        ),
                },
            )

        except Exception as exc:
            try:
                integration.fail(
                    context=
                        context,
                    error_code=(
                        getattr(
                            exc,
                            "code",
                            None,
                        )
                        or "chat_execution_failed"
                    ),
                    diagnostic=
                        str(
                            exc
                        ),
                    metadata={
                        "live_chat_wrapper":
                            schema,
                    },
                )

            finally:
                raise

        finally:
            _EXECUTION_CONTEXT.reset(
                token
            )

            _REQUEST_ENVELOPE.set(
                None
            )

    chat_with_execution.__name__ = (
        getattr(
            original_chat,
            "__name__",
            "chat",
        )
    )

    chat_with_execution.__doc__ = (
        getattr(
            original_chat,
            "__doc__",
            None,
        )
    )

    chat_with_execution._palaver_live_execution = (
        True
    )

    chat_with_execution._palaver_original_chat = (
        original_chat
    )

    legacy.chat = (
        chat_with_execution
    )

    return {
        "schema":
            schema,
        "installed":
            True,
        "already_installed":
            False,
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "persona_owner":
            persona_owner,
        "contract_session_binding":
            True,
        "request_header_binding":
            True,
        "outcome_capture":
            True,
        "provider_lifecycle":
            True,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


def status(
    legacy: ModuleType,
) -> dict[str, Any]:
    chat_target = getattr(
        legacy,
        "chat",
        None,
    )

    body_target = getattr(
        legacy,
        "body_json",
        None,
    )

    return {
        "schema":
            schema,
        "installed":
            bool(
                callable(
                    chat_target
                )
                and getattr(
                    chat_target,
                    "_palaver_live_execution",
                    False,
                )
            ),
        "request_capture_installed":
            bool(
                callable(
                    body_target
                )
                and getattr(
                    body_target,
                    "_palaver_live_execution_capture",
                    False,
                )
            ),
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "persona_owner":
            persona_owner,
        "contract_session_binding":
            True,
        "request_header_binding":
            True,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    class headers_test(
        dict
    ):
        pass

    class handler_test:
        path = "/api/chat"

        headers = headers_test(
            {
                "X-Request-ID":
                    "request-test",
            }
        )

    class legacy_test:
        @staticmethod
        def body_json(
            _: Any,
        ):
            return {
                "message":
                    "test",
                "session_id":
                    "session-test",
            }

        @staticmethod
        def chat(
            message: str,
        ):
            return {
                "answer":
                    f"answer:{message}",
                "response":
                    f"answer:{message}",
            }

        @staticmethod
        def palaver_envoy_project_persona(
            persona_id: str,
            **_: Any,
        ):
            return {
                "persona_id":
                    persona_id,
                "composition_digest":
                    "composition-test",
                "traits": [
                    {
                        "id":
                            "planning",
                    }
                ],
            }

    legacy = (
        legacy_test()
    )

    installed = install(
        legacy,
        selected_persona=lambda: (
            "orobouros"
        ),
    )

    if not installed.get(
        "installed"
    ):
        raise live_chat_execution_error(
            "installation failed"
        )

    payload = legacy.body_json(
        handler_test()
    )

    if (
        payload.get(
            "session_id"
        )
        != "session-test"
    ):
        raise live_chat_execution_error(
            "body payload changed"
        )

    envelope = (
        current_request_envelope()
    )

    if (
        envelope.get(
            "session_id"
        )
        != "session-test"
    ):
        raise live_chat_execution_error(
            "session identity "
            "was not captured"
        )

    if (
        envelope.get(
            "request_id"
        )
        != "request-test"
    ):
        raise live_chat_execution_error(
            "request identity "
            "was not captured"
        )

    result = legacy.chat(
        "test"
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise live_chat_execution_error(
            "wrapped result is invalid"
        )

    if (
        result.get(
            "answer"
        )
        != "answer:test"
    ):
        raise live_chat_execution_error(
            "chat semantics changed"
        )

    if (
        result.get(
            "session_id"
        )
        != "session-test"
    ):
        raise live_chat_execution_error(
            "session identity "
            "was not propagated"
        )

    if (
        result.get(
            "request_id"
        )
        != "request-test"
    ):
        raise live_chat_execution_error(
            "request identity "
            "was not propagated"
        )

    if not isinstance(
        result.get(
            "outcome_evidence"
        ),
        Mapping,
    ):
        raise live_chat_execution_error(
            "outcome evidence missing"
        )

    if not result[
        "outcome_evidence"
    ].get(
        "native_builder_used"
    ):
        raise live_chat_execution_error(
            "native evidence builder "
            "was not used"
        )

    if current_request_envelope():
        raise live_chat_execution_error(
            "request envelope leaked"
        )

    state = status(
        legacy
    )

    if not state.get(
        "installed"
    ):
        raise live_chat_execution_error(
            "installation status failed"
        )

    if not state.get(
        "request_capture_installed"
    ):
        raise live_chat_execution_error(
            "request capture status failed"
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "chat_semantics_preserved":
            True,
        "contract_session_binding":
            True,
        "request_header_binding":
            True,
        "native_outcome_capture":
            True,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
