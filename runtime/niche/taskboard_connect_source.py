#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


PATH = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/niche/runtime/"
    "living_task.py"
)


def main() -> int:
    if not PATH.is_file():
        print(
            "ABSENT: "
            + str(PATH)
        )
        return 1

    lines = PATH.read_text(
        encoding="utf-8"
    ).splitlines()

    ranges = (
        (1, 80),
        (390, 535),
    )

    for start, end in ranges:
        print(
            "\n===== "
            + str(PATH)
            + f" {start}:{end} ====="
        )

        for number in range(
            start,
            min(end, len(lines)) + 1,
        ):
            print(
                f"{number:05d}: "
                f"{lines[number - 1]}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
