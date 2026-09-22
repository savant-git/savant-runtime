#!/usr/bin/env python3
"""
savant / niche
read-path source extractor

owner: exile:niche
authority_effect: none
mutation_effect: none

Prints only the current implementation regions proven by the blocking
stack trace to participate in the Niche task read path.
"""

from __future__ import annotations

import json
from pathlib import Path


NICHE_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/niche"
)

FILES = {
    "living_task": NICHE_ROOT / "runtime/living_task.py",
    "task_engine": NICHE_ROOT / "runtime/task_engine.py",
}

RANGES = {
    "living_task": (
        (410, 465),
        (615, 715),
        (1960, 2115),
    ),
    "task_engine": (
        (535, 590),
        (635, 690),
    ),
}


def extract(
    path: Path,
    ranges: tuple[tuple[int, int], ...],
) -> list[dict[str, object]]:
    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    regions: list[dict[str, object]] = []

    for start, end in ranges:
        actual_start = max(1, start)
        actual_end = min(
            len(lines),
            end,
        )

        regions.append(
            {
                "start": actual_start,
                "end": actual_end,
                "source": "\n".join(
                    f"{number:05d}: {lines[number - 1]}"
                    for number in range(
                        actual_start,
                        actual_end + 1,
                    )
                ),
            }
        )

    return regions


def main() -> int:
    report: dict[str, object] = {
        "schema": "savant.niche.read-path-source.v1",
        "authority_effect": "none",
        "mutation_effect": "none",
        "evidence": (
            "ranges selected from the proven blocking traceback"
        ),
        "files": {},
    }

    files: dict[str, object] = {}

    for name, path in FILES.items():
        if not path.is_file():
            files[name] = {
                "path": str(path),
                "present": False,
            }
            continue

        files[name] = {
            "path": str(path),
            "present": True,
            "regions": extract(
                path,
                RANGES[name],
            ),
        }

    report["files"] = files

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
