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
    "chat-outcome-capture/1.0.2"
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

    missing: list[
        str,
    ] = []

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
            missing.append(
                name
            )

    if missing:
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
            str(
                session_id
                or ""
            ).strip(),
        "request_id":
            str(
                request_id
                or ""
            ).strip(),
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
            str(
                persona_composition_digest
                or ""
            ).strip(),
        "active_traits":
            tuple(
                sorted(
                    {
                        str(item).strip()
                        for item
                        in active_traits
                        if str(
                            item
                            or ""
                        ).strip()
                    }
                )
            ),
        "provider_id":
            str(
                provider_id
                or ""
            ).strip(),
        "model_id":
            str(
                model_id
                or ""
            ).strip(),
        "domains":
            tuple(
                sorted(
                    {
                        str(item).strip()
                        for item
                        in domains
                        if str(
                            item
                            or ""
                        ).strip()
                    }
                )
            ),
        "signals":
            tuple(
                sorted(
                    {
                        str(item).strip()
                        for item
                        in signals
                        if str(
                            item
                            or ""
                        ).strip()
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

    message_digest = str(
        context.get(
            "message_digest"
        )
        or _digest(
            message
        )
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
        "composition_digest":
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

        provider_id = str(
            provider.get(
                "provider_id"
            )
            or payload.get(
                "provider_id"
            )
            or context.get(
                "provider_id"
            )
            or ""
        ).strip()

        model_id = str(
            provider.get(
                "model_id"
            )
            or payload.get(
                "model_id"
            )
            or context.get(
                "model_id"
            )
            or ""
        ).strip()

        persona = _mapping(
            payload.get(
                "persona_composition"
            )
        )

        composition_digest = str(
            persona.get(
                "composition_digest"
            )
            or payload.get(
                "persona_composition_digest"
            )
            or payload.get(
                "composition_digest"
            )
            or context.get(
                "persona_composition_digest"
            )
            or ""
        ).strip()

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
                    str(item).strip()
                    for item
                    in active_traits_raw
                    if str(
                        item
                        or ""
                    ).strip()
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

        evidence_runtime = (
            _load_evidence_runtime()
        )

        builder = _builder(
            evidence_runtime
        )

        if builder is not None:
            result = (
                _invoke_builder(
                    builder,
                    values,
                )
            )

            if isinstance(
                result,
                Mapping,
            ):
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
                    "authority_effect"
                ] = "none"

                return projection

        fallback_semantic = {
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
                metadata_value,
        }

        evidence_digest = (
            _digest(
                fallback_semantic
            )
        )

        return {
            "schema":
                (
                    "savant://runtime/palaver/"
                    "conversation-outcome-evidence/"
                    "compatibility/1.0.1"
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
                fallback_semantic,
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
            "authority_effect":
                authority_effect,
        }

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
        active_traits=(
            "planning",
        ),
    )

    evidence = complete(
        response_payload={
            "answer":
                "test response",
        },
        success=True,
    )

    if not isinstance(
        evidence,
        dict,
    ):
        raise (
            chat_outcome_capture_error(
                "outcome evidence "
                "was not produced"
            )
        )

    if (
        evidence.get(
            "owner"
        )
        not in {
            owner,
            "palaver",
        }
    ):
        raise (
            chat_outcome_capture_error(
                "outcome evidence owner "
                "is incompatible"
            )
        )

    if (
        evidence.get(
            "authority_effect"
        )
        != "none"
    ):
        raise (
            chat_outcome_capture_error(
                "outcome evidence "
                "acquired authority"
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
        "contract_adaptation":
            "signature_bound_keyword_only",
        "fallback_available":
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
