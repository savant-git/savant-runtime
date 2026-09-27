from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import uuid4


schema = "savant://runtime/exiles/flow/1.0.0"
owner = "exile:segue"

max_hops_default = 64
max_payload_bytes_default = 4 * 1024 * 1024
max_history_default = 256

terminal_states = frozenset(
    {
        "complete",
        "failed",
        "cancelled",
        "expired",
    }
)

valid_states = frozenset(
    {
        "created",
        "ready",
        "running",
        "waiting",
        "complete",
        "failed",
        "cancelled",
        "expired",
    }
)


class exile_flow_error(RuntimeError):
    pass


class exile_flow_contract_error(exile_flow_error):
    pass


class exile_flow_limit_error(exile_flow_error):
    pass


class exile_flow_transition_error(exile_flow_error):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise exile_flow_contract_error(
            "flow substance must be canonical-json serializable"
        ) from exc


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _now_ns() -> int:
    return time.time_ns()


def _token() -> str:
    return uuid4().hex


def _required_text(value: Any, field: str) -> str:
    result = str(value or "").strip().lower()

    if not result:
        raise exile_flow_contract_error(
            field + " is required"
        )

    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None

    result = str(value).strip()

    return result or None


def _positive_integer(
    value: Any,
    field: str,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool):
        raise exile_flow_contract_error(
            field + " must be an integer"
        )

    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise exile_flow_contract_error(
            field + " must be an integer"
        ) from exc

    if result < minimum:
        raise exile_flow_contract_error(
            field + " must be at least " + str(minimum)
        )

    if maximum is not None and result > maximum:
        raise exile_flow_contract_error(
            field + " must not exceed " + str(maximum)
        )

    return result


