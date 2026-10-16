#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


SERVER = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/niche/apps/taskboard/server.py"
)


def main() -> None:
    lines = SERVER.read_text(
        encoding="utf-8"
    ).splitlines()

    for number in range(
        1880,
        min(
            1970,
            len(lines),
        )
        + 1,
    ):
        print(
            f"{number}:"
            + lines[number - 1]
        )


if __name__ == "__main__":
    main()
