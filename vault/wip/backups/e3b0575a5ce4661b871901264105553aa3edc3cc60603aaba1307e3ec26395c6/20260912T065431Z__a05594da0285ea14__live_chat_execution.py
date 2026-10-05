#!/usr/bin/env python3

from __future__ import annotations

from contextvars import ContextVar
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping


schema = (
    "savant://runtime/palaver/"
    "live-chat-execution/1.0.0"
)

owner = "exile:palaver"
provider_owner = "exile:opus"
persona_owner = "exile:envoy"
authority_effect = "none"


runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver/runtime"
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
    return _EXECUTION_CONTEXT.get()


def install(
    legacy: ModuleType,
    *,
    selected_persona: callable,
) -> dict[str, Any]:
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
                },
            )

        except Exception as exc:
            try:
                integration.fail(
                    context=
                        context,
                    error_code=
                        (
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
    target = getattr(
        legacy,
        "chat",
        None,
    )

    return {
        "schema":
            schema,
        "installed":
            bool(
                callable(
                    target
                )
                and getattr(
                    target,
                    "_palaver_live_execution",
                    False,
                )
            ),
        "owner":
            owner,
        "provider_owner":
            provider_owner,
        "persona_owner":
            persona_owner,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    class legacy_test:
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

    legacy = legacy_test()

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

    if not isinstance(
        result.get(
            "outcome_evidence"
        ),
        Mapping,
    ):
        raise live_chat_execution_error(
            "outcome evidence missing"
        )

    if not status(
        legacy
    ).get(
        "installed"
    ):
        raise live_chat_execution_error(
            "installation status failed"
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "chat_semantics_preserved":
            True,
        "outcome_capture":
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
