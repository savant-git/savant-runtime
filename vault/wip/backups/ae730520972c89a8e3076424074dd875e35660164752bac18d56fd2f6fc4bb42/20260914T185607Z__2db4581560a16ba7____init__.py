#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.history.v1"
owner = "savant"
authority_effect = "none"


def build_event(
    *,
    sequence: int,
    action: str,
    record: Mapping[str, Any],
    previous_event_digest: str | None,
) -> dict[str, Any]:
    if sequence < 1:
        raise StraubValidationError(
            "history sequence must be positive"
        )

    action_id = str(
        action or ""
    ).strip().lower()

    if not action_id:
        raise StraubValidationError(
            "history action is required"
        )

    if not isinstance(
        record,
        Mapping,
    ):
        raise StraubValidationError(
            "history record must be an object"
        )

    record_id = str(
        record.get("id")
        or ""
    ).strip()

    record_digest = str(
        record.get("digest")
        or ""
    ).strip()

    if not record_id:
        raise StraubValidationError(
            "history record id is required"
        )

    if not record_digest:
        raise StraubValidationError(
            "history record digest is required"
        )

    event = {
        "schema":
            "savant.straub.history-event.v1",
        "sequence":
            sequence,
        "action":
            action_id,
        "record_id":
            record_id,
        "record_kind":
            str(
                record.get("kind")
                or ""
            ),
        "record_digest":
            record_digest,
        "previous_event_digest":
            previous_event_digest,
        "record":
            deepcopy(
                dict(record)
            ),
        "authority_effect":
            "none",
    }

    unsigned = deepcopy(
        event
    )

    event["event_digest"] = (
        content_digest(
            unsigned
        )
    )

    event["event_id"] = (
        "event:straub:"
        f"{sequence:020d}:"
        f"{event['event_digest'][:16]}"
    )

    return event


def validate_history(
    events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    previous: str | None = None

    normalized: list[
        dict[str, Any]
    ] = []

    for expected_sequence, raw in enumerate(
        events,
        start=1,
    ):
        if not isinstance(
            raw,
            Mapping,
        ):
            raise StraubValidationError(
                "history event must be an object"
            )

        event = deepcopy(
            dict(raw)
        )

        if (
            event.get("schema")
            != "savant.straub.history-event.v1"
        ):
            raise StraubValidationError(
                "unsupported history event schema"
            )

        if (
            event.get("sequence")
            != expected_sequence
        ):
            raise StraubValidationError(
                "history sequence discontinuity"
            )

        if (
            event.get(
                "previous_event_digest"
            )
            != previous
        ):
            raise StraubValidationError(
                "history chain mismatch"
            )

        record = event.get(
            "record"
        )

        if not isinstance(
            record,
            Mapping,
        ):
            raise StraubValidationError(
                "history record missing"
            )

        if (
            str(
                record.get("digest")
                or ""
            )
            != str(
                event.get(
                    "record_digest"
                )
                or ""
            )
        ):
            raise StraubValidationError(
                "history record digest mismatch"
            )

        supplied_digest = str(
            event.get(
                "event_digest"
            )
            or ""
        )

        supplied_id = str(
            event.get(
                "event_id"
            )
            or ""
        )

        unsigned = deepcopy(
            event
        )

        unsigned.pop(
            "event_digest",
            None,
        )

        unsigned.pop(
            "event_id",
            None,
        )

        calculated = content_digest(
            unsigned
        )

        if (
            supplied_digest
            != calculated
        ):
            raise StraubValidationError(
                "history event digest mismatch"
            )

        expected_id = (
            "event:straub:"
            f"{expected_sequence:020d}:"
            f"{calculated[:16]}"
        )

        if (
            supplied_id
            != expected_id
        ):
            raise StraubValidationError(
                "history event id mismatch"
            )

        normalized.append(
            event
        )

        previous = calculated

    projection = {
        "schema":
            schema,
        "event_count":
            len(
                normalized
            ),
        "head_digest":
            previous,
        "events":
            normalized,
        "immutable":
            True,
        "authority_effect":
            authority_effect,
    }

    projection[
        "digest"
    ] = content_digest(
        projection
    )

    return projection
