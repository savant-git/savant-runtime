#!/usr/bin/env python3

from __future__ import annotations

import sys


niche_runtime = (
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/niche/runtime"
)

sys.path.insert(
    0,
    niche_runtime,
)

import task_engine
import living_task


def main() -> None:
    print(
        "task_engine_file:",
        task_engine.__file__,
    )

    print(
        "task_engine_default_db:",
        task_engine.default_db,
    )

    print(
        "living_task_file:",
        living_task.__file__,
    )

    print(
        "living_task_default_db:",
        living_task.DEFAULT_DB,
    )

    print(
        "living_task_default_datrix:",
        living_task.DEFAULT_DATRIX,
    )


if __name__ == "__main__":
    main()
