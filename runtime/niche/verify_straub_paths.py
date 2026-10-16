#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

from runtime.straub.resilience import (
    ResilientCapsulePersistence,
)


DATRIX = Path(
    "/root/savant-runtime/runtime/niche/tasks.datrix"
)


def main() -> None:
    persistence = ResilientCapsulePersistence(
        DATRIX
    )

    print(
        "requested_datrix:",
        DATRIX,
    )

    print(
        "persistence_type:",
        type(
            persistence
        ).__name__,
    )

    print(
        "persistence_attributes:"
    )

    for name in sorted(
        vars(
            persistence
        )
    ):
        value = getattr(
            persistence,
            name,
        )

        if isinstance(
            value,
            (
                str,
                Path,
                int,
                float,
                bool,
                type(None),
            ),
        ):
            print(
                name + ":",
                value,
            )
            continue

        nested_path = getattr(
            value,
            "path",
            None,
        )

        if nested_path is not None:
            print(
                name + ".path:",
                nested_path,
            )


if __name__ == "__main__":
    main()
