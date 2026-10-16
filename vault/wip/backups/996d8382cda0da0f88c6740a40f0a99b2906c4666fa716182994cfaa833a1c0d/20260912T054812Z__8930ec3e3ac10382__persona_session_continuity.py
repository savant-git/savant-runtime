#!/usr/bin/env python3

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any


schema = (
    "savant://runtime/palaver/"
    "persona-session-continuity/1.0.0"
)

owner = "exile:palaver"
persona_owner = "envoy"

receipt_type = (
    "envoy.persona.composition"
)


class persona_session_continuity_error(
    RuntimeError
):
    pass


def _mapping(
    value: Any,
) -> dict[str, Any] | None:
    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key):
                item
            for key, item
            in value.items()
        }

    return None


def _call_with_known_arguments(
    function: Any,
    values: Mapping[
        str,
        Any,
    ],
) -> Any:
    signature = inspect.signature(
        function
    )

    positional: list[Any] = []
    keyword: dict[str, Any] = {}

    aliases = {
        "session":
            "session_id",
        "session_id":
            "session_id",
        "request":
            "request_id",
        "request_id":
            "request_id",
        "type":
            "receipt_type",
        "kind":
            "receipt_type",
        "receipt_type":
            "receipt_type",
        "owner":
            "owner",
        "payload":
            "payload",
        "data":
            "payload",
    }

    for parameter in (
        signature.parameters.values()
    ):
        if parameter.name == "self":
            continue

        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        canonical = aliases.get(
            parameter.name
        )

        if canonical is None:
            if (
                parameter.default
                is inspect.Parameter.empty
            ):
                raise (
                    persona_session_continuity_error(
                        "unsupported store method "
                        f"parameter: {parameter.name}"
                    )
                )

            continue

        if canonical not in values:
            if (
                parameter.default
                is inspect.Parameter.empty
            ):
                raise (
                    persona_session_continuity_error(
                        "missing store method "
                        f"argument: {canonical}"
                    )
                )

            continue

        value = values[
            canonical
        ]

        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }:
            positional.append(
                value
            )
        else:
            keyword[
                parameter.name
            ] = value

    return function(
        *positional,
        **keyword,
    )


def _payload_from_receipt(
    receipt: Any,
) -> dict[str, Any] | None:
    row = _mapping(
        receipt
    )

    if row is None:
        return None

    kind = str(
        row.get(
            "receipt_type"
        )
        or row.get(
            "type"
        )
        or ""
    ).strip()

    if (
        kind
        and kind != receipt_type
    ):
        return None

    payload = row.get(
        "payload"
    )

    if isinstance(
        payload,
        Mapping,
    ):
        return dict(
            payload
        )

    return None


def previous_traits(
    store: Any,
    session_id: str,
) -> tuple[str, ...]:
    reader = getattr(
        store,
        "receipts",
        None,
    )

    if not callable(
        reader
    ):
        return ()

    try:
        rows = (
            _call_with_known_arguments(
                reader,
                {
                    "session_id":
                        session_id,
                },
            )
        )
    except Exception:
        return ()

    if not isinstance(
        rows,
        (
            list,
            tuple,
        ),
    ):
        return ()

    for row in reversed(
        rows
    ):
        payload = (
            _payload_from_receipt(
                row
            )
        )

        if payload is None:
            continue

        active = payload.get(
            "active_traits"
        )

        if not isinstance(
            active,
            (
                list,
                tuple,
                set,
            ),
        ):
            continue

        normalized = {
            str(item)
            .strip()
            .lower()
            for item in active
            if str(
                item
                or ""
            ).strip()
        }

        return tuple(
            sorted(
                normalized
            )
        )

    return ()


def record(
    store: Any,
    *,
    session_id: str,
    request_id: str,
    receipt: Mapping[
        str,
        Any,
    ],
) -> bool:
    writer = getattr(
        store,
        "record_receipt",
        None,
    )

    if not callable(
        writer
    ):
        return False

    payload = dict(
        receipt
    )

    if payload.get(
        "owner"
    ) != persona_owner:
        raise (
            persona_session_continuity_error(
                "persona receipt must "
                "remain Envoy-owned"
            )
        )

    _call_with_known_arguments(
        writer,
        {
            "session_id":
                session_id,
            "request_id":
                request_id,
            "receipt_type":
                receipt_type,
            "owner":
                persona_owner,
            "payload":
                payload,
        },
    )

    return True


def projection(
    store: Any,
    session_id: str,
) -> dict[str, Any]:
    traits = previous_traits(
        store,
        session_id,
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_owner":
            persona_owner,
        "session_id":
            session_id,
        "previous_traits":
            list(
                traits
            ),
        "persistent_receipt":
            callable(
                getattr(
                    store,
                    "record_receipt",
                    None,
                )
            ),
        "database_is_authority":
            False,
        "authority_effect":
            "none",
    }
