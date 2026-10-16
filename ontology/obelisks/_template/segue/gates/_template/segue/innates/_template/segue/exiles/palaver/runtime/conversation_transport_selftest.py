from __future__ import annotations

import threading
import time

from .conversation_transport import (
    conversation_event_buffer,
    conversation_transport_registry,
    cursor_expired,
    decode_cursor,
    encode_cursor,
    project_event,
)


def main() -> int:
    first = project_event(
        session="session-1",
        request="request-1",
        sequence=1,
        kind="request.accepted",
        payload={
            "message":
                "hello",
        },
        observed_at=1.0,
    )

    second = project_event(
        session="session-1",
        request="request-1",
        sequence=1,
        kind="request.accepted",
        payload={
            "message":
                "hello",
        },
        observed_at=999.0,
    )

    assert (
        first.semantic_digest
        == second.semantic_digest
    )

    assert (
        first.event_id
        == second.event_id
    )

    cursor = encode_cursor(
        first
    )

    decoded = decode_cursor(
        cursor
    )

    assert (
        decoded.session_id
        == "session-1"
    )

    assert (
        decoded.sequence
        == 1
    )

    buffer = conversation_event_buffer(
        session="session-1",
        maximum_events=16,
    )

    accepted = buffer.publish(
        request="request-1",
        kind="request.accepted",
        payload={
            "message":
                "hello",
        },
        dedupe_key="accepted",
    )

    duplicate = buffer.publish(
        request="request-1",
        kind="request.accepted",
        payload={
            "message":
                "hello",
        },
        dedupe_key="accepted",
    )

    assert (
        duplicate.event_id
        == accepted.event_id
    )

    assert (
        buffer.latest_sequence
        == 1
    )

    delta = buffer.publish(
        request="request-1",
        kind="response.delta",
        payload={
            "text":
                "hel",
        },
    )

    completed = buffer.publish(
        request="request-1",
        kind="response.completed",
        payload={
            "text":
                "hello",
        },
    )

    assert delta.sequence == 2
    assert completed.sequence == 3
    assert completed.terminal is True

    resumed = buffer.resume(
        encode_cursor(
            accepted
        )
    )

    assert [
        event.sequence
        for event in resumed
    ] == [
        2,
        3,
    ]

    token = buffer.cancellation(
        "request-2"
    )

    assert token.cancelled() is False

    changed = buffer.cancel(
        "request-2",
        "user_requested",
    )

    assert changed is True
    assert token.cancelled() is True
    assert token.reason() == "user_requested"

    repeated = buffer.cancel(
        "request-2",
        "again",
    )

    assert repeated is False

    waiter_result = []

    def waiter() -> None:
        result = buffer.wait_after(
            buffer.latest_sequence,
            timeout=2.0,
        )

        waiter_result.extend(
            result
        )

    thread = threading.Thread(
        target=waiter,
        daemon=True,
    )

    thread.start()

    time.sleep(
        0.05
    )

    streamed = buffer.publish(
        request="request-3",
        kind="response.delta",
        payload={
            "text":
                "stream",
        },
    )

    thread.join(
        timeout=2.0
    )

    assert (
        thread.is_alive()
        is False
    )

    assert (
        waiter_result
    )

    assert (
        waiter_result[0].event_id
        == streamed.event_id
    )

    small = conversation_event_buffer(
        session="session-small",
        maximum_events=16,
    )

    oldest = None

    for index in range(
        1,
        18,
    ):
        event = small.publish(
            request="request-small",
            kind="execution.state",
            payload={
                "index":
                    index,
            },
        )

        if index == 1:
            oldest = event

    assert oldest is not None

    expired = False

    try:
        small.resume(
            encode_cursor(
                oldest
            )
        )
    except cursor_expired:
        expired = True

    assert expired is True

    projection = (
        buffer.compact_projection()
    )

    assert (
        projection[
            "resume_supported"
        ]
        is True
    )

    assert (
        projection[
            "persistent_session_store"
        ]
        if "persistent_session_store"
        in projection
        else projection[
            "boundaries"
        ][
            "persistent_session_store"
        ]
    ) is False

    assert (
        projection[
            "boundaries"
        ][
            "provider_stream_execution"
        ]
        is False
    )

    registry = (
        conversation_transport_registry(
            maximum_sessions=2,
            maximum_events_per_session=16,
        )
    )

    one = registry.session(
        "one"
    )

    two = registry.session(
        "two"
    )

    assert (
        registry.session(
            "one"
        )
        is one
    )

    registry.session(
        "three"
    )

    registry_projection = (
        registry.projection()
    )

    assert (
        registry_projection[
            "session_count"
        ]
        == 2
    )

    assert (
        registry_projection[
            "persistent_authority"
        ]
        is False
    )

    print(
        "palaver conversation transport: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
