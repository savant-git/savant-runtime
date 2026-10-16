from __future__ import annotations

import tempfile
from pathlib import Path

from .session_runtime import (
    session_runtime,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        database = (
            Path(
                directory
            )
            / "sessions.sqlite3"
        )

        runtime = session_runtime(
            database=database,
            maximum_sessions=8,
            maximum_events_per_session=16,
        )

        opened = runtime.open(
            "session-1"
        )

        assert opened["ok"] is True
        assert opened["created"] is True

        accepted = runtime.publish(
            session="session-1",
            request="request-1",
            kind="request.accepted",
            payload={
                "message":
                    "hello",
            },
            dedupe_key="accepted",
        )

        runtime.publish(
            session="session-1",
            request="request-1",
            kind="response.delta",
            payload={
                "text":
                    "hel",
            },
        )

        runtime.publish(
            session="session-1",
            request="request-1",
            kind="response.completed",
            payload={
                "text":
                    "hello",
            },
        )

        events = runtime.events(
            session="session-1",
            after_sequence=1,
        )

        assert [
            event["sequence"]
            for event in events["events"]
        ] == [
            2,
            3,
        ]

        assert (
            accepted[
                "sequence"
            ]
            == 1
        )

        cancellation = runtime.cancel(
            session="session-1",
            request="request-2",
            reason="user_requested",
        )

        assert (
            cancellation[
                "changed"
            ]
            is True
        )

        projection = runtime.recover(
            "session-1"
        )

        assert (
            projection[
                "transport"
            ][
                "latest_sequence"
            ]
            == 4
        )

        assert (
            projection[
                "recovery"
            ][
                "database_is_authority"
            ]
            is False
        )

        runtime.close()

        reopened = session_runtime(
            database=database,
            maximum_sessions=8,
            maximum_events_per_session=16,
        )

        recovered = reopened.recover(
            "session-1"
        )

        assert (
            recovered[
                "transport"
            ][
                "latest_sequence"
            ]
            == 4
        )

        assert (
            len(
                recovered[
                    "events"
                ]
            )
            == 4
        )

        reopened.close()

    print(
        "palaver session runtime: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
