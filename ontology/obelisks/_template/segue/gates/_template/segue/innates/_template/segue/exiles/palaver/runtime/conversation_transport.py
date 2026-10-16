from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/palaver/"
    "conversation-transport/1.0.0"
)

owner = "exile:palaver"

session_pattern = re.compile(
    r"^[a-zA-Z0-9._:-]{1,160}$"
)

request_pattern = re.compile(
    r"^[a-zA-Z0-9._:-]{1,160}$"
)

event_types = frozenset(
    {
        "request.accepted",
        "request.started",
        "response.delta",
        "response.completed",
        "response.failed",
        "tool.requested",
        "tool.started",
        "tool.completed",
        "tool.failed",
        "execution.cancel_requested",
        "execution.cancelled",
        "execution.state",
        "session.state",
        "heartbeat",
    }
)

terminal_event_types = frozenset(
    {
        "response.completed",
        "response.failed",
        "execution.cancelled",
    }
)


class conversation_transport_error(
    ValueError
):
    pass


class cursor_expired(
    conversation_transport_error
):
    pass


class cursor_invalid(
    conversation_transport_error
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _identifier(
    value: Any,
    *,
    name: str,
    pattern: re.Pattern[str],
) -> str:
    result = str(
        value
        or ""
    ).strip()

    if not result:
        raise conversation_transport_error(
            f"{name} is required"
        )

    if not pattern.fullmatch(
        result
    ):
        raise conversation_transport_error(
            f"{name} is invalid"
        )

    return result


def session_id(
    value: Any,
) -> str:
    return _identifier(
        value,
        name="session_id",
        pattern=session_pattern,
    )


def request_id(
    value: Any,
) -> str:
    return _identifier(
        value,
        name="request_id",
        pattern=request_pattern,
    )


def event_type(
    value: Any,
) -> str:
    result = str(
        value
        or ""
    ).strip().casefold()

    if result not in event_types:
        raise conversation_transport_error(
            "unsupported conversation event type"
        )

    return result


def finite_number(
    value: Any,
    *,
    name: str,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise conversation_transport_error(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(
        result
    ):
        raise conversation_transport_error(
            f"{name} must be finite"
        )

    return result


def normalize_payload(
    value: Any,
    *,
    maximum_bytes: int = 262144,
) -> Any:
    try:
        serialized = canonical_json(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise conversation_transport_error(
            "event payload is not JSON compatible"
        ) from exc

    size = len(
        serialized.encode(
            "utf-8"
        )
    )

    if size > maximum_bytes:
        raise conversation_transport_error(
            "event payload exceeds configured limit"
        )

    return json.loads(
        serialized
    )


@dataclass(
    frozen=True,
    slots=True,
)
class conversation_event:
    session_id: str
    request_id: str
    sequence: int
    type: str
    payload: Any
    observed_at: float
    event_id: str
    semantic_digest: str
    terminal: bool
    authority_effect: str = "none"

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "owner":
                owner,
            "type":
                self.type,
            "session_id":
                self.session_id,
            "request_id":
                self.request_id,
            "sequence":
                self.sequence,
            "payload":
                self.payload,
            "observed_at":
                self.observed_at,
            "event_id":
                self.event_id,
            "semantic_digest":
                self.semantic_digest,
            "terminal":
                self.terminal,
            "authority_effect":
                self.authority_effect,
            "boundaries": {
                "conversation_owner":
                    "palaver",
                "provider_owner":
                    "opus",
                "persona_owner":
                    "envoy",
                "task_owner":
                    "niche",
                "mutation_owner":
                    "coda",
                "executes_provider":
                    False,
                "creates_authority":
                    False,
            },
        }


def project_event(
    *,
    session: Any,
    request: Any,
    sequence: int,
    kind: Any,
    payload: Any,
    observed_at: float | None = None,
) -> conversation_event:
    normalized_session = session_id(
        session
    )

    normalized_request = request_id(
        request
    )

    normalized_kind = event_type(
        kind
    )

    if (
        not isinstance(
            sequence,
            int,
        )
        or isinstance(
            sequence,
            bool,
        )
        or sequence < 1
    ):
        raise conversation_transport_error(
            "sequence must be a positive integer"
        )

    normalized_payload = normalize_payload(
        payload
    )

    semantic = {
        "schema":
            schema,
        "owner":
            owner,
        "session_id":
            normalized_session,
        "request_id":
            normalized_request,
        "sequence":
            sequence,
        "type":
            normalized_kind,
        "payload":
            normalized_payload,
        "authority_effect":
            "none",
    }

    semantic_digest = digest(
        semantic
    )

    observation = (
        finite_number(
            observed_at,
            name="observed_at",
        )
        if observed_at is not None
        else time.time()
    )

    event_identifier = (
        "palevt_"
        + semantic_digest[:32]
    )

    return conversation_event(
        session_id=
            normalized_session,
        request_id=
            normalized_request,
        sequence=
            sequence,
        type=
            normalized_kind,
        payload=
            normalized_payload,
        observed_at=
            observation,
        event_id=
            event_identifier,
        semantic_digest=
            semantic_digest,
        terminal=(
            normalized_kind
            in terminal_event_types
        ),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class resume_cursor:
    session_id: str
    sequence: int
    semantic_digest: str

    def encode(
        self,
    ) -> str:
        payload = {
            "session_id":
                self.session_id,
            "sequence":
                self.sequence,
            "semantic_digest":
                self.semantic_digest,
        }

        encoded = (
            canonical_json(
                payload
            )
            .encode(
                "utf-8"
            )
            .hex()
        )

        return (
            "palcur_"
            + encoded
        )


def encode_cursor(
    event: conversation_event,
) -> str:
    return resume_cursor(
        session_id=
            event.session_id,
        sequence=
            event.sequence,
        semantic_digest=
            event.semantic_digest,
    ).encode()


def decode_cursor(
    value: Any,
) -> resume_cursor:
    raw = str(
        value
        or ""
    ).strip()

    if not raw.startswith(
        "palcur_"
    ):
        raise cursor_invalid(
            "invalid Palaver cursor"
        )

    hexadecimal = raw[
        len(
            "palcur_"
        ):
    ]

    try:
        payload = json.loads(
            bytes.fromhex(
                hexadecimal
            ).decode(
                "utf-8"
            )
        )
    except (
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise cursor_invalid(
            "invalid Palaver cursor"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise cursor_invalid(
            "invalid Palaver cursor"
        )

    normalized_session = session_id(
        payload.get(
            "session_id"
        )
    )

    sequence = payload.get(
        "sequence"
    )

    if (
        not isinstance(
            sequence,
            int,
        )
        or isinstance(
            sequence,
            bool,
        )
        or sequence < 1
    ):
        raise cursor_invalid(
            "invalid Palaver cursor sequence"
        )

    semantic = str(
        payload.get(
            "semantic_digest"
        )
        or ""
    ).strip()

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        semantic,
    ):
        raise cursor_invalid(
            "invalid Palaver cursor digest"
        )

    return resume_cursor(
        session_id=
            normalized_session,
        sequence=
            sequence,
        semantic_digest=
            semantic,
    )


class cancellation_token:
    def __init__(
        self,
        *,
        session: Any,
        request: Any,
    ) -> None:
        self.session_id = session_id(
            session
        )

        self.request_id = request_id(
            request
        )

        self._event = (
            threading.Event()
        )

        self._lock = (
            threading.Lock()
        )

        self._reason: str | None = None

    def cancel(
        self,
        reason: Any = None,
    ) -> bool:
        normalized_reason = str(
            reason
            or "cancel_requested"
        ).strip()

        if len(
            normalized_reason
        ) > 512:
            normalized_reason = (
                normalized_reason[:512]
            )

        with self._lock:
            if self._event.is_set():
                return False

            self._reason = (
                normalized_reason
            )

            self._event.set()

            return True

    def cancelled(
        self,
    ) -> bool:
        return self._event.is_set()

    def reason(
        self,
    ) -> str | None:
        with self._lock:
            return self._reason

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "owner":
                owner,
            "type":
                "palaver_cancellation_projection",
            "session_id":
                self.session_id,
            "request_id":
                self.request_id,
            "cancelled":
                self.cancelled(),
            "reason":
                self.reason(),
            "authority_effect":
                "none",
        }


class conversation_event_buffer:
    def __init__(
        self,
        *,
        session: Any,
        maximum_events: int = 2048,
    ) -> None:
        self.session_id = session_id(
            session
        )

        if (
            not isinstance(
                maximum_events,
                int,
            )
            or isinstance(
                maximum_events,
                bool,
            )
            or not 16 <= maximum_events <= 65536
        ):
            raise conversation_transport_error(
                "maximum_events must be between "
                "16 and 65536"
            )

        self.maximum_events = (
            maximum_events
        )

        self._events: deque[
            conversation_event
        ] = deque(
            maxlen=maximum_events
        )

        self._sequence = 0

        self._request_event_ids: dict[
            str,
            set[str],
        ] = {}

        self._cancellations: dict[
            str,
            cancellation_token,
        ] = {}

        self._condition = (
            threading.Condition(
                threading.RLock()
            )
        )

    @property
    def latest_sequence(
        self,
    ) -> int:
        with self._condition:
            return self._sequence

    def cancellation(
        self,
        request: Any,
    ) -> cancellation_token:
        normalized_request = request_id(
            request
        )

        with self._condition:
            token = (
                self._cancellations.get(
                    normalized_request
                )
            )

            if token is None:
                token = cancellation_token(
                    session=self.session_id,
                    request=
                        normalized_request,
                )

                self._cancellations[
                    normalized_request
                ] = token

            return token

    def cancel(
        self,
        request: Any,
        reason: Any = None,
    ) -> bool:
        token = self.cancellation(
            request
        )

        changed = token.cancel(
            reason
        )

        if changed:
            self.publish(
                request=request,
                kind=
                    "execution.cancel_requested",
                payload={
                    "reason":
                        token.reason(),
                },
            )

        return changed

    def publish(
        self,
        *,
        request: Any,
        kind: Any,
        payload: Any,
        dedupe_key: Any = None,
    ) -> conversation_event:
        normalized_request = request_id(
            request
        )

        normalized_kind = event_type(
            kind
        )

        normalized_payload = normalize_payload(
            payload
        )

        with self._condition:
            next_sequence = (
                self._sequence
                + 1
            )

            if dedupe_key is not None:
                normalized_dedupe = str(
                    dedupe_key
                ).strip()

                if not normalized_dedupe:
                    raise conversation_transport_error(
                        "dedupe_key cannot be empty"
                    )

                dedupe_identity = digest(
                    {
                        "session_id":
                            self.session_id,
                        "request_id":
                            normalized_request,
                        "type":
                            normalized_kind,
                        "dedupe_key":
                            normalized_dedupe,
                        "payload":
                            normalized_payload,
                    }
                )

                known = (
                    self._request_event_ids
                    .setdefault(
                        normalized_request,
                        set(),
                    )
                )

                if dedupe_identity in known:
                    for existing in reversed(
                        self._events
                    ):
                        if (
                            existing.request_id
                            == normalized_request
                            and digest(
                                {
                                    "session_id":
                                        self.session_id,
                                    "request_id":
                                        normalized_request,
                                    "type":
                                        existing.type,
                                    "dedupe_key":
                                        normalized_dedupe,
                                    "payload":
                                        existing.payload,
                                }
                            )
                            == dedupe_identity
                        ):
                            return existing

                known.add(
                    dedupe_identity
                )

            event = project_event(
                session=
                    self.session_id,
                request=
                    normalized_request,
                sequence=
                    next_sequence,
                kind=
                    normalized_kind,
                payload=
                    normalized_payload,
            )

            self._events.append(
                event
            )

            self._sequence = (
                next_sequence
            )

            self._condition.notify_all()

            return event

    def snapshot(
        self,
    ) -> tuple[
        conversation_event,
        ...,
    ]:
        with self._condition:
            return tuple(
                self._events
            )

    def resume(
        self,
        cursor: Any = None,
        *,
        limit: int = 256,
    ) -> tuple[
        conversation_event,
        ...,
    ]:
        if (
            not isinstance(
                limit,
                int,
            )
            or isinstance(
                limit,
                bool,
            )
            or not 1 <= limit <= 4096
        ):
            raise conversation_transport_error(
                "resume limit must be between "
                "1 and 4096"
            )

        with self._condition:
            events = tuple(
                self._events
            )

            if cursor in (
                None,
                "",
            ):
                return events[
                    -limit:
                ]

            decoded = decode_cursor(
                cursor
            )

            if (
                decoded.session_id
                != self.session_id
            ):
                raise cursor_invalid(
                    "cursor belongs to another session"
                )

            if not events:
                raise cursor_expired(
                    "cursor cannot be resumed"
                )

            earliest = (
                events[0]
            )

            latest = (
                events[-1]
            )

            if (
                decoded.sequence
                < earliest.sequence
            ):
                raise cursor_expired(
                    "cursor is older than retained history"
                )

            if (
                decoded.sequence
                > latest.sequence
            ):
                raise cursor_invalid(
                    "cursor is ahead of session history"
                )

            matched = False

            result: list[
                conversation_event
            ] = []

            for event in events:
                if (
                    event.sequence
                    == decoded.sequence
                ):
                    if (
                        event.semantic_digest
                        != decoded.semantic_digest
                    ):
                        raise cursor_invalid(
                            "cursor digest does not match "
                            "session history"
                        )

                    matched = True
                    continue

                if (
                    matched
                    and len(
                        result
                    ) < limit
                ):
                    result.append(
                        event
                    )

            if not matched:
                raise cursor_expired(
                    "cursor event is no longer retained"
                )

            return tuple(
                result
            )

    def wait_after(
        self,
        sequence: int,
        *,
        timeout: float = 15.0,
        limit: int = 256,
    ) -> tuple[
        conversation_event,
        ...,
    ]:
        if (
            not isinstance(
                sequence,
                int,
            )
            or isinstance(
                sequence,
                bool,
            )
            or sequence < 0
        ):
            raise conversation_transport_error(
                "sequence must be a nonnegative integer"
            )

        normalized_timeout = finite_number(
            timeout,
            name="timeout",
        )

        if not 0 <= normalized_timeout <= 60:
            raise conversation_transport_error(
                "timeout must be between 0 and 60 seconds"
            )

        if (
            not isinstance(
                limit,
                int,
            )
            or isinstance(
                limit,
                bool,
            )
            or not 1 <= limit <= 4096
        ):
            raise conversation_transport_error(
                "limit must be between 1 and 4096"
            )

        deadline = (
            time.monotonic()
            + normalized_timeout
        )

        with self._condition:
            while (
                self._sequence <= sequence
            ):
                remaining = (
                    deadline
                    - time.monotonic()
                )

                if remaining <= 0:
                    return ()

                self._condition.wait(
                    remaining
                )

            return tuple(
                event
                for event
                in self._events
                if event.sequence
                > sequence
            )[:limit]

    def compact_projection(
        self,
    ) -> dict[str, Any]:
        with self._condition:
            events = tuple(
                self._events
            )

            terminal_requests = sorted(
                {
                    event.request_id
                    for event in events
                    if event.terminal
                }
            )

            active_requests = sorted(
                {
                    event.request_id
                    for event in events
                }
                - set(
                    terminal_requests
                )
            )

            projection = {
                "schema":
                    schema,
                "owner":
                    owner,
                "type":
                    "palaver_conversation_transport",
                "session_id":
                    self.session_id,
                "latest_sequence":
                    self._sequence,
                "retained_events":
                    len(
                        events
                    ),
                "maximum_events":
                    self.maximum_events,
                "earliest_sequence":
                    (
                        events[0].sequence
                        if events
                        else None
                    ),
                "active_requests":
                    active_requests,
                "terminal_requests":
                    terminal_requests,
                "cancelled_requests":
                    sorted(
                        request
                        for request, token
                        in self._cancellations.items()
                        if token.cancelled()
                    ),
                "resume_supported":
                    True,
                "bounded_history":
                    True,
                "persistence":
                    "not_owned_by_transport_primitive",
                "deterministic_event_identity":
                    True,
                "authority_effect":
                    "none",
                "boundaries": {
                    "conversation_owner":
                        "palaver",
                    "provider_owner":
                        "opus",
                    "persistent_session_store":
                        False,
                    "provider_stream_execution":
                        False,
                    "mutation_authority":
                        False,
                },
            }

            projection[
                "projection_digest"
            ] = digest(
                projection
            )

            return projection


class conversation_transport_registry:
    def __init__(
        self,
        *,
        maximum_sessions: int = 256,
        maximum_events_per_session: int = 2048,
    ) -> None:
        if (
            not isinstance(
                maximum_sessions,
                int,
            )
            or isinstance(
                maximum_sessions,
                bool,
            )
            or not 1 <= maximum_sessions <= 4096
        ):
            raise conversation_transport_error(
                "maximum_sessions must be between "
                "1 and 4096"
            )

        self.maximum_sessions = (
            maximum_sessions
        )

        self.maximum_events_per_session = (
            maximum_events_per_session
        )

        self._sessions: dict[
            str,
            conversation_event_buffer,
        ] = {}

        self._order: deque[str] = deque()

        self._lock = (
            threading.RLock()
        )

    def session(
        self,
        session: Any,
    ) -> conversation_event_buffer:
        normalized_session = session_id(
            session
        )

        with self._lock:
            existing = self._sessions.get(
                normalized_session
            )

            if existing is not None:
                return existing

            while (
                len(
                    self._sessions
                )
                >= self.maximum_sessions
                and self._order
            ):
                oldest = (
                    self._order.popleft()
                )

                self._sessions.pop(
                    oldest,
                    None,
                )

            created = (
                conversation_event_buffer(
                    session=
                        normalized_session,
                    maximum_events=
                        self.maximum_events_per_session,
                )
            )

            self._sessions[
                normalized_session
            ] = created

            self._order.append(
                normalized_session
            )

            return created

    def projection(
        self,
    ) -> dict[str, Any]:
        with self._lock:
            sessions = sorted(
                self._sessions
            )

            projection = {
                "schema":
                    schema,
                "owner":
                    owner,
                "type":
                    "palaver_conversation_transport_registry",
                "session_count":
                    len(
                        sessions
                    ),
                "maximum_sessions":
                    self.maximum_sessions,
                "maximum_events_per_session":
                    self.maximum_events_per_session,
                "sessions":
                    sessions,
                "process_local":
                    True,
                "persistent_authority":
                    False,
                "authority_effect":
                    "none",
            }

            projection[
                "projection_digest"
            ] = digest(
                projection
            )

            return projection
