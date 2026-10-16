#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import traceback

from runtime.straub.datrix import StraubDatrix


DATRIX = Path(
    "/root/savant-runtime/runtime/niche/tasks.datrix"
)


def describe(
    path: Path,
) -> None:
    print(
        "path:",
        path,
    )

    print(
        "exists:",
        path.exists(),
    )

    if not path.exists():
        return

    print(
        "is_file:",
        path.is_file(),
    )

    print(
        "size:",
        path.stat().st_size,
    )

    if not path.is_file():
        return

    with path.open(
        "rb"
    ) as handle:
        prefix = handle.read(
            64
        )

    print(
        "prefix_hex:",
        prefix.hex(),
    )

    print(
        "sqlite_header:",
        prefix.startswith(
            b"SQLite format 3\x00"
        ),
    )


def main() -> None:
    backup = Path(
        str(
            DATRIX
        )
        + ".bak"
    )

    lock = Path(
        str(
            DATRIX
        )
        + ".lock"
    )

    print(
        "before_open:"
    )

    describe(
        DATRIX
    )

    describe(
        backup
    )

    describe(
        lock
    )

    print(
        "opening_straub_datrix:"
    )

    try:
        datrix = StraubDatrix.open(
            DATRIX
        )

        print(
            "open_result: PASS"
        )

        print(
            "datrix_type:",
            type(
                datrix
            ).__name__,
        )

    except Exception as exc:
        print(
            "open_result: FAIL"
        )

        print(
            "exception_type:",
            type(
                exc
            ).__name__,
        )

        print(
            "exception:",
            str(
                exc
            ),
        )

        traceback.print_exc()

    print(
        "after_open:"
    )

    describe(
        DATRIX
    )

    describe(
        backup
    )

    describe(
        lock
    )


if __name__ == "__main__":
    main()
