#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/niche"
)

TARGETS = (
    (
        ROOT / "runtime/task_engine.py",
        360,
        435,
    ),
    (
        ROOT / "runtime/task_engine.py",
        690,
        790,
    ),
    (
        ROOT / "runtime/living_task.py",
        2160,
        2245,
    ),
)


def emit(
    path: Path,
    start: int,
    end: int,
) -> None:
    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    print(
        f"\n===== {path} "
        f"{start}:{end} ====="
    )

    for number in range(
        start,
        min(end, len(lines)) + 1,
    ):
        print(
            f"{number:05d}: "
            f"{lines[number - 1]}"
        )


def main() -> int:
    for path, start, end in TARGETS:
        if not path.is_file():
            print(
                f"\nABSENT: {path}"
            )
            continue

        emit(
            path,
            start,
            end,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
