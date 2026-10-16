#!/usr/bin/env python3

from __future__ import annotations

from contextvars import ContextVar
from hashlib import sha256
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping


schema = (
    "savant://runtime/palaver/"
    "chat-outcome-capture/1.0.3"
)

owner = "exile:palaver"

persona_owner = "exile:envoy"
provider_owner = "exile:opus"
verification_owner = "exile:notary"

authority_effect = "none"


root = Path(
    "/root/savant-runtime"
)

evidence_path = (
    root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "palaver"
    / "runtime"
    / "conversation_outcome_evidence.py"
)

evidence_module_name = (
    "savant_palaver_conversation_outcome_evidence"
)


_REQUEST_CONTEXT: ContextVar[
    dict[str, Any] | None
] = ContextVar(
    "palaver_chat_outcome_context",
    default=None,
)


class chat_outcome_capture_error(
    RuntimeError
):
    pass


def _canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        return {}

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def _load_evidence_runtime():
    existing = sys.modules.get(
        evidence_module_name
    )

    if existing is not None:
        return existing

    if not evidence_path.is_file():
        raise (
            chat_outcome_capture_error(
                "conversation outcome evidence "
                "runtime is missing"
            )
        )

    specification = (
        importlib.util.spec_from_file_location(
            evidence_module_name,
            evidence_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            chat_outcome_capture_error(
                "unable to load conversation "
                "outcome evidence runtime"
            )
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        evidence_module_name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            evidence_module_name,
            None,
        )
        raise

    return module


def _builder(
    runtime: Any,
):
    for name in (
        "build_evidence",
        "build",
        "project",
    ):
        candidate = getattr(
            runtime,
            name,
            None,
        )

        if callable(
            candidate
        ):
            return candidate

    return None


def _invoke_builder(
    builder: Any,
    values: Mapping[
        str,
        Any,
    ],
) -> Mapping[
    str,
    Any,
] | None:
    signature = inspect.signature(
        builder
    )

    parameters = (
        signature.parameters
    )

    accepts_kwargs = any(
        parameter.kind
        is inspect.Parameter.VAR_KEYWORD
        for parameter
        in parameters.values()
    )

    if accepts_kwargs:
        result = builder(
            **dict(
                values
            )
        )

        if isinstance(
            result,
            Mapping,
        ):
            return result

        return None

    kwargs: dict[
        str,
        Any,
    ] = {}

    for name, parameter in (
        parameters.items()
    ):
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        if parameter.kind is (
            inspect.Parameter.POSITIONAL_ONLY
        ):
            return None

        if name in values:
            kwargs[
                name
            ] = values[
                name
            ]
            continue

        if (
            parameter.default
            is inspect.Parameter.empty
        ):
            return None

    result = builder(
        **kwargs
    )

    if not isinstance(
        result,
        Mapping,
    ):
        return None

    return result


def begin(
    *,
    session_id: str | None,
    request_id: str | None,
    message: str,
    persona_composition_digest: str | None = None,
    active_traits: tuple[
        str,
        ...,
    ] = (),
    provider_id: str | None = None,
    model_id: str | None = None,
    domains: tuple[
        str,
        ...,
    ] = (),
    signals: tuple[
        str,
        ...,
    ] = (),
) -> dict[str, Any]:
    context = {
        "session_id":
            _text(
                session_id
            ),
        "request_id":
            _text(
                request_id
            ),
        "message":
            str(
                message
                or ""
            ),
        "message_digest":
            _digest(
                str(
                    message
                    or ""
                )
            ),
        "persona_composition_digest":
            _text(
                persona_composition_digest
            ),
        "active_traits":
            tuple(
                sorted(
                    {
                        _text(
                            item
                        )
                        for item
                        in active_traits
                        if _text(
                            item
                        )
                    }
                )
            ),
        "provider_id":
            _text(
                provider_id
            ),
        "model_id":
            _text(
                model_id
            ),
        "domains":
            tuple(
                sorted(
                    {
                        _text(
                            item
                        )
                        for item
                        in domains
                        if _text(
                            item
                        )
                    }
                )
            ),
        "signals":
            tuple(
                sorted(
                    {
                        _text(
                            item
                        )
                        for item
                        in signals
                        if _text(
                            item
                        )
                    }
                )
            ),
        "started_monotonic":
            time.monotonic(),
    }

    _REQUEST_CONTEXT.set(
        context
    )

    return dict(
        context
    )


def current() -> dict[str, Any] | None:
    value = (
        _REQUEST_CONTEXT.get()
    )

    if value is None:
        return None

    return dict(
        value
    )


def clear() -> None:
    _REQUEST_CONTEXT.set(
        None
    )


def _native_values(
    *,
    context: Mapping[
        str,
        Any,
    ],
    payload: Mapping[
        str,
        Any,
    ],
    answer: str,
    composition_digest: str,
    active_traits: tuple[
        str,
        ...,
    ],
    provider_id: str,
    model_id: str,
    elapsed_ms: int,
    success: bool,
    cancelled: bool,
    retry_count: int,
    provider_failover_count: int,
    tool_count: int,
    cost: float | None,
    external_evaluations: tuple[
        Mapping[
            str,
            Any,
        ],
        ...,
    ],
    metadata: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    message = str(
        context.get(
            "message"
        )
        or ""
    )

    message_digest = _text(
        context.get(
            "message_digest"
        )
    ) or _digest(
        message
    )

    response_digest = _digest(
        answer
    )

    operational_observation = {
        "success":
            bool(
                success
            ),
        "cancelled":
            bool(
                cancelled
            ),
        "latency_ms":
            elapsed_ms,
        "cost":
            cost,
        "retry_count":
            max(
                0,
                int(
                    retry_count
                ),
            ),
        "tool_count":
            max(
                0,
                int(
                    tool_count
                ),
            ),
        "provider_failover_count":
            max(
                0,
                int(
                    provider_failover_count
                ),
            ),
    }

    provider = {
        "provider_id":
            provider_id,
        "model_id":
            model_id,
    }

    return {
        "session_id":
            context.get(
                "session_id"
            ),
        "request_id":
            context.get(
                "request_id"
            ),
        "message":
            message,
        "message_text":
            message,
        "prompt":
            message,
        "prompt_text":
            message,
        "message_digest":
            message_digest,
        "prompt_digest":
            message_digest,
        "response":
            answer,
        "response_text":
            answer,
        "answer":
            answer,
        "answer_text":
            answer,
        "response_digest":
            response_digest,
        "answer_digest":
            response_digest,
        "composition":
            composition_digest,
        "composition_id":
            composition_digest,
        "composition_digest":
            composition_digest,
        "persona_composition":
            composition_digest,
        "persona_composition_id":
            composition_digest,
        "persona_composition_digest":
            composition_digest,
        "active_traits":
            active_traits,
        "traits":
            active_traits,
        "domains":
            tuple(
                context.get(
                    "domains",
                    (),
                )
            ),
        "signals":
            tuple(
                context.get(
                    "signals",
                    (),
                )
            ),
        "provider":
            provider,
        "provider_id":
            provider_id,
        "model_id":
            model_id,
        "success":
            bool(
                success
            ),
        "cancelled":
            bool(
                cancelled
            ),
        "latency_ms":
            elapsed_ms,
        "cost":
            cost,
        "retry_count":
            max(
                0,
                int(
                    retry_count
                ),
            ),
        "tool_count":
            max(
                0,
                int(
                    tool_count
                ),
            ),
        "provider_failover_count":
            max(
                0,
                int(
                    provider_failover_count
                ),
            ),
        "operational_observation":
            operational_observation,
        "external_evaluations":
            tuple(
                external_evaluations
            ),
        "evaluations":
            tuple(
                external_evaluations
            ),
        "metadata":
            dict(
                metadata
            ),
        "response_payload":
            dict(
                payload
            ),
    }


def _fallback(
    *,
    context: Mapping[
        str,
        Any,
    ],
    values: Mapping[
        str,
        Any,
    ],
    composition_digest: str,
    active_traits: tuple[
        str,
        ...,
    ],
    external_evaluations: tuple[
        Mapping[
            str,
            Any,
        ],
        ...,
    ],
    metadata: Mapping[
        str,
        Any,
    ],
    fallback_reason: str,
) -> dict[str, Any]:
    semantic = {
        "session_id":
            context.get(
                "session_id"
            ),
        "request_id":
            context.get(
                "request_id"
            ),
        "message_digest":
            values[
                "message_digest"
            ],
        "response_digest":
            values[
                "response_digest"
            ],
        "persona_composition_digest":
            composition_digest,
        "active_traits":
            list(
                active_traits
            ),
        "domains":
            list(
                context.get(
                    "domains",
                    (),
                )
            ),
        "signals":
            list(
                context.get(
                    "signals",
                    (),
                )
            ),
        "provider":
            values[
                "provider"
            ],
        "operational_observation":
            values[
                "operational_observation"
            ],
        "external_evaluations":
            [
                dict(
                    item
                )
                for item
                in external_evaluations
            ],
        "metadata":
            dict(
                metadata
            ),
        "fallback_reason":
            fallback_reason,
    }

    evidence_digest = (
        _digest(
            semantic
        )
    )

    return {
        "schema":
            (
                "savant://runtime/palaver/"
                "conversation-outcome-evidence/"
                "compatibility/1.0.2"
            ),
        "owner":
            owner,
        "evidence_id":
            (
                "paloe_"
                + evidence_digest[
                    :32
                ]
            ),
        "evidence_digest":
            evidence_digest,
        "semantic":
            semantic,
        "capture_owner":
            owner,
        "persona_owner":
            persona_owner,
        "provider_owner":
            provider_owner,
        "verification_owner":
            verification_owner,
        "authoritative":
            False,
        "evaluation_is_authority":
            False,
        "promotion_permission":
            False,
        "mutation_permission":
            False,
        "projection_only":
            True,
        "native_builder_used":
            False,
        "fallback_reason":
            fallback_reason,
        "authority_effect":
            authority_effect,
    }


def complete(
    *,
    response_payload: Mapping[
        str,
        Any,
    ],
    success: bool,
    cancelled: bool = False,
    retry_count: int = 0,
    provider_failover_count: int = 0,
    tool_count: int = 0,
    cost: float | None = None,
    external_evaluations: tuple[
        Mapping[
            str,
            Any,
        ],
        ...,
    ] = (),
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any] | None:
    context = current()

    if context is None:
        return None

    try:
        payload = _mapping(
            response_payload
        )

        answer = str(
            payload.get(
                "answer"
            )
            or payload.get(
                "response"
            )
            or payload.get(
                "text"
            )
            or ""
        )

        elapsed_ms = max(
            0,
            int(
                (
                    time.monotonic()
                    - float(
                        context[
                            "started_monotonic"
                        ]
                    )
                )
                * 1000
            ),
        )

        provider = _mapping(
            payload.get(
                "provider"
            )
        )

        provider_id = _text(
            provider.get(
                "provider_id"
            )
            or payload.get(
                "provider_id"
            )
            or context.get(
                "provider_id"
            )
        )

        model_id = _text(
            provider.get(
                "model_id"
            )
            or payload.get(
                "model_id"
            )
            or context.get(
                "model_id"
            )
        )

        persona = _mapping(
            payload.get(
                "persona_composition"
            )
        )

        composition_digest = _text(
            persona.get(
                "composition_digest"
            )
            or persona.get(
                "composition_id"
            )
            or payload.get(
                "persona_composition_digest"
            )
            or payload.get(
                "composition_digest"
            )
            or payload.get(
                "composition_id"
            )
            or context.get(
                "persona_composition_digest"
            )
        )

        active_traits_raw = (
            persona.get(
                "active_traits"
            )
            or payload.get(
                "active_traits"
            )
            or context.get(
                "active_traits"
            )
            or ()
        )

        active_traits = tuple(
            sorted(
                {
                    _text(
                        item
                    )
                    for item
                    in active_traits_raw
                    if _text(
                        item
                    )
                }
            )
        )

        metadata_value = dict(
            metadata
            or {}
        )

        values = _native_values(
            context=
                context,
            payload=
                payload,
            answer=
                answer,
            composition_digest=
                composition_digest,
            active_traits=
                active_traits,
            provider_id=
                provider_id,
            model_id=
                model_id,
            elapsed_ms=
                elapsed_ms,
            success=
                success,
            cancelled=
                cancelled,
            retry_count=
                retry_count,
            provider_failover_count=
                provider_failover_count,
            tool_count=
                tool_count,
            cost=
                cost,
            external_evaluations=
                external_evaluations,
            metadata=
                metadata_value,
        )

        if not composition_digest:
            return _fallback(
                context=
                    context,
                values=
                    values,
                composition_digest=
                    composition_digest,
                active_traits=
                    active_traits,
                external_evaluations=
                    external_evaluations,
                metadata=
                    metadata_value,
                fallback_reason=
                    "composition_identifier_unavailable",
            )

        evidence_runtime = (
            _load_evidence_runtime()
        )

        builder = _builder(
            evidence_runtime
        )

        if builder is None:
            return _fallback(
                context=
                    context,
                values=
                    values,
                composition_digest=
                    composition_digest,
                active_traits=
                    active_traits,
                external_evaluations=
                    external_evaluations,
                metadata=
                    metadata_value,
                fallback_reason=
                    "native_builder_unavailable",
            )

        result = _invoke_builder(
            builder,
            values,
        )

        if not isinstance(
            result,
            Mapping,
        ):
            return _fallback(
                context=
                    context,
                values=
                    values,
                composition_digest=
                    composition_digest,
                active_traits=
                    active_traits,
                external_evaluations=
                    external_evaluations,
                metadata=
                    metadata_value,
                fallback_reason=
                    "native_contract_not_satisfied",
            )

        projection = dict(
            result
        )

        projection.setdefault(
            "owner",
            owner,
        )

        projection[
            "capture_owner"
        ] = owner

        projection[
            "persona_owner"
        ] = persona_owner

        projection[
            "provider_owner"
        ] = provider_owner

        projection[
            "verification_owner"
        ] = verification_owner

        projection[
            "native_builder_used"
        ] = True

        projection[
            "authority_effect"
        ] = "none"

        return projection

    finally:
        clear()


def selftest() -> dict[str, Any]:
    runtime = (
        _load_evidence_runtime()
    )

    native_builder = _builder(
        runtime
    )

    if native_builder is None:
        raise (
            chat_outcome_capture_error(
                "conversation outcome evidence "
                "has no projection function"
            )
        )

    signature = inspect.signature(
        native_builder
    )

    begin(
        session_id=
            "session-test",
        request_id=
            "request-test",
        message=
            "test message",
        persona_composition_digest=
            "composition-test",
        active_traits=(
            "planning",
        ),
    )

    native_evidence = complete(
        response_payload={
            "answer":
                "test response",
            "persona_composition_digest":
                "composition-test",
        },
        success=True,
    )

    if not isinstance(
        native_evidence,
        dict,
    ):
        raise (
            chat_outcome_capture_error(
                "native outcome evidence "
                "was not produced"
            )
        )

    if (
        native_evidence.get(
            "authority_effect"
        )
        != "none"
    ):
        raise (
            chat_outcome_capture_error(
                "native evidence acquired "
                "authority"
            )
        )

    begin(
        session_id=
            "session-fallback-test",
        request_id=
            "request-fallback-test",
        message=
            "fallback test message",
    )

    fallback_evidence = complete(
        response_payload={
            "answer":
                "fallback response",
        },
        success=True,
    )

    if not isinstance(
        fallback_evidence,
        dict,
    ):
        raise (
            chat_outcome_capture_error(
                "fallback evidence "
                "was not produced"
            )
        )

    if (
        fallback_evidence.get(
            "fallback_reason"
        )
        != "composition_identifier_unavailable"
    ):
        raise (
            chat_outcome_capture_error(
                "missing composition identity "
                "did not select fallback"
            )
        )

    if current() is not None:
        raise (
            chat_outcome_capture_error(
                "request context leaked"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "owner":
            owner,
        "native_builder":
            getattr(
                native_builder,
                "__name__",
                "unknown",
            ),
        "native_builder_signature":
            str(
                signature
            ),
        "native_composition_identity_required":
            True,
        "missing_composition_fallback":
            True,
        "mutation_permission":
            False,
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
