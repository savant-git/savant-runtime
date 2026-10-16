from __future__ import annotations

import json
import secrets
import threading
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from .conversation_transport import (
        conversation_event_buffer,
        conversation_transport_registry,
        request_id,
        session_id,
    )
    from .session_store import (
        default_database,
        session_store,
    )
except ImportError:
    from conversation_transport import (
        conversation_event_buffer,
        conversation_transport_registry,
        request_id,
        session_id,
    )
    from session_store import (
        default_database,
        session_store,
    )


schema = (
    "savant://runtime/palaver/"
    "session-runtime/1.0.0"
)

owner = "exile:palaver"


class session_runtime_error(
    RuntimeError
):
    pass


def new_session_id() -> str:
    return (
        "palses_"
        + secrets.token_hex(
            16
        )
    )


class session_runtime:
    def __init__(
        self,
        *,
        database: Path | str = default_database,
        maximum_sessions: int = 256,
        maximum_events_per_session: int = 2048,
    ) -> None:
        self.store = session_store(
            database
        )

        self.registry = (
            conversation_transport_registry(
                maximum_sessions=
                    maximum_sessions,
                maximum_events_per_session=
                    maximum_events_per_session,
            )
        )

        self.maximum_events_per_session = (
            maximum_events_per_session
        )

        self._restored: set[str] = set()

        self._lock = (
            threading.RLock()
        )

    def close(
        self,
    ) -> None:
        self.store.close()

    def open(
        self,
        session: Any = None,
    ) -> dict[str, Any]:
        identifier = (
            session_id(
                session
            )
            if str(
                session
                or ""
            ).strip()
            else new_session_id()
        )

        with self._lock:
            existing = self.store.load_session(
                identifier
            )

            if existing is None:
                self.store.ensure_session(
                    identifier
                )

            buffer = self._buffer(
                identifier
            )

            recovery = (
                self.store.recovery_projection(
                    identifier
                )
            )

            return {
                "ok":
                    True,
                "schema":
                    schema,
                "owner":
                    owner,
                "session_id":
                    identifier,
                "created":
                    existing is None,
                "latest_sequence":
                    buffer.latest_sequence,
                "recovery":
                    recovery,
                "authority_effect":
                    "none",
                "boundaries": {
                    "conversation_owner":
                        "palaver",
                    "provider_owner":
                        "opus",
                    "task_owner":
                        "niche",
                    "persona_owner":
                        "envoy",
                    "mutation_owner":
                        "coda",
                },
            }

    def _buffer(
        self,
        session: Any,
    ) -> conversation_event_buffer:
        identifier = session_id(
            session
        )

        with self._lock:
            buffer = self.registry.session(
                identifier
            )

            if identifier in self._restored:
                return buffer

            persisted = self.store.load_events(
                identifier,
                limit=
                    self.maximum_events_per_session,
            )

            if persisted:
                for event in persisted:
                    rebuilt = buffer.publish(
                        request=
                            event.request_id,
                        kind=
                            event.type,
                        payload=
                            event.payload,
                    )

                    if (
                        rebuilt.sequence
                        != event.sequence
                        or rebuilt.semantic_digest
                        != event.semantic_digest
                    ):
                        raise session_runtime_error(
                            "session replay diverged"
                        )

            self._restored.add(
                identifier
            )

            return buffer

    def publish(
        self,
        *,
        session: Any,
        request: Any,
        kind: Any,
        payload: Any,
        dedupe_key: Any = None,
    ) -> dict[str, Any]:
        identifier = session_id(
            session
        )

        self.store.ensure_session(
            identifier
        )

        buffer = self._buffer(
            identifier
        )

        event = buffer.publish(
            request=request,
            kind=kind,
            payload=payload,
            dedupe_key=
                dedupe_key,
        )

        self.store.persist_event(
            event
        )

        return event.projection()

    def cancel(
        self,
        *,
        session: Any,
        request: Any,
        reason: Any = None,
    ) -> dict[str, Any]:
        identifier = session_id(
            session
        )

        normalized_request = request_id(
            request
        )

        self.store.ensure_session(
            identifier
        )

        buffer = self._buffer(
            identifier
        )

        before = (
            buffer.latest_sequence
        )

        changed = buffer.cancel(
            normalized_request,
            reason,
        )

        if changed:
            events = tuple(
                event
                for event
                in buffer.snapshot()
                if event.sequence > before
            )

            self.store.persist_events(
                events
            )

        token = buffer.cancellation(
            normalized_request
        )

        return {
            "ok":
                True,
            "schema":
                schema,
            "owner":
                owner,
            "session_id":
                identifier,
            "request_id":
                normalized_request,
            "changed":
                changed,
            "cancellation":
                token.projection(),
            "latest_sequence":
                buffer.latest_sequence,
            "authority_effect":
                "none",
        }

    def events(
        self,
        *,
        session: Any,
        after_sequence: int = 0,
        wait_seconds: float = 0.0,
        limit: int = 256,
    ) -> dict[str, Any]:
        identifier = session_id(
            session
        )

        self.store.ensure_session(
            identifier
        )

        buffer = self._buffer(
            identifier
        )

        if after_sequence < 0:
            raise session_runtime_error(
                "after_sequence cannot be negative"
            )

        if wait_seconds > 0:
            events = buffer.wait_after(
                after_sequence,
                timeout=
                    min(
                        wait_seconds,
                        30.0,
                    ),
                limit=limit,
            )
        else:
            events = tuple(
                event
                for event
                in buffer.snapshot()
                if event.sequence
                > after_sequence
            )[:limit]

        return {
            "ok":
                True,
            "schema":
                schema,
            "owner":
                owner,
            "session_id":
                identifier,
            "after_sequence":
                after_sequence,
            "latest_sequence":
                buffer.latest_sequence,
            "events": [
                event.projection()
                for event in events
            ],
            "authority_effect":
                "none",
        }

    def recover(
        self,
        session: Any,
    ) -> dict[str, Any]:
        identifier = session_id(
            session
        )

        opened = self.open(
            identifier
        )

        buffer = self._buffer(
            identifier
        )

        opened[
            "transport"
        ] = buffer.compact_projection()

        opened[
            "events"
        ] = [
            event.projection()
            for event
            in buffer.snapshot()
        ]

        return opened


