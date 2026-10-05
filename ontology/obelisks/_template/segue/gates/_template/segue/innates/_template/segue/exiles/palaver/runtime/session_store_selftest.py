from __future__ import annotations

import tempfile
from pathlib import Path

from .conversation_transport import (
    conversation_event_buffer,
)
from .session_store import (
    session_store,
    session_store_error,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        database = (
            Path(
                directory
            )
            / "sessions.sqlite3"
        )

        store = session_store(
            database
        )

        session = (
            "session-persistence-test"
        )

        store.ensure_session(
            session
        )

        updated = store.update_session(
            session,
            state="active",
            task_binding={
                "task_id":
                    "task-1",
                "owner":
                    "niche",
            },
            context_sources=[
                {
                    "kind":
                        "source_reference",
                    "uri":
                        "savant://test/source",
                }
            ],
            workspace_state={
                "preset":
                    "conversation",
            },
            usage_summary={
                "input_tokens":
                    10,
                "output_tokens":
                    20,
            },
            replay_metadata={
                "replayable":
                    True,
            },
            replace_task_binding=True,
        )

        assert (
            updated[
                "task_binding"
            ][
                "owner"
            ]
            == "niche"
        )

        buffer = (
            conversation_event_buffer(
                session=session,
                maximum_events=16,
            )
        )

        first = buffer.publish(
            request="request-1",
            kind="request.accepted",
            payload={
                "message":
                    "hello",
            },
        )

        second = buffer.publish(
            request="request-1",
            kind="response.delta",
            payload={
                "text":
                    "hel",
            },
        )

        third = buffer.publish(
            request="request-1",
            kind="response.completed",
            payload={
                "text":
                    "hello",
            },
        )

        assert (
            store.persist_events(
                buffer.snapshot()
            )
            == 3
        )

        assert (
            store.persist_event(
                first
            )
            is False
        )

        loaded = store.load_events(
            session
        )

        assert [
            event.sequence
            for event in loaded
        ] == [
            1,
            2,
            3,
        ]

        assert (
            loaded[1].event_id
            == second.event_id
        )

        assert (
            loaded[2].semantic_digest
            == third.semantic_digest
        )

        restored = (
            store.restore_buffer(
                session,
                maximum_events=16,
            )
        )

        assert (
            restored.latest_sequence
            == 3
        )

        assert (
            [
                event.semantic_digest
                for event
                in restored.snapshot()
            ]
            == [
                event.semantic_digest
                for event
                in buffer.snapshot()
            ]
        )

        assert (
            store.record_receipt(
                receipt_id=
                    "receipt-1",
                session=session,
                request="request-1",
                receipt_type=
                    "tool.execution",
                receipt_owner="coda",
                payload={
                    "ok":
                        True,
                },
            )
            is True
        )

        assert (
            store.record_receipt(
                receipt_id=
                    "receipt-1",
                session=session,
                request="request-1",
                receipt_type=
                    "tool.execution",
                receipt_owner="coda",
                payload={
                    "ok":
                        True,
                },
            )
            is False
        )

        conflict = False

        try:
            store.record_receipt(
                receipt_id=
                    "receipt-1",
                session=session,
                request="request-1",
                receipt_type=
                    "tool.execution",
                receipt_owner="coda",
                payload={
                    "ok":
                        False,
                },
            )
        except session_store_error:
            conflict = True

        assert conflict is True

        projection = (
            store.recovery_projection(
                session
            )
        )

        assert projection is not None

        assert (
            projection[
                "event_count"
            ]
            == 3
        )

        assert (
            projection[
                "latest_sequence"
            ]
            == 3
        )

        assert (
            projection[
                "receipt_count"
            ]
            == 1
        )

        assert (
            projection[
                "database_is_authority"
            ]
            is False
        )

        assert (
            projection[
                "repository_content_duplicated"
            ]
            is False
        )

        assert (
            projection[
                "boundaries"
            ][
                "conversation_owner"
            ]
            == "palaver"
        )

        assert (
            projection[
                "boundaries"
            ][
                "mutation_owner"
            ]
            == "coda"
        )

        store.close()

        reopened = session_store(
            database
        )

        replayed = reopened.load_events(
            session
        )

        assert (
            len(
                replayed
            )
            == 3
        )

        assert (
            replayed[-1]
            .semantic_digest
            == third.semantic_digest
        )

        reopened.close()

    print(
        "palaver session store: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