def _mapping(
    value: Any,
    field: str,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(value, Mapping):
        raise exile_flow_contract_error(
            field + " must be a mapping"
        )

    return dict(value)


def _text_tuple(
    value: Any,
    field: str,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        values: Iterable[Any] = (value,)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (bytes, bytearray),
    ):
        values = value
    else:
        raise exile_flow_contract_error(
            field + " must be text or a sequence"
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for item in values:
        text = str(item).strip().lower()

        if not text or text in seen:
            continue

        seen.add(text)
        normalized.append(text)

    return tuple(normalized)


def _freeze_mapping(
    value: Mapping[str, Any],
) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class flow_limits:
    max_hops: int = max_hops_default
    max_payload_bytes: int = max_payload_bytes_default
    max_history: int = max_history_default
    deadline_ns: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_hops",
            _positive_integer(
                self.max_hops,
                "max_hops",
                maximum=4096,
            ),
        )
        object.__setattr__(
            self,
            "max_payload_bytes",
            _positive_integer(
                self.max_payload_bytes,
                "max_payload_bytes",
                maximum=1024 * 1024 * 1024,
            ),
        )
        object.__setattr__(
            self,
            "max_history",
            _positive_integer(
                self.max_history,
                "max_history",
                maximum=16384,
            ),
        )

        if self.deadline_ns is not None:
            object.__setattr__(
                self,
                "deadline_ns",
                _positive_integer(
                    self.deadline_ns,
                    "deadline_ns",
                ),
            )

    def projection(self) -> dict[str, Any]:
        return {
            "max_hops": self.max_hops,
            "max_payload_bytes": self.max_payload_bytes,
            "max_history": self.max_history,
            "deadline_ns": self.deadline_ns,
        }


@dataclass(frozen=True, slots=True)
class flow_contract:
    capability: str
    source: str
    target: str
    required_capabilities: tuple[str, ...] = ()
    accepted_schemas: tuple[str, ...] = ()
    emitted_schema: str | None = None
    idempotent: bool = False
    replayable: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability",
            _required_text(
                self.capability,
                "capability",
            ),
        )
        object.__setattr__(
            self,
            "source",
            _required_text(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "target",
            _required_text(
                self.target,
                "target",
            ),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _text_tuple(
                self.required_capabilities,
                "required_capabilities",
            ),
        )
        object.__setattr__(
            self,
            "accepted_schemas",
            _text_tuple(
                self.accepted_schemas,
                "accepted_schemas",
            ),
        )
        object.__setattr__(
            self,
            "emitted_schema",
            _optional_text(
                self.emitted_schema
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "source": self.source,
            "target": self.target,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "accepted_schemas": list(
                self.accepted_schemas
            ),
            "emitted_schema": self.emitted_schema,
            "idempotent": self.idempotent,
            "replayable": self.replayable,
        }


@dataclass(frozen=True, slots=True)
class flow_event:
    sequence: int
    state: str
    exile: str
    capability: str
    at_ns: int
    input_digest: str | None
    output_digest: str | None
    detail: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.state not in valid_states:
            raise exile_flow_contract_error(
                "invalid flow state: " + self.state
            )

        object.__setattr__(
            self,
            "detail",
            _freeze_mapping(
                self.detail
            ),
        )

    def projection(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "state": self.state,
            "exile": self.exile,
            "capability": self.capability,
            "at_ns": self.at_ns,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True, slots=True)
class flow_envelope:
    flow_id: str
    trace_id: str
    parent_flow_id: str | None
    state: str
    source: str
    target: str
    capability: str
    payload: Mapping[str, Any]
    payload_schema: str | None
    payload_digest: str
    hop: int
    created_ns: int
    updated_ns: int
    limits: flow_limits
    lineage: tuple[str, ...]
    provenance: Mapping[str, Any]
    context: Mapping[str, Any]
    history: tuple[flow_event, ...]
    version: int = 1

    def __post_init__(self) -> None:
        if self.state not in valid_states:
            raise exile_flow_contract_error(
                "invalid flow state: " + self.state
            )

        object.__setattr__(
            self,
            "source",
            _required_text(
                self.source,
                "source",
            ),
        )
        object.__setattr__(
            self,
            "target",
            _required_text(
                self.target,
                "target",
            ),
        )
        object.__setattr__(
            self,
            "capability",
            _required_text(
                self.capability,
                "capability",
            ),
        )
        object.__setattr__(
            self,
            "payload",
            _freeze_mapping(
                self.payload
            ),
        )
        object.__setattr__(
            self,
            "provenance",
            _freeze_mapping(
                self.provenance
            ),
        )
        object.__setattr__(
            self,
            "context",
            _freeze_mapping(
                self.context
            ),
        )

    def projection(
        self,
        *,
        include_payload: bool = True,
    ) -> dict[str, Any]:
        result = {
            "schema": schema,
            "owner": owner,
            "flow_id": self.flow_id,
            "trace_id": self.trace_id,
            "parent_flow_id": self.parent_flow_id,
            "state": self.state,
            "source": self.source,
            "target": self.target,
            "capability": self.capability,
            "payload_schema": self.payload_schema,
            "payload_digest": self.payload_digest,
            "hop": self.hop,
            "created_ns": self.created_ns,
            "updated_ns": self.updated_ns,
            "limits": self.limits.projection(),
            "lineage": list(self.lineage),
            "provenance": dict(self.provenance),
            "context": dict(self.context),
            "history": [
                event.projection()
                for event in self.history
            ],
            "version": self.version,
            "boundaries": {
                "creates_authority": False,
                "mutates_authority": False,
                "owns_exile_behavior": False,
                "owns_provider_routing": False,
                "owns_personality": False,
                "owns_task_semantics": False,
                "owns_conversation": False,
                "owns_persistence": False,
                "projection_only": True,
            },
        }

        if include_payload:
            result["payload"] = dict(
                self.payload
            )

        result["digest"] = _digest(
            result
        )

        return result


def create_flow(
    *,
    source: str,
    target: str,
    capability: str,
    payload: Mapping[str, Any] | None = None,
    payload_schema: str | None = None,
    trace_id: str | None = None,
    parent_flow_id: str | None = None,
    lineage: Sequence[str] | None = None,
    provenance: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    limits: flow_limits | None = None,
) -> flow_envelope:
    normalized_payload = _mapping(
        payload,
        "payload",
    )
    normalized_limits = limits or flow_limits()

    payload_bytes = _canonical(
        normalized_payload
    )

    if len(payload_bytes) > normalized_limits.max_payload_bytes:
        raise exile_flow_limit_error(
            "payload exceeds max_payload_bytes"
        )

    now = _now_ns()
    flow_id = _token()
    resolved_trace_id = (
        _optional_text(trace_id)
        or flow_id
    )

    event = flow_event(
        sequence=0,
        state="created",
        exile=_required_text(
            source,
            "source",
        ),
        capability=_required_text(
            capability,
            "capability",
        ),
        at_ns=now,
        input_digest=None,
        output_digest=_digest(
            normalized_payload
        ),
        detail={
            "target": _required_text(
                target,
                "target",
            ),
        },
    )

    return flow_envelope(
        flow_id=flow_id,
        trace_id=resolved_trace_id,
        parent_flow_id=_optional_text(
            parent_flow_id
        ),
        state="created",
        source=source,
        target=target,
        capability=capability,
        payload=normalized_payload,
        payload_schema=_optional_text(
            payload_schema
        ),
        payload_digest=_digest(
            normalized_payload
        ),
        hop=0,
        created_ns=now,
        updated_ns=now,
        limits=normalized_limits,
        lineage=_text_tuple(
            lineage,
            "lineage",
        ),
        provenance=_mapping(
            provenance,
            "provenance",
        ),
        context=_mapping(
            context,
            "context",
        ),
        history=(event,),
    )


def _assert_live(
    envelope: flow_envelope,
) -> None:
    if envelope.state in terminal_states:
        raise exile_flow_transition_error(
            "terminal flow cannot transition"
        )

    if (
        envelope.limits.deadline_ns is not None
        and _now_ns() > envelope.limits.deadline_ns
    ):
        raise exile_flow_limit_error(
            "flow deadline exceeded"
        )

    if envelope.hop >= envelope.limits.max_hops:
        raise exile_flow_limit_error(
            "flow hop limit exceeded"
        )


def _append_event(
    envelope: flow_envelope,
    event: flow_event,
) -> tuple[flow_event, ...]:
    history = envelope.history + (
        event,
    )

    if len(history) > envelope.limits.max_history:
        raise exile_flow_limit_error(
            "flow history limit exceeded"
        )

    return history


def transition(
    envelope: flow_envelope,
    *,
    state: str,
    exile: str,
    capability: str | None = None,
    payload: Mapping[str, Any] | None = None,
    payload_schema: str | None = None,
    target: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> flow_envelope:
    _assert_live(
        envelope
    )

    normalized_state = str(
        state
    ).strip().lower()

    if normalized_state not in valid_states:
        raise exile_flow_transition_error(
            "invalid target state: "
            + normalized_state
        )

    normalized_payload = (
        dict(envelope.payload)
        if payload is None
        else _mapping(
            payload,
            "payload",
        )
    )

    payload_bytes = _canonical(
        normalized_payload
    )

    if len(payload_bytes) > envelope.limits.max_payload_bytes:
        raise exile_flow_limit_error(
            "payload exceeds max_payload_bytes"
        )

    resolved_capability = (
        envelope.capability
        if capability is None
        else _required_text(
            capability,
            "capability",
        )
    )

    resolved_target = (
        envelope.target
        if target is None
        else _required_text(
            target,
            "target",
        )
    )

    now = _now_ns()
    output_digest = _digest(
        normalized_payload
    )

    event = flow_event(
        sequence=len(
            envelope.history
        ),
        state=normalized_state,
        exile=_required_text(
            exile,
            "exile",
        ),
        capability=resolved_capability,
        at_ns=now,
        input_digest=envelope.payload_digest,
        output_digest=output_digest,
        detail=_mapping(
            detail,
            "detail",
        ),
    )

    return flow_envelope(
        flow_id=envelope.flow_id,
        trace_id=envelope.trace_id,
        parent_flow_id=envelope.parent_flow_id,
        state=normalized_state,
        source=envelope.source,
        target=resolved_target,
        capability=resolved_capability,
        payload=normalized_payload,
        payload_schema=(
            envelope.payload_schema
            if payload_schema is None
            else _optional_text(
                payload_schema
            )
        ),
        payload_digest=output_digest,
        hop=envelope.hop + 1,
        created_ns=envelope.created_ns,
        updated_ns=now,
        limits=envelope.limits,
        lineage=envelope.lineage + (
            envelope.payload_digest,
        ),
        provenance=dict(
            envelope.provenance
        ),
        context=dict(
            envelope.context
        ),
        history=_append_event(
            envelope,
            event,
        ),
        version=envelope.version,
    )


def validate_contract(
    envelope: flow_envelope,
    contract: flow_contract,
    *,
    capabilities: Iterable[str] = (),
) -> None:
    if envelope.source != contract.source:
        raise exile_flow_contract_error(
            "flow source does not satisfy contract"
        )

    if envelope.target != contract.target:
        raise exile_flow_contract_error(
            "flow target does not satisfy contract"
        )

    if envelope.capability != contract.capability:
        raise exile_flow_contract_error(
            "flow capability does not satisfy contract"
        )

    available = set(
        _text_tuple(
            tuple(capabilities),
            "capabilities",
        )
    )

    missing = [
        capability
        for capability
        in contract.required_capabilities
        if capability not in available
    ]

    if missing:
        raise exile_flow_contract_error(
            "missing required capabilities: "
            + ", ".join(missing)
        )

    if (
        contract.accepted_schemas
        and envelope.payload_schema
        not in contract.accepted_schemas
    ):
        raise exile_flow_contract_error(
            "payload schema does not satisfy contract"
        )


def execute_hop(
    envelope: flow_envelope,
    *,
    contract: flow_contract,
    handler: Callable[
        [Mapping[str, Any]],
        Mapping[str, Any],
    ],
    capabilities: Iterable[str] = (),
) -> flow_envelope:
    _assert_live(
        envelope
    )

    validate_contract(
        envelope,
        contract,
        capabilities=capabilities,
    )

    running = transition(
        envelope,
        state="running",
        exile=contract.target,
        detail={
            "contract_digest":
                _digest(
                    contract.projection()
                ),
        },
    )

    try:
        output = handler(
            dict(
                running.payload
            )
        )
    except Exception as exc:
        return transition(
            running,
            state="failed",
            exile=contract.target,
            detail={
                "error_type":
                    type(exc).__name__,
                "error":
                    str(exc),
            },
        )

    if not isinstance(
        output,
        Mapping,
    ):
        return transition(
            running,
            state="failed",
            exile=contract.target,
            detail={
                "error_type":
                    "invalid-handler-output",
                "error":
                    "handler output must be a mapping",
            },
        )

    return transition(
        running,
        state="complete",
        exile=contract.target,
        payload=output,
        payload_schema=contract.emitted_schema,
        detail={
            "contract_digest":
                _digest(
                    contract.projection()
                ),
        },
    )


def fork_flow(
    envelope: flow_envelope,
    *,
    target: str,
    capability: str,
    payload: Mapping[str, Any] | None = None,
    payload_schema: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> flow_envelope:
    _assert_live(
        envelope
    )

    return create_flow(
        source=envelope.target,
        target=target,
        capability=capability,
        payload=(
            dict(envelope.payload)
            if payload is None
            else payload
        ),
        payload_schema=(
            envelope.payload_schema
            if payload_schema is None
            else payload_schema
        ),
        trace_id=envelope.trace_id,
        parent_flow_id=envelope.flow_id,
        lineage=(
            *envelope.lineage,
            envelope.payload_digest,
        ),
        provenance={
            **dict(
                envelope.provenance
            ),
            "parent_flow_id":
                envelope.flow_id,
        },
        context={
            **dict(
                envelope.context
            ),
            **_mapping(
                context,
                "context",
            ),
        },
        limits=envelope.limits,
    )


def replay_projection(
    envelope: flow_envelope,
) -> dict[str, Any]:
    return {
        "schema":
            schema,
        "flow_id":
            envelope.flow_id,
        "trace_id":
            envelope.trace_id,
        "parent_flow_id":
            envelope.parent_flow_id,
        "initial_digest":
            (
                envelope.history[0].output_digest
                if envelope.history
                else None
            ),
        "current_digest":
            envelope.payload_digest,
        "events": [
            {
                "sequence":
                    event.sequence,
                "state":
                    event.state,
                "exile":
                    event.exile,
                "capability":
                    event.capability,
                "input_digest":
                    event.input_digest,
                "output_digest":
                    event.output_digest,
            }
            for event in envelope.history
        ],
        "replayable":
            True,
        "creates_authority":
            False,
        "digest":
            _digest(
                [
                    event.projection()
                    for event in envelope.history
                ]
            ),
    }


def prepare_exile(
    *,
    exile: str,
    capabilities: Sequence[str] = (),
    accepts: Sequence[str] = (),
    emits: Sequence[str] = (),
    extensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exile_id = _required_text(
        exile,
        "exile",
    )

    projection = {
        "schema":
            "savant://runtime/exiles/preparation/1.0.0",
        "owner":
            owner,
        "exile":
            exile_id,
        "state":
            "prepared",
        "capabilities":
            list(
                _text_tuple(
                    capabilities,
                    "capabilities",
                )
            ),
        "accepts":
            list(
                _text_tuple(
                    accepts,
                    "accepts",
                )
            ),
        "emits":
            list(
                _text_tuple(
                    emits,
                    "emits",
                )
            ),
        "extensions":
            _mapping(
                extensions,
                "extensions",
            ),
        "reserved": {
            "runtime":
                {},
            "contracts":
                {},
            "adapters":
                {},
            "projections":
                {},
            "exile_specific":
                {},
        },
        "boundaries": {
            "creates_exile_behavior":
                False,
            "creates_authority":
                False,
            "requires_exile_specific_code":
                False,
            "extension_space_reserved":
                True,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


def compose_pipeline(
    *,
    source: str,
    payload: Mapping[str, Any],
    steps: Sequence[
        tuple[
            flow_contract,
            Callable[
                [Mapping[str, Any]],
                Mapping[str, Any],
            ],
            Iterable[str],
        ]
    ],
    payload_schema: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    limits: flow_limits | None = None,
) -> flow_envelope:
    if not steps:
        raise exile_flow_contract_error(
            "pipeline requires at least one step"
        )

    first_contract = steps[0][0]

    if first_contract.source != _required_text(
        source,
        "source",
    ):
        raise exile_flow_contract_error(
            "pipeline source does not match first contract"
        )

    envelope = create_flow(
        source=first_contract.source,
        target=first_contract.target,
        capability=first_contract.capability,
        payload=payload,
        payload_schema=payload_schema,
        provenance=provenance,
        context=context,
        limits=limits,
    )

    for index, (
        contract,
        handler,
        capabilities,
    ) in enumerate(steps):
        if index:
            previous = steps[
                index - 1
            ][0]

            if previous.target != contract.source:
                raise exile_flow_contract_error(
                    "pipeline contracts are not contiguous"
                )

            envelope = create_flow(
                source=contract.source,
                target=contract.target,
                capability=contract.capability,
                payload=dict(
                    envelope.payload
                ),
                payload_schema=envelope.payload_schema,
                trace_id=envelope.trace_id,
                parent_flow_id=envelope.flow_id,
                lineage=(
                    *envelope.lineage,
                    envelope.payload_digest,
                ),
                provenance={
                    **dict(
                        envelope.provenance
                    ),
                    "previous_flow_id":
                        envelope.flow_id,
                },
                context=dict(
                    envelope.context
                ),
                limits=envelope.limits,
            )

        envelope = execute_hop(
            envelope,
            contract=contract,
            handler=handler,
            capabilities=capabilities,
        )

        if envelope.state != "complete":
            break

    return envelope


def architecture_projection() -> dict[str, Any]:
    enhancements = (
        "canonical serialization",
        "content-addressed payloads",
        "immutable envelopes",
        "immutable event history",
        "trace identity",
        "parent-child flow identity",
        "lineage propagation",
        "provenance propagation",
        "typed capability contracts",
        "schema boundaries",
        "capability requirements",
        "ownership preservation",
        "bounded payload size",
        "bounded hop count",
        "bounded history",
        "deadline enforcement",
        "terminal-state protection",
        "failure isolation",
        "idempotency declaration",
        "replay declaration",
        "deterministic replay projection",
        "pipeline composition",
        "flow forking",
        "extension reservations",
        "unbuilt-exile preparation",
        "explicit context propagation",
        "stable digests",
        "strict canonical-json boundary",
        "zero authority creation",
        "zero exile-behavior fabrication",
    )

    projection = {
        "schema":
            schema,
        "owner":
            owner,
        "pattern":
            (
                "substantiate once -> instance -> compose -> "
                "typed segue -> project"
            ),
        "enhancements":
            list(
                enhancements
            ),
        "enhancement_count":
            len(
                enhancements
            ),
        "integration": {
            "urge":
                "instances flow contracts for improvement execution",
            "palaver":
                "instances flow contracts for conversation exchange",
            "envoy":
                "instances flow contracts for personality projection",
            "opus":
                "instances flow contracts for provider orchestration",
            "niche":
                "instances flow contracts for task execution",
            "underscore":
                "instances flow contracts without preassigning exile-specific semantics",
            "unbuilt_exiles":
                "prepare_exile reserves modular extension space without fabricating behavior",
        },
        "boundaries": {
            "existing_registries_remain_authoritative":
                True,
            "existing_exile_ownership_remains_authoritative":
                True,
            "external_dependencies_added":
                False,
            "creates_authority":
                False,
        },
    }

    projection[
        "digest"
    ] = _digest(
        projection
    )

    return projection


__all__ = [
    "architecture_projection",
    "compose_pipeline",
    "create_flow",
    "execute_hop",
    "exile_flow_contract_error",
    "exile_flow_error",
    "exile_flow_limit_error",
    "exile_flow_transition_error",
    "flow_contract",
    "flow_envelope",
    "flow_event",
    "flow_limits",
    "fork_flow",
    "owner",
    "prepare_exile",
    "replay_projection",
    "schema",
    "transition",
    "validate_contract",
]
