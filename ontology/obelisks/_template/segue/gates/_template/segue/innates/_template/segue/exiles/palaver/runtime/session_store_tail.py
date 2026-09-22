from __future__ import annotations

import json
from typing import Any

try:
    from .conversation_transport import (
        project_event,
    )
except ImportError:
    from conversation_transport import (
        project_event,
    )


schema = (
    "savant://runtime/palaver/"
    "session-store-tail/1.0.0"
)

owner = "exile:palaver"


class session_store_tail_error(
    RuntimeError
):
    pass


def install(
    store_class: type,
) -> dict[str, Any]:
    if getattr(
        store_class,
        "_palaver_tail_loader_installed",
        False,
    ):
        return {
            "schema": schema,
            "owner": owner,
            "installed": True,
            "already_installed": True,
            "authority_effect": "none",
        }

    original = getattr(
        store_class,
        "load_events",
        None,
    )

    if not callable(
        original
    ):
        raise session_store_tail_error(
            "session store load_events unavailable"
        )

    def load_events(
        self: Any,
        session_id: str,
        *,
        limit: int | None = None,
        tail: bool = False,
    ):
        if not tail:
            return original(
                self,
                session_id,
                limit=limit,
            )

        identifier = str(
            session_id
            or ""
        ).strip()

        if not identifier:
            raise session_store_tail_error(
                "session id is required"
            )

        effective_limit = (
            int(limit)
            if limit is not None
            else 1024
        )

        if effective_limit < 1:
            return []

        connection_factory = getattr(
            self,
            "_connect",
            None,
        )

        if not callable(
            connection_factory
        ):
            raise session_store_tail_error(
                "session store connection "
                "factory unavailable"
            )

        connection = (
            connection_factory()
        )

        try:
            rows = connection.execute(
                """
                SELECT
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
                FROM events
                WHERE session_id = ?
                ORDER BY sequence DESC
                LIMIT ?
                """,
                (
                    identifier,
                    effective_limit,
                ),
            ).fetchall()

        finally:
            connection.close()

        rows = list(
            reversed(
                rows
            )
        )

        events = []

        for row in rows:
            (
                stored_session,
                sequence,
                request,
                event_type,
                payload_json,
                observed_at,
                event_id,
                semantic_digest,
                terminal,
                authority_effect,
            ) = row

            payload = json.loads(
                payload_json
            )

            event = project_event(
                session=
                    stored_session,
                request=
                    request,
                sequence=
                    int(
                        sequence
                    ),
                kind=
                    event_type,
                payload=
                    payload,
                observed_at=
                    observed_at,
            )

            if (
                getattr(
                    event,
                    "event_id",
                    None,
                )
                != event_id
            ):
                raise session_store_tail_error(
                    "stored event id failed "
                    "deterministic replay"
                )

            if (
                getattr(
                    event,
                    "semantic_digest",
                    None,
                )
                != semantic_digest
            ):
                raise session_store_tail_error(
                    "stored semantic digest failed "
                    "deterministic replay"
                )

            if (
                bool(
                    getattr(
                        event,
                        "terminal",
                        False,
                    )
                )
                != bool(
                    terminal
                )
            ):
                raise session_store_tail_error(
                    "stored terminal state failed "
                    "deterministic replay"
                )

            if (
                getattr(
                    event,
                    "authority_effect",
                    "none",
                )
                != (
                    authority_effect
                    or "none"
                )
            ):
                raise session_store_tail_error(
                    "stored authority effect failed "
                    "deterministic replay"
                )

            events.append(
                event
            )

        return events

    store_class.load_events = (
        load_events
    )

    store_class._palaver_tail_loader_installed = (
        True
    )

    return {
        "schema": schema,
        "owner": owner,
        "installed": True,
        "already_installed": False,
        "tail_loading":
            True,
        "latest_first_query":
            True,
        "ascending_replay_projection":
            True,
        "deterministic_replay_validation":
            True,
        "database_is_authority":
            False,
        "authority_effect":
            "none",
    }
