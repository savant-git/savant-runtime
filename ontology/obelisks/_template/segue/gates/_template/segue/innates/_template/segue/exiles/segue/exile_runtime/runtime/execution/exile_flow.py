from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import uuid4


schema = "savant://runtime/exiles/flow/1.0.1"
owner = "exile:segue"

states = frozenset(
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

terminal = frozenset(
    {
        "complete",
        "failed",
        "cancelled",
        "expired",
    }
)

unforkable = frozenset(
    {
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


def _text(value: Any, name: str) -> str:
    result = str(value or "").strip().lower()

    if not result:
        raise exile_flow_contract_error(name + " is required")

    return result


def _map(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(value, Mapping):
        raise exile_flow_contract_error(name + " must be a mapping")

    return dict(value)


def _texts(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        value = (value,)

    if not isinstance(value, Sequence):
        raise exile_flow_contract_error(name + " must be a sequence")

    return tuple(
        dict.fromkeys(
            item
            for item in (_text(entry, name) for entry in value)
            if item
        )
    )


@dataclass(frozen=True, slots=True)
class flow_limits:
    max_hops: int = 64
    max_payload_bytes: int = 4_194_304
    max_history: int = 256
    deadline_ns: int | None = None

    def __post_init__(self) -> None:
        ranges = (
            ("max_hops", 1, 4096),
            ("max_payload_bytes", 1, 1_073_741_824),
            ("max_history", 1, 16_384),
        )

        for name, minimum, maximum in ranges:
            value = getattr(self, name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise exile_flow_contract_error(name + " out of range")

        if self.deadline_ns is not None:
            if (
                isinstance(self.deadline_ns, bool)
                or not isinstance(self.deadline_ns, int)
                or self.deadline_ns < 1
            ):
                raise exile_flow_contract_error("deadline_ns invalid")

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
            _text(self.capability, "capability"),
        )
        object.__setattr__(
            self,
            "source",
            _text(self.source, "source"),
        )
        object.__setattr__(
            self,
            "target",
            _text(self.target, "target"),
        )
        object.__setattr__(
            self,
            "required_capabilities",
            _texts(
                self.required_capabilities,
                "required_capabilities",
            ),
        )
        object.__setattr__(
            self,
            "accepted_schemas",
            _texts(
                self.accepted_schemas,
                "accepted_schemas",
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
        if self.state not in states:
            raise exile_flow_contract_error(
                "invalid flow state"
            )

        object.__setattr__(
            self,
            "detail",
            MappingProxyType(dict(self.detail)),
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
        object.__setattr__(
            self,
            "payload",
            MappingProxyType(dict(self.payload)),
        )
        object.__setattr__(
            self,
            "provenance",
            MappingProxyType(dict(self.provenance)),
        )
        object.__setattr__(
            self,
            "context",
            MappingProxyType(dict(self.context)),
        )

    def projection(
        self,
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
                "projection_only": True,
            },
        }

        if include_payload:
            result["payload"] = dict(self.payload)

        result["digest"] = _digest(result)

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
    normalized_payload = _map(
        payload,
        "payload",
    )

    resolved_limits = limits or flow_limits()

    if (
        len(_canonical(normalized_payload))
        > resolved_limits.max_payload_bytes
    ):
        raise exile_flow_limit_error(
            "payload exceeds max_payload_bytes"
        )

    now = time.time_ns()
    flow_id = uuid4().hex

    normalized_source = _text(
        source,
        "source",
    )
    normalized_target = _text(
        target,
        "target",
    )
    normalized_capability = _text(
        capability,
        "capability",
    )

    payload_digest = _digest(
        normalized_payload
    )

    event = flow_event(
        sequence=0,
        state="created",
        exile=normalized_source,
        capability=normalized_capability,
        at_ns=now,
        input_digest=None,
        output_digest=payload_digest,
        detail={
            "target": normalized_target,
        },
    )

    return flow_envelope(
        flow_id=flow_id,
        trace_id=trace_id or flow_id,
        parent_flow_id=parent_flow_id,
        state="created",
        source=normalized_source,
        target=normalized_target,
        capability=normalized_capability,
        payload=normalized_payload,
        payload_schema=payload_schema,
        payload_digest=payload_digest,
        hop=0,
        created_ns=now,
        updated_ns=now,
        limits=resolved_limits,
        lineage=_texts(
            lineage,
            "lineage",
        ),
        provenance=_map(
            provenance,
            "provenance",
        ),
        context=_map(
            context,
            "context",
        ),
        history=(event,),
    )


def _limits(
    envelope: flow_envelope,
    fork: bool = False,
) -> None:
    forbidden_states = (
        unforkable
        if fork
        else terminal
    )

    if envelope.state in forbidden_states:
        raise exile_flow_transition_error(
            "flow state cannot transition"
        )

    if (
        envelope.limits.deadline_ns is not None
        and time.time_ns()
        > envelope.limits.deadline_ns
    ):
        raise exile_flow_limit_error(
            "flow deadline exceeded"
        )

    if envelope.hop >= envelope.limits.max_hops:
        raise exile_flow_limit_error(
            "flow hop limit exceeded"
        )


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
    _limits(envelope)

    normalized_state = _text(
        state,
        "state",
    )

    if normalized_state not in states:
        raise exile_flow_transition_error(
            "invalid target state"
        )

    normalized_payload = (
        dict(envelope.payload)
        if payload is None
        else _map(payload, "payload")
    )

    if (
        len(_canonical(normalized_payload))
        > envelope.limits.max_payload_bytes
    ):
        raise exile_flow_limit_error(
            "payload exceeds max_payload_bytes"
        )

    now = time.time_ns()
    payload_digest = _digest(
        normalized_payload
    )

    resolved_capability = (
        capability
        or envelope.capability
    )

    resolved_target = (
        target
        or envelope.target
    )

    event = flow_event(
        sequence=len(envelope.history),
        state=normalized_state,
        exile=_text(
            exile,
            "exile",
        ),
        capability=resolved_capability,
        at_ns=now,
        input_digest=envelope.payload_digest,
        output_digest=payload_digest,
        detail=_map(
            detail,
            "detail",
        ),
    )

    history = envelope.history + (event,)

    if len(history) > envelope.limits.max_history:
        raise exile_flow_limit_error(
            "flow history limit exceeded"
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
            else payload_schema
        ),
        payload_digest=payload_digest,
        hop=envelope.hop + 1,
        created_ns=envelope.created_ns,
        updated_ns=now,
        limits=envelope.limits,
        lineage=(
            envelope.lineage
            + (envelope.payload_digest,)
        ),
        provenance=dict(
            envelope.provenance
        ),
        context=dict(
            envelope.context
        ),
        history=history,
        version=envelope.version,
    )


def validate_contract(
    envelope: flow_envelope,
    contract: flow_contract,
    *,
    capabilities: Iterable[str] = (),
) -> None:
    actual = (
        envelope.source,
        envelope.target,
        envelope.capability,
    )

    expected = (
        contract.source,
        contract.target,
        contract.capability,
    )

    if actual != expected:
        raise exile_flow_contract_error(
            "flow does not satisfy contract"
        )

    available = set(
        _texts(
            tuple(capabilities),
            "capabilities",
        )
    )

    missing = (
        set(contract.required_capabilities)
        - available
    )

    if missing:
        raise exile_flow_contract_error(
            "missing required capabilities: "
            + ", ".join(sorted(missing))
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
    _limits(envelope)

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
            "contract_digest": _digest(
                contract.projection()
            ),
        },
    )

    try:
        output = handler(
            dict(running.payload)
        )
    except Exception as exc:
        return transition(
            running,
            state="failed",
            exile=contract.target,
            detail={
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )

    if not isinstance(output, Mapping):
        return transition(
            running,
            state="failed",
            exile=contract.target,
            detail={
                "error_type":
                    "invalid-handler-output",
            },
        )

    return transition(
        running,
        state="complete",
        exile=contract.target,
        payload=output,
        payload_schema=contract.emitted_schema,
        detail={
            "contract_digest": _digest(
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
    _limits(
        envelope,
        True,
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
            **dict(envelope.provenance),
            "parent_flow_id":
                envelope.flow_id,
        },
        context={
            **dict(envelope.context),
            **_map(
                context,
                "context",
            ),
        },
        limits=envelope.limits,
    )


def replay_projection(
    envelope: flow_envelope,
) -> dict[str, Any]:
    result = {
        "schema": schema,
        "flow_id": envelope.flow_id,
        "trace_id": envelope.trace_id,
        "parent_flow_id":
            envelope.parent_flow_id,
        "initial_digest": (
            envelope.history[0].output_digest
            if envelope.history
            else None
        ),
        "current_digest":
            envelope.payload_digest,
        "events": [
            {
                "sequence": event.sequence,
                "state": event.state,
                "exile": event.exile,
                "capability":
                    event.capability,
                "input_digest":
                    event.input_digest,
                "output_digest":
                    event.output_digest,
            }
            for event in envelope.history
        ],
        "replayable": True,
        "creates_authority": False,
    }

    result["digest"] = _digest(result)

    return result


def prepare_exile(
    *,
    exile: str,
    capabilities: Sequence[str] = (),
    accepts: Sequence[str] = (),
    emits: Sequence[str] = (),
    extensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema":
            "savant://runtime/exiles/preparation/1.0.0",
        "owner": owner,
        "exile": _text(
            exile,
            "exile",
        ),
        "state": "prepared",
        "capabilities": list(
            _texts(
                capabilities,
                "capabilities",
            )
        ),
        "accepts": list(
            _texts(
                accepts,
                "accepts",
            )
        ),
        "emits": list(
            _texts(
                emits,
                "emits",
            )
        ),
        "extensions": _map(
            extensions,
            "extensions",
        ),
        "reserved": {
            "runtime": {},
            "contracts": {},
            "adapters": {},
            "projections": {},
            "exile_specific": {},
        },
        "boundaries": {
            "creates_exile_behavior": False,
            "creates_authority": False,
            "requires_exile_specific_code": False,
            "extension_space_reserved": True,
        },
    }

    result["digest"] = _digest(result)

    return result


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

    if first_contract.source != _text(
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
            previous_contract = (
                steps[index - 1][0]
            )

            if (
                previous_contract.target
                != contract.source
            ):
                raise exile_flow_contract_error(
                    "pipeline contracts are not contiguous"
                )

            envelope = fork_flow(
                envelope,
                target=contract.target,
                capability=contract.capability,
                payload_schema=
                    envelope.payload_schema,
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
        "completed-parent composition",
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

    result = {
        "schema": schema,
        "owner": owner,
        "pattern":
            "substantiate once -> instance -> compose -> typed segue -> project",
        "enhancements": list(enhancements),
        "enhancement_count":
            len(enhancements),
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

    result["digest"] = _digest(result)

    return result


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
