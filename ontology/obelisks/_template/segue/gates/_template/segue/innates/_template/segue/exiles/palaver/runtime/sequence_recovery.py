from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "sequence-recovery/1.0.0"
)

owner = "exile:palaver"


class sequence_recovery_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class recovery_window:
    session_id: str
    total_events: int
    earliest_sequence: int
    latest_sequence: int
    retained_from_sequence: int
    retained_event_count: int

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "session_id":
                self.session_id,
            "total_events":
                self.total_events,
            "earliest_sequence":
                self.earliest_sequence,
            "latest_sequence":
                self.latest_sequence,
            "retained_from_sequence":
                self.retained_from_sequence,
            "retained_event_count":
                self.retained_event_count,
            "authority_effect":
                "none",
        }


def inspect_window(
    database: str | Path,
    session: str,
    *,
    capacity: int,
) -> recovery_window:
    database_path = Path(
        database
    )

    identifier = str(
        session
        or ""
    ).strip()

    if not identifier:
        raise sequence_recovery_error(
            "session id is required"
        )

    if capacity < 1:
        raise sequence_recovery_error(
            "capacity must be positive"
        )

    connection = sqlite3.connect(
        str(
            database_path
        ),
        timeout=30.0,
    )

    try:
        row = connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(MIN(sequence), 0),
                COALESCE(MAX(sequence), 0)
            FROM events
            WHERE session_id = ?
            """,
            (
                identifier,
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        total = 0
        earliest = 0
        latest = 0
    else:
        total = int(
            row[0]
            or 0
        )

        earliest = int(
            row[1]
            or 0
        )

        latest = int(
            row[2]
            or 0
        )

    retained_count = min(
        total,
        capacity,
    )

    retained_from = (
        max(
            earliest,
            latest
            - retained_count
            + 1,
        )
        if retained_count
        else 0
    )

    return recovery_window(
        session_id=
            identifier,
        total_events=
            total,
        earliest_sequence=
            earliest,
        latest_sequence=
            latest,
        retained_from_sequence=
            retained_from,
        retained_event_count=
            retained_count,
    )


def seed_sequence(
    buffer: Any,
    target_sequence: int,
    *,
    session: str,
) -> None:
    current = int(
        getattr(
            buffer,
            "latest_sequence",
            0,
        )
        or 0
    )

    if current > target_sequence:
        raise sequence_recovery_error(
            "buffer sequence exceeds "
            "recovery target"
        )

    while current < target_sequence:
        next_sequence = (
            current + 1
        )

        event = buffer.publish(
            request=
                (
                    "palreq_recovery_"
                    f"{next_sequence}"
                ),
            kind=
                "session.state",
            payload={
                "recovery_seed":
                    True,
                "authority_effect":
                    "none",
            },
            dedupe_key=None,
        )

        observed = int(
            getattr(
                event,
                "sequence",
                0,
            )
            or 0
        )

        if (
            observed
            != next_sequence
        ):
            raise sequence_recovery_error(
                "conversation buffer sequence "
                "is not monotonic"
            )

        current = observed


def restore_bounded_history(
    *,
    store: Any,
    buffer: Any,
    session: str,
    capacity: int,
) -> dict[str, Any]:
    database = (
        getattr(
            store,
            "path",
            None,
        )
        or getattr(
            store,
            "database",
            None,
        )
        or getattr(
            store,
            "database_path",
            None,
        )
    )

    if database is None:
        raise sequence_recovery_error(
            "session store database path "
            "is unavailable"
        )

    window = inspect_window(
        database,
        session,
        capacity=capacity,
    )

    if (
        window.total_events
        == 0
    ):
        return window.projection()

    retained = store.load_events(
        session,
        limit=
            window.retained_event_count,
        tail=True,
    )

    if not retained:
        raise sequence_recovery_error(
            "persistent event history "
            "could not be restored"
        )

    first_sequence = int(
        getattr(
            retained[0],
            "sequence",
            0,
        )
        or 0
    )

    expected_first = (
        window.retained_from_sequence
    )

    if (
        first_sequence
        != expected_first
    ):
        raise sequence_recovery_error(
            "persistent tail does not begin "
            "at expected sequence"
        )

    seed_sequence(
        buffer,
        expected_first - 1,
        session=session,
    )

    for event in retained:
        published = buffer.publish(
            request=
                getattr(
                    event,
                    "request_id",
                    None,
                ),
            kind=
                getattr(
                    event,
                    "event_type",
                    None,
                ),
            payload=
                getattr(
                    event,
                    "payload",
                    {},
                ),
            observed_at=
                getattr(
                    event,
                    "observed_at",
                    None,
                ),
            dedupe_key=None,
        )

        expected = int(
            getattr(
                event,
                "sequence",
                0,
            )
            or 0
        )

        actual = int(
            getattr(
                published,
                "sequence",
                0,
            )
            or 0
        )

        if actual != expected:
            raise sequence_recovery_error(
                "recovered event sequence "
                "diverged"
            )

        expected_digest = getattr(
            event,
            "semantic_digest",
            None,
        )

        actual_digest = getattr(
            published,
            "semantic_digest",
            None,
        )

        if (
            expected_digest
            and actual_digest
            and expected_digest
            != actual_digest
        ):
            raise sequence_recovery_error(
                "recovered event digest "
                "diverged"
            )

    latest = int(
        getattr(
            buffer,
            "latest_sequence",
            0,
        )
        or 0
    )

    if (
        latest
        != window.latest_sequence
    ):
        raise sequence_recovery_error(
            "buffer did not recover "
            "persistent latest sequence"
        )

    return window.projection()
