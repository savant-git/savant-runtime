from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .conversation_transport import (
        conversation_event,
        conversation_event_buffer,
        conversation_transport_error,
        project_event,
        session_id,
    )
except ImportError:
    from conversation_transport import (
        conversation_event,
        conversation_event_buffer,
        conversation_transport_error,
        project_event,
        session_id,
    )


schema = (
    "savant://runtime/palaver/"
    "session-store/1.0.0"
)

owner = "exile:palaver"

schema_version = 1

default_database = Path(
    "/root/savant-runtime/runtime/state/"
    "palaver/sessions.sqlite3"
)


class session_store_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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


def _now() -> float:
    return time.time()


def _json_value(
    value: Any,
) -> str:
    return canonical_json(
        value
    )


def _decode_json(
    value: str | None,
    default: Any = None,
) -> Any:
    if value in (
        None,
        "",
    ):
        return default

    try:
        return json.loads(
            value
        )
    except json.JSONDecodeError as exc:
        raise session_store_error(
            "stored Palaver JSON is invalid"
        ) from exc


class session_store:
    def __init__(
        self,
        path: Path | str = default_database,
    ) -> None:
        self.path = Path(
            path
        ).resolve()

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = (
            threading.RLock()
        )

        self._connection = (
            sqlite3.connect(
                str(
                    self.path
                ),
                timeout=30.0,
                isolation_level=None,
                check_same_thread=False,
            )
        )

        self._connection.row_factory = (
            sqlite3.Row
        )

        self._configure()

        self._bootstrap()

    def _configure(
        self,
    ) -> None:
        with self._lock:
            self._connection.execute(
                "PRAGMA foreign_keys=ON"
            )

            self._connection.execute(
                "PRAGMA journal_mode=WAL"
            )

            self._connection.execute(
                "PRAGMA synchronous=FULL"
            )

            self._connection.execute(
                "PRAGMA busy_timeout=30000"
            )

            self._connection.execute(
                "PRAGMA temp_store=MEMORY"
            )

    def _bootstrap(
        self,
    ) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                state TEXT NOT NULL,
                task_binding TEXT,
                context_sources TEXT NOT NULL,
                workspace_state TEXT NOT NULL,
                usage_summary TEXT NOT NULL,
                replay_metadata TEXT NOT NULL,
                semantic_digest TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS events (
                session_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                observed_at REAL NOT NULL,
                event_id TEXT NOT NULL,
                semantic_digest TEXT NOT NULL,
                terminal INTEGER NOT NULL,
                authority_effect TEXT NOT NULL,
                PRIMARY KEY (
                    session_id,
                    sequence
                ),
                UNIQUE (
                    session_id,
                    event_id
                ),
                FOREIGN KEY (
                    session_id
                )
                REFERENCES sessions (
                    session_id
                )
                ON DELETE CASCADE
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS
            events_request_index
            ON events (
                session_id,
                request_id,
                sequence
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                request_id TEXT,
                receipt_type TEXT NOT NULL,
                owner TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                semantic_digest TEXT NOT NULL,
                authority_effect TEXT NOT NULL,
                FOREIGN KEY (
                    session_id
                )
                REFERENCES sessions (
                    session_id
                )
                ON DELETE CASCADE
            )
            """,
        )

        with self.transaction():
            for statement in statements:
                self._connection.execute(
                    statement
                )

            version = self._connection.execute(
                """
                SELECT value
                FROM metadata
                WHERE key='schema_version'
                """
            ).fetchone()

            if version is None:
                self._connection.execute(
                    """
                    INSERT INTO metadata (
                        key,
                        value
                    )
                    VALUES (
                        'schema_version',
                        ?
                    )
                    """,
                    (
                        str(
                            schema_version
                        ),
                    ),
                )

            elif int(
                version["value"]
            ) != schema_version:
                raise session_store_error(
                    "unsupported Palaver "
                    "session-store schema version"
                )

    def transaction(
        self,
    ):
        store = self

        class transaction_context:
            def __enter__(
                self,
            ) -> sqlite3.Connection:
                store._lock.acquire()

                try:
                    store._connection.execute(
                        "BEGIN IMMEDIATE"
                    )
                except Exception:
                    store._lock.release()
                    raise

                return store._connection

            def __exit__(
                self,
                exc_type,
                exc,
                traceback,
            ) -> bool:
                try:
                    if exc_type is None:
                        store._connection.execute(
                            "COMMIT"
                        )
                    else:
                        store._connection.execute(
                            "ROLLBACK"
                        )
                finally:
                    store._lock.release()

                return False

        return transaction_context()

    def close(
        self,
    ) -> None:
        with self._lock:
            self._connection.close()

    def ensure_session(
        self,
        session: Any,
        *,
        state: str = "active",
    ) -> str:
        identifier = session_id(
            session
        )

        now = _now()

        empty_context = _json_value(
            []
        )

        empty_mapping = _json_value(
            {}
        )

        semantic = digest(
            {
                "session_id":
                    identifier,
                "state":
                    state,
                "task_binding":
                    None,
                "context_sources":
                    [],
                "workspace_state":
                    {},
                "usage_summary":
                    {},
                "replay_metadata":
                    {},
            }
        )

        with self.transaction():
            self._connection.execute(
                """
                INSERT OR IGNORE INTO sessions (
                    session_id,
                    created_at,
                    updated_at,
                    state,
                    task_binding,
                    context_sources,
                    workspace_state,
                    usage_summary,
                    replay_metadata,
                    semantic_digest
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identifier,
                    now,
                    now,
                    state,
                    None,
                    empty_context,
                    empty_mapping,
                    empty_mapping,
                    empty_mapping,
                    semantic,
                ),
            )

        return identifier

    def _session_payload(
        self,
        identifier: str,
    ) -> dict[str, Any]:
        row = self._connection.execute(
            """
            SELECT *
            FROM sessions
            WHERE session_id=?
            """,
            (
                identifier,
            ),
        ).fetchone()

        if row is None:
            raise session_store_error(
                "Palaver session does not exist"
            )

        return {
            "session_id":
                row["session_id"],
            "created_at":
                row["created_at"],
            "updated_at":
                row["updated_at"],
            "state":
                row["state"],
            "task_binding":
                _decode_json(
                    row["task_binding"]
                ),
            "context_sources":
                _decode_json(
                    row["context_sources"],
                    [],
                ),
            "workspace_state":
                _decode_json(
                    row["workspace_state"],
                    {},
                ),
            "usage_summary":
                _decode_json(
                    row["usage_summary"],
                    {},
                ),
            "replay_metadata":
                _decode_json(
                    row["replay_metadata"],
                    {},
                ),
            "semantic_digest":
                row["semantic_digest"],
        }

    def load_session(
        self,
        session: Any,
    ) -> dict[str, Any] | None:
        identifier = session_id(
            session
        )

        with self._lock:
            row = self._connection.execute(
                """
                SELECT session_id
                FROM sessions
                WHERE session_id=?
                """,
                (
                    identifier,
                ),
            ).fetchone()

            if row is None:
                return None

            return self._session_payload(
                identifier
            )

    def _update_session(
        self,
        identifier: str,
        *,
        state: Any = None,
        task_binding: Any = None,
        context_sources: Any = None,
        workspace_state: Any = None,
        usage_summary: Any = None,
        replay_metadata: Any = None,
        replace_task_binding: bool = False,
    ) -> dict[str, Any]:
        current = self._session_payload(
            identifier
        )

        updated = {
            "session_id":
                identifier,
            "state":
                (
                    str(
                        state
                    ).strip()
                    if state is not None
                    else current[
                        "state"
                    ]
                ),
            "task_binding":
                (
                    task_binding
                    if replace_task_binding
                    else current[
                        "task_binding"
                    ]
                ),
            "context_sources":
                (
                    context_sources
                    if context_sources is not None
                    else current[
                        "context_sources"
                    ]
                ),
            "workspace_state":
                (
                    workspace_state
                    if workspace_state is not None
                    else current[
                        "workspace_state"
                    ]
                ),
            "usage_summary":
                (
                    usage_summary
                    if usage_summary is not None
                    else current[
                        "usage_summary"
                    ]
                ),
            "replay_metadata":
                (
                    replay_metadata
                    if replay_metadata is not None
                    else current[
                        "replay_metadata"
                    ]
                ),
        }

        if not updated["state"]:
            raise session_store_error(
                "session state cannot be empty"
            )

        semantic = digest(
            updated
        )

        now = _now()

        self._connection.execute(
            """
            UPDATE sessions
            SET
                updated_at=?,
                state=?,
                task_binding=?,
                context_sources=?,
                workspace_state=?,
                usage_summary=?,
                replay_metadata=?,
                semantic_digest=?
            WHERE session_id=?
            """,
            (
                now,
                updated[
                    "state"
                ],
                (
                    _json_value(
                        updated[
                            "task_binding"
                        ]
                    )
                    if updated[
                        "task_binding"
                    ] is not None
                    else None
                ),
                _json_value(
                    updated[
                        "context_sources"
                    ]
                ),
                _json_value(
                    updated[
                        "workspace_state"
                    ]
                ),
                _json_value(
                    updated[
                        "usage_summary"
                    ]
                ),
                _json_value(
                    updated[
                        "replay_metadata"
                    ]
                ),
                semantic,
                identifier,
            ),
        )

        return self._session_payload(
            identifier
        )

    def update_session(
        self,
        session: Any,
        *,
        state: Any = None,
        task_binding: Any = None,
        context_sources: Any = None,
        workspace_state: Any = None,
        usage_summary: Any = None,
        replay_metadata: Any = None,
        replace_task_binding: bool = False,
    ) -> dict[str, Any]:
        identifier = self.ensure_session(
            session
        )

        with self.transaction():
            return self._update_session(
                identifier,
                state=state,
                task_binding=
                    task_binding,
                context_sources=
                    context_sources,
                workspace_state=
                    workspace_state,
                usage_summary=
                    usage_summary,
                replay_metadata=
                    replay_metadata,
                replace_task_binding=
                    replace_task_binding,
            )

    def persist_event(
        self,
        event: conversation_event,
    ) -> bool:
        identifier = self.ensure_session(
            event.session_id
        )

        with self.transaction():
            existing = self._connection.execute(
                """
                SELECT semantic_digest
                FROM events
                WHERE
                    session_id=?
                    AND sequence=?
                """,
                (
                    identifier,
                    event.sequence,
                ),
            ).fetchone()

            if existing is not None:
                if (
                    existing[
                        "semantic_digest"
                    ]
                    != event.semantic_digest
                ):
                    raise session_store_error(
                        "conversation sequence conflict"
                    )

                return False

            self._connection.execute(
                """
                INSERT INTO events (
                    session_id,
                    sequence,
                    request_id,
                    event_type,
                    payload,
                    observed_at,
                    event_id,
                    semantic_digest,
                    terminal,
                    authority_effect
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.sequence,
                    event.request_id,
                    event.type,
                    _json_value(
                        event.payload
                    ),
                    event.observed_at,
                    event.event_id,
                    event.semantic_digest,
                    (
                        1
                        if event.terminal
                        else 0
                    ),
                    event.authority_effect,
                ),
            )

            self._connection.execute(
                """
                UPDATE sessions
                SET updated_at=?
                WHERE session_id=?
                """,
                (
                    _now(),
                    identifier,
                ),
            )

        return True

    def persist_events(
        self,
        events: Iterable[
            conversation_event
        ],
    ) -> int:
        count = 0

        for event in events:
            if self.persist_event(
                event
            ):
                count += 1

        return count

    def load_events(
        self,
        session: Any,
        *,
        after_sequence: int = 0,
        limit: int = 4096,
    ) -> tuple[
        conversation_event,
        ...,
    ]:
        identifier = session_id(
            session
        )

        if (
            not isinstance(
                after_sequence,
                int,
            )
            or isinstance(
                after_sequence,
                bool,
            )
            or after_sequence < 0
        ):
            raise session_store_error(
                "after_sequence must be a "
                "nonnegative integer"
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
            or not 1 <= limit <= 65536
        ):
            raise session_store_error(
                "event limit must be between "
                "1 and 65536"
            )

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT *
                FROM events
                WHERE
                    session_id=?
                    AND sequence>?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (
                    identifier,
                    after_sequence,
                    limit,
                ),
            ).fetchall()

        events: list[
            conversation_event
        ] = []

        for row in rows:
            rebuilt = project_event(
                session=
                    row["session_id"],
                request=
                    row["request_id"],
                sequence=
                    row["sequence"],
                kind=
                    row["event_type"],
                payload=
                    _decode_json(
                        row["payload"]
                    ),
                observed_at=
                    row["observed_at"],
            )

            if (
                rebuilt.event_id
                != row["event_id"]
                or rebuilt.semantic_digest
                != row[
                    "semantic_digest"
                ]
            ):
                raise session_store_error(
                    "stored conversation event "
                    "failed deterministic replay"
                )

            events.append(
                rebuilt
            )

        return tuple(
            events
        )

    def restore_buffer(
        self,
        session: Any,
        *,
        maximum_events: int = 2048,
    ) -> conversation_event_buffer:
        identifier = session_id(
            session
        )

        buffer = conversation_event_buffer(
            session=identifier,
            maximum_events=
                maximum_events,
        )

        events = self.load_events(
            identifier,
            limit=
                maximum_events,
        )

        for event in events:
            recreated = buffer.publish(
                request=
                    event.request_id,
                kind=
                    event.type,
                payload=
                    event.payload,
            )

            if (
                recreated.sequence
                != event.sequence
                or recreated.semantic_digest
                != event.semantic_digest
            ):
                raise session_store_error(
                    "conversation buffer replay "
                    "diverged from stored history"
                )

        return buffer

    def record_receipt(
        self,
        *,
        receipt_id: Any,
        session: Any,
        request: Any = None,
        receipt_type: Any,
        receipt_owner: Any,
        payload: Any,
        authority_effect: str = "none",
    ) -> bool:
        identifier = self.ensure_session(
            session
        )

        normalized_receipt = str(
            receipt_id
            or ""
        ).strip()

        normalized_type = str(
            receipt_type
            or ""
        ).strip()

        normalized_owner = str(
            receipt_owner
            or ""
        ).strip()

        if not normalized_receipt:
            raise session_store_error(
                "receipt_id is required"
            )

        if not normalized_type:
            raise session_store_error(
                "receipt_type is required"
            )

        if not normalized_owner:
            raise session_store_error(
                "receipt owner is required"
            )

        semantic = digest(
            {
                "receipt_id":
                    normalized_receipt,
                "session_id":
                    identifier,
                "request_id":
                    request,
                "receipt_type":
                    normalized_type,
                "owner":
                    normalized_owner,
                "payload":
                    payload,
                "authority_effect":
                    authority_effect,
            }
        )

        with self.transaction():
            existing = self._connection.execute(
                """
                SELECT semantic_digest
                FROM receipts
                WHERE receipt_id=?
                """,
                (
                    normalized_receipt,
                ),
            ).fetchone()

            if existing is not None:
                if (
                    existing[
                        "semantic_digest"
                    ]
                    != semantic
                ):
                    raise session_store_error(
                        "receipt identity conflict"
                    )

                return False

            self._connection.execute(
                """
                INSERT INTO receipts (
                    receipt_id,
                    session_id,
                    request_id,
                    receipt_type,
                    owner,
                    payload,
                    created_at,
                    semantic_digest,
                    authority_effect
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_receipt,
                    identifier,
                    (
                        str(
                            request
                        )
                        if request is not None
                        else None
                    ),
                    normalized_type,
                    normalized_owner,
                    _json_value(
                        payload
                    ),
                    _now(),
                    semantic,
                    authority_effect,
                ),
            )

        return True

    def receipts(
        self,
        session: Any,
    ) -> tuple[
        dict[str, Any],
        ...,
    ]:
        identifier = session_id(
            session
        )

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT *
                FROM receipts
                WHERE session_id=?
                ORDER BY created_at ASC, receipt_id ASC
                """,
                (
                    identifier,
                ),
            ).fetchall()

        return tuple(
            {
                "receipt_id":
                    row["receipt_id"],
                "session_id":
                    row["session_id"],
                "request_id":
                    row["request_id"],
                "receipt_type":
                    row["receipt_type"],
                "owner":
                    row["owner"],
                "payload":
                    _decode_json(
                        row["payload"]
                    ),
                "created_at":
                    row["created_at"],
                "semantic_digest":
                    row[
                        "semantic_digest"
                    ],
                "authority_effect":
                    row[
                        "authority_effect"
                    ],
            }
            for row in rows
        )

    def recovery_projection(
        self,
        session: Any,
    ) -> dict[str, Any] | None:
        identifier = session_id(
            session
        )

        session_record = self.load_session(
            identifier
        )

        if session_record is None:
            return None

        events = self.load_events(
            identifier
        )

        receipts = self.receipts(
            identifier
        )

        latest_sequence = (
            events[-1].sequence
            if events
            else 0
        )

        projection = {
            "schema":
                schema,
            "owner":
                owner,
            "type":
                "palaver_session_recovery",
            "session":
                session_record,
            "event_count":
                len(
                    events
                ),
            "latest_sequence":
                latest_sequence,
            "receipt_count":
                len(
                    receipts
                ),
            "deterministic_event_replay":
                True,
            "database":
                str(
                    self.path
                ),
            "database_is_authority":
                False,
            "repository_content_duplicated":
                False,
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
                "canon_owner":
                    False,
            },
        }

        projection[
            "projection_digest"
        ] = digest(
            {
                key: value
                for key, value
                in projection.items()
                if key != "database"
            }
        )

        return projection
