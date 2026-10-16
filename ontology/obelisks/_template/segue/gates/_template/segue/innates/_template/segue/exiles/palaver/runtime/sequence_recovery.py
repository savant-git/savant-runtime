from __future__ import annotations

from dataclasses import dataclass
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
            "bounded_retention":
                True,
            "persistent_sequence_continuity":
                True,
            "restart_sequence_reset":
                False,
            "database_is_authority":
                False,
            "authority_effect":
                "none",
        }


def inspect_window(
    store: Any,
    session: str,
    capacity: int,
) -> recovery_window:
    identifier = str(
        session
        or ""
    ).strip()

    if not identifier:
        raise sequence_recovery_error(
            "session id is required"
        )

    effective_capacity = int(
        capacity
    )

    if effective_capacity < 1:
        raise sequence_recovery_error(
            "capacity must be positive"
        )

    inspector = getattr(
        store,
        "event_window",
        None,
    )

    if not callable(
        inspector
    ):
        raise sequence_recovery_error(
            "session store event window unavailable"
        )

    value = inspector(
        identifier,
        capacity=effective_capacity,
    )

    return recovery_window(
        session_id=str(
            value["session_id"]
        ),
        total_events=int(
            value["total_events"]
        ),
        earliest_sequence=int(
            value["earliest_sequence"]
        ),
        latest_sequence=int(
            value["latest_sequence"]
        ),
        retained_from_sequence=int(
            value["retained_from_sequence"]
        ),
        retained_event_count=int(
            value["retained_event_count"]
        ),
    )


def seed_sequence(
    buffer: Any,
    target_sequence: int,
    session: str,
) -> None:
    target = int(
        target_sequence
    )

    if target <= 0:
        return

    while (
        int(
            getattr(
                buffer,
                "latest_sequence",
                0,
            )
            or 0
        )
        < target
    ):
        before = int(
            getattr(
                buffer,
                "latest_sequence",
                0,
            )
            or 0
        )

        published = buffer.publish(
            request=(
                "palaver-recovery-seed:"
                + str(session)
                + ":"
                + str(before + 1)
            ),
            kind="session.state",
            payload={
                "recovery_seed": True,
                "authority_effect": "none",
            },
        )

        after = int(
            getattr(
                published,
                "sequence",
                0,
            )
            or 0
        )

        if after != before + 1:
            raise sequence_recovery_error(
                "recovery seed sequence diverged"
            )


def restore_bounded_history(
    *,
    store: Any,
    buffer: Any,
    session: str,
    capacity: int,
) -> dict[str, Any]:
    identifier = str(
        session
        or ""
    ).strip()

    if not identifier:
        raise sequence_recovery_error(
            "session id is required"
        )

    window = inspect_window(
        store,
        identifier,
        capacity,
    )

    if window.total_events <= 0:
        return window.projection()

    persisted = store.load_events(
        identifier,
        limit=
            window.retained_event_count,
        tail=True,
    )

    if not persisted:
        raise sequence_recovery_error(
            "persistent recovery window is empty"
        )

    actual_first = int(
        getattr(
            persisted[0],
            "sequence",
            0,
        )
        or 0
    )

    if (
        actual_first
        != window.retained_from_sequence
    ):
        raise sequence_recovery_error(
            "persistent recovery window "
            "start diverged"
        )

    seed_sequence(
        buffer,
        window.retained_from_sequence - 1,
        identifier,
    )

    for event in persisted:
        published = buffer.publish(
            request=event.request_id,
            kind=event.type,
            payload=event.payload,
        )

        if (
            published.sequence
            != event.sequence
        ):
            raise sequence_recovery_error(
                "persistent recovery sequence "
                "diverged"
            )

        if (
            published.semantic_digest
            != event.semantic_digest
        ):
            raise sequence_recovery_error(
                "persistent recovery semantic "
                "digest diverged"
            )

    if (
        int(
            getattr(
                buffer,
                "latest_sequence",
                0,
            )
            or 0
        )
        != window.latest_sequence
    ):
        raise sequence_recovery_error(
            "persistent recovery latest "
            "sequence diverged"
        )

    return window.projection()
