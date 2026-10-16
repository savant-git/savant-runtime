#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping


schema = (
    "savant://runtime/palaver/"
    "chat-execution-integration/1.0.0"
)

owner = "exile:palaver"
persona_owner = "exile:envoy"
provider_owner = "exile:opus"
verification_owner = "exile:notary"

authority_effect = "none"


root = Path(
    "/root/savant-runtime"
)

runtime_root = (
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
)

capture_path = (
    runtime_root
    / "chat_outcome_capture.py"
)

lifecycle_path = (
    runtime_root
    / "provider_lifecycle.py"
)


class chat_execution_integration_error(
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


def _text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


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


def _load_module(
    *,
    module_name: str,
    path: Path,
):
    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise (
            chat_execution_integration_error(
                f"required runtime is missing: {path}"
            )
        )

    specification = (
        importlib.util.spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            chat_execution_integration_error(
                f"unable to load runtime: {path}"
            )
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


def capture_runtime():
    return _load_module(
        module_name=(
            "savant_palaver_chat_outcome_capture"
        ),
        path=capture_path,
    )


def lifecycle_runtime():
    return _load_module(
        module_name=(
            "savant_palaver_provider_lifecycle"
        ),
        path=lifecycle_path,
    )


def _request_id(
    *,
    supplied: str | None,
    session_id: str | None,
    message: str,
) -> str:
    explicit = _text(
        supplied
    )

    if explicit:
        return explicit

    semantic = {
        "session_id":
            _text(
                session_id
            ),
        "message_digest":
            _digest(
                message
            ),
    }

    return (
        "palreq_"
        + _digest(
            semantic
        )[:32]
    )


@dataclass(
    frozen=True,
)
class execution_context:
    request_id: str
    session_id: str
    message: str
    persona_id: str
    persona_composition_digest: str
    active_traits: tuple[str, ...]
    provider_id: str
    model_id: str
    domains: tuple[str, ...]
    signals: tuple[str, ...]


def begin(
    *,
    message: str,
    session_id: str | None = None,
    request_id: str | None = None,
    persona_id: str | None = None,
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
    cancel_hook: Callable[
        [],
        Any,
    ] | None = None,
) -> execution_context:
    text = str(
        message
        or ""
    ).strip()

    if not text:
        raise (
            chat_execution_integration_error(
                "message is required"
            )
        )

    resolved_request_id = (
        _request_id(
            supplied=
                request_id,
            session_id=
                session_id,
            message=
                text,
        )
    )

    context = execution_context(
        request_id=
            resolved_request_id,
        session_id=
            _text(
                session_id
            ),
        message=
            text,
        persona_id=
            _text(
                persona_id
            ),
        persona_composition_digest=
            _text(
                persona_composition_digest
            ),
        active_traits=
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
        provider_id=
            _text(
                provider_id
            ),
        model_id=
            _text(
                model_id
            ),
        domains=
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
        signals=
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
    )

    capture = capture_runtime()

    capture.begin(
        session_id=
            context.session_id,
        request_id=
            context.request_id,
        message=
            context.message,
        persona_composition_digest=
            context.persona_composition_digest,
        active_traits=
            context.active_traits,
        provider_id=
            context.provider_id,
        model_id=
            context.model_id,
        domains=
            context.domains,
        signals=
            context.signals,
    )

    lifecycle = (
        lifecycle_runtime()
        .lifecycle
    )

    lifecycle.register(
        request_id=
            context.request_id,
        cancel_hook=
            cancel_hook,
    )

    return context


def attach_provider_cancel(
    *,
    context: execution_context,
    cancel_hook: Callable[
        [],
        Any,
    ],
) -> bool:
    return bool(
        lifecycle_runtime()
        .lifecycle
        .attach_cancel_hook(
            request_id=
                context.request_id,
            cancel_hook=
                cancel_hook,
        )
    )


def cancel(
    *,
    context: execution_context,
) -> dict[str, Any]:
    result = (
        lifecycle_runtime()
        .lifecycle
        .cancel(
            request_id=
                context.request_id
        )
    )

    result = dict(
        result
    )

    result[
        "conversation_owner"
    ] = owner

    result[
        "provider_owner"
    ] = provider_owner

    result[
        "authority_effect"
    ] = authority_effect

    return result


def _enrich_result(
    *,
    context: execution_context,
    result: Mapping[
        str,
        Any,
    ],
    outcome_evidence: Mapping[
        str,
        Any,
    ] | None,
    lifecycle_result: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    projection = dict(
        result
    )

    if (
        "response" not in projection
        and "answer" in projection
    ):
        projection[
            "response"
        ] = projection[
            "answer"
        ]

    projection[
        "request_id"
    ] = context.request_id

    if context.session_id:
        projection[
            "session_id"
        ] = context.session_id

    projection[
        "conversation_owner"
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
    ] = authority_effect

    if isinstance(
        outcome_evidence,
        Mapping,
    ):
        projection[
            "outcome_evidence"
        ] = dict(
            outcome_evidence
        )

    projection[
        "provider_lifecycle"
    ] = {
        "completed":
            bool(
                lifecycle_result.get(
                    "completed",
                    False,
                )
            ),
        "cancellation_requested":
            bool(
                lifecycle_result.get(
                    "cancellation_requested",
                    False,
                )
            ),
        "cancellation_propagated":
            bool(
                lifecycle_result.get(
                    "cancellation_propagated",
                    False,
                )
            ),
        "provider_cancellation_available":
            bool(
                lifecycle_result.get(
                    "provider_cancellation_available",
                    False,
                )
            ),
    }

    return projection


def complete(
    *,
    context: execution_context,
    result: Mapping[
        str,
        Any,
    ],
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
) -> dict[str, Any]:
    if not isinstance(
        result,
        Mapping,
    ):
        raise (
            chat_execution_integration_error(
                "chat result must be a mapping"
            )
        )

    capture = capture_runtime()

    try:
        evidence = capture.complete(
            response_payload=
                result,
            success=True,
            cancelled=False,
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
            metadata={
                "persona_id":
                    context.persona_id,
                **dict(
                    metadata
                    or {}
                ),
            },
        )
    finally:
        lifecycle_result = (
            lifecycle_runtime()
            .lifecycle
            .complete(
                request_id=
                    context.request_id
            )
        )

    return _enrich_result(
        context=
            context,
        result=
            result,
        outcome_evidence=
            evidence,
        lifecycle_result=
            lifecycle_result,
    )


def fail(
    *,
    context: execution_context,
    error_code: str,
    diagnostic: str | None = None,
    cancelled: bool = False,
    retry_count: int = 0,
    provider_failover_count: int = 0,
    tool_count: int = 0,
    metadata: Mapping[
        str,
        Any,
    ] | None = None,
) -> dict[str, Any]:
    failure_payload = {
        "answer":
            "",
        "response":
            "",
        "error_code":
            _text(
                error_code
            ),
    }

    capture = capture_runtime()

    try:
        evidence = capture.complete(
            response_payload=
                failure_payload,
            success=False,
            cancelled=
                bool(
                    cancelled
                ),
            retry_count=
                retry_count,
            provider_failover_count=
                provider_failover_count,
            tool_count=
                tool_count,
            metadata={
                "persona_id":
                    context.persona_id,
                "error_code":
                    _text(
                        error_code
                    ),
                "diagnostic":
                    _text(
                        diagnostic
                    ),
                **dict(
                    metadata
                    or {}
                ),
            },
        )
    finally:
        lifecycle_result = (
            lifecycle_runtime()
            .lifecycle
            .complete(
                request_id=
                    context.request_id
            )
        )

    return {
        "schema":
            schema,
        "request_id":
            context.request_id,
        "session_id":
            context.session_id,
        "error_code":
            _text(
                error_code
            ),
        "cancelled":
            bool(
                cancelled
            ),
        "outcome_evidence":
            evidence,
        "provider_lifecycle":
            lifecycle_result,
        "conversation_owner":
            owner,
        "provider_owner":
            provider_owner,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    capture = capture_runtime()

    capture_status = {
        "schema":
            getattr(
                capture,
                "schema",
                None,
            ),
        "owner":
            getattr(
                capture,
                "owner",
                None,
            ),
    }

    lifecycle_status = (
        lifecycle_runtime()
        .lifecycle
        .status()
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_owner":
            persona_owner,
        "provider_owner":
            provider_owner,
        "verification_owner":
            verification_owner,
        "capture_runtime":
            capture_status,
        "provider_lifecycle":
            lifecycle_status,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
        "mutation_permission":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    cancelled: list[
        str,
    ] = []

    context = begin(
        message=
            "integration test",
        session_id=
            "session-test",
        request_id=
            "request-test",
        persona_id=
            "orobouros",
        persona_composition_digest=
            "composition-test",
        active_traits=(
            "planning",
        ),
        provider_id=
            "provider-test",
        model_id=
            "model-test",
        cancel_hook=lambda: (
            cancelled.append(
                "cancelled"
            )
        ),
    )

    result = complete(
        context=
            context,
        result={
            "answer":
                "integration response",
            "persona_composition_digest":
                "composition-test",
            "provider_id":
                "provider-test",
            "model_id":
                "model-test",
        },
    )

    if (
        result.get(
            "answer"
        )
        != "integration response"
    ):
        raise (
            chat_execution_integration_error(
                "legacy answer was not preserved"
            )
        )

    if (
        result.get(
            "response"
        )
        != "integration response"
    ):
        raise (
            chat_execution_integration_error(
                "response compatibility "
                "projection failed"
            )
        )

    if (
        result.get(
            "request_id"
        )
        != "request-test"
    ):
        raise (
            chat_execution_integration_error(
                "request identity was lost"
            )
        )

    if not isinstance(
        result.get(
            "outcome_evidence"
        ),
        Mapping,
    ):
        raise (
            chat_execution_integration_error(
                "outcome evidence was not attached"
            )
        )

    if (
        result.get(
            "authority_effect"
        )
        != "none"
    ):
        raise (
            chat_execution_integration_error(
                "integration acquired authority"
            )
        )

    second = begin(
        message=
            "cancellation test",
        session_id=
            "session-cancel-test",
        request_id=
            "request-cancel-test",
        persona_id=
            "orobouros",
        persona_composition_digest=
            "composition-test",
        cancel_hook=lambda: (
            cancelled.append(
                "cancelled"
            )
        ),
    )

    cancellation = cancel(
        context=
            second
    )

    fail(
        context=
            second,
        error_code=
            "request_cancelled",
        cancelled=True,
    )

    if (
        not cancellation.get(
            "cancellation_propagated"
        )
    ):
        raise (
            chat_execution_integration_error(
                "real cancellation hook "
                "was not propagated"
            )
        )

    if len(
        cancelled
    ) != 1:
        raise (
            chat_execution_integration_error(
                "cancellation hook executed "
                "unexpected number of times"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "legacy_answer_preserved":
            True,
        "response_projection":
            True,
        "outcome_evidence_attached":
            True,
        "real_cancellation_hook":
            True,
        "synthetic_streaming":
            False,
        "synthetic_provider_cancellation":
            False,
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