def _send_json(
    handler: Any,
    payload: Any,
    status: int = 200,
) -> None:
    body = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode(
        "utf-8"
    )

    handler.send_response(
        status
    )

    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8",
    )

    handler.send_header(
        "Content-Length",
        str(
            len(
                body
            )
        ),
    )

    handler.end_headers()

    if (
        getattr(
            handler,
            "command",
            ""
        )
        != "HEAD"
    ):
        handler.wfile.write(
            body
        )


def _body_json(
    handler: Any,
) -> dict[str, Any]:
    raw_length = (
        handler.headers.get(
            "Content-Length",
            "0",
        )
        if getattr(
            handler,
            "headers",
            None,
        )
        is not None
        else "0"
    )

    try:
        length = int(
            raw_length
            or 0
        )
    except ValueError as exc:
        raise session_runtime_error(
            "invalid content length"
        ) from exc

    if length <= 0:
        return {}

    raw = handler.rfile.read(
        length
    )

    try:
        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise session_runtime_error(
            "invalid JSON payload"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise session_runtime_error(
            "request body must be an object"
        )

    return value


def _query_session(
    handler: Any,
) -> str:
    parsed = urlparse(
        handler.path
    )

    query = parse_qs(
        parsed.query
    )

    return str(
        (
            query.get(
                "session_id"
            )
            or [""]
        )[0]
        or ""
    ).strip()


def _query_int(
    query: dict[str, list[str]],
    name: str,
    default: int,
) -> int:
    raw = str(
        (
            query.get(
                name
            )
            or [
                str(
                    default
                )
            ]
        )[0]
    ).strip()

    try:
        return int(
            raw
        )
    except ValueError as exc:
        raise session_runtime_error(
            f"{name} must be an integer"
        ) from exc


def _query_float(
    query: dict[str, list[str]],
    name: str,
    default: float,
) -> float:
    raw = str(
        (
            query.get(
                name
            )
            or [
                str(
                    default
                )
            ]
        )[0]
    ).strip()

    try:
        return float(
            raw
        )
    except ValueError as exc:
        raise session_runtime_error(
            f"{name} must be numeric"
        ) from exc


def make_session_handler(
    canonical_factory: Any,
    legacy: Any,
    *,
    runtime: session_runtime,
):
    parent = canonical_factory(
        legacy
    )

    class SessionCanonicalHandler(
        parent
    ):
        def do_GET(
            self,
        ) -> None:
            parsed = urlparse(
                self.path
            )

            path = parsed.path

            if path not in {
                "/api/session/recover",
                "/api/session/events",
            }:
                super().do_GET()
                return

            try:
                query = parse_qs(
                    parsed.query
                )

                session = str(
                    (
                        query.get(
                            "session_id"
                        )
                        or [""]
                    )[0]
                ).strip()

                if not session:
                    raise session_runtime_error(
                        "session_id is required"
                    )

                if path == (
                    "/api/session/recover"
                ):
                    _send_json(
                        self,
                        runtime.recover(
                            session
                        ),
                    )
                    return

                after_sequence = _query_int(
                    query,
                    "after",
                    0,
                )

                wait_seconds = _query_float(
                    query,
                    "wait",
                    0.0,
                )

                limit = _query_int(
                    query,
                    "limit",
                    256,
                )

                if not 1 <= limit <= 4096:
                    raise session_runtime_error(
                        "limit must be between "
                        "1 and 4096"
                    )

                _send_json(
                    self,
                    runtime.events(
                        session=session,
                        after_sequence=
                            after_sequence,
                        wait_seconds=
                            wait_seconds,
                        limit=limit,
                    ),
                )

            except Exception:
                _send_json(
                    self,
                    {
                        "ok":
                            False,
                        "error":
                            (
                                "Palaver could not "
                                "resolve the session."
                            ),
                        "error_code":
                            "session_request_failed",
                        "authority_effect":
                            "none",
                    },
                    400,
                )

        def do_POST(
            self,
        ) -> None:
            parsed = urlparse(
                self.path
            )

            path = parsed.path

            if path not in {
                "/api/session/open",
                "/api/session/cancel",
            }:
                super().do_POST()
                return

            try:
                data = _body_json(
                    self
                )

                if path == (
                    "/api/session/open"
                ):
                    _send_json(
                        self,
                        runtime.open(
                            data.get(
                                "session_id"
                            )
                        ),
                    )
                    return

                session = str(
                    data.get(
                        "session_id",
                        "",
                    )
                    or ""
                ).strip()

                request = str(
                    data.get(
                        "request_id",
                        "",
                    )
                    or ""
                ).strip()

                if (
                    not session
                    or not request
                ):
                    raise session_runtime_error(
                        "session_id and request_id "
                        "are required"
                    )

                _send_json(
                    self,
                    runtime.cancel(
                        session=session,
                        request=request,
                        reason=data.get(
                            "reason"
                        ),
                    ),
                )

            except Exception:
                _send_json(
                    self,
                    {
                        "ok":
                            False,
                        "error":
                            (
                                "Palaver could not "
                                "complete the session request."
                            ),
                        "error_code":
                            "session_request_failed",
                        "authority_effect":
                            "none",
                    },
                    400,
                )

    SessionCanonicalHandler.__name__ = (
        "PalaverSessionCanonicalHandler"
    )

    return SessionCanonicalHandler


def install(
    server_module: Any,
    *,
    runtime: session_runtime | None = None,
) -> session_runtime:
    if getattr(
        server_module,
        "_palaver_session_runtime_installed",
        False,
    ):
        existing = getattr(
            server_module,
            "_palaver_session_runtime",
            None,
        )

        if isinstance(
            existing,
            session_runtime,
        ):
            return existing

        raise session_runtime_error(
            "Palaver session runtime installation "
            "state is invalid"
        )

    original = getattr(
        server_module,
        "make_canonical_handler",
        None,
    )

    if not callable(
        original
    ):
        raise session_runtime_error(
            "canonical handler factory unavailable"
        )

    active_runtime = (
        runtime
        if runtime is not None
        else session_runtime()
    )

    def session_factory(
        legacy: Any,
    ):
        return make_session_handler(
            original,
            legacy,
            runtime=
                active_runtime,
        )

    session_factory.__name__ = (
        "make_session_canonical_handler"
    )

    server_module.make_canonical_handler = (
        session_factory
    )

    server_module._palaver_session_runtime = (
        active_runtime
    )

    server_module._palaver_session_runtime_installed = (
        True
    )

    return active_runtime


def status(
    runtime: session_runtime,
) -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "database":
            str(
                runtime.store.path
            ),
        "persistent":
            True,
        "canonical_authority":
            False,
        "routes": {
            "get": [
                "/api/session/recover",
                "/api/session/events",
            ],
            "post": [
                "/api/session/open",
                "/api/session/cancel",
            ],
        },
        "streaming_transport":
            "bounded_long_poll",
        "websocket_installed":
            False,
        "provider_streaming_owned_by":
            "opus",
        "conversation_owned_by":
            "palaver",
        "authority_effect":
            "none",
    }
