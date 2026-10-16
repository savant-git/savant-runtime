#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


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

    try:
        prefix.decode(
            "utf-8"
        )

        print(
            "prefix_utf8:",
            True,
        )

    except UnicodeDecodeError as exc:
        print(
            "prefix_utf8:",
            False,
        )

        print(
            "utf8_error:",
            str(
                exc
            ),
        )


def main() -> None:
    describe(
        DATRIX
    )

    print(
        "siblings:"
    )

    for path in sorted(
        DATRIX.parent.glob(
            DATRIX.name + "*"
        )
    ):
        print(
            " ",
            path.name,
            path.stat().st_size,
        )


if __name__ == "__main__":
    main()
