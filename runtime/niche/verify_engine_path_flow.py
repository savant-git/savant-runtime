#!/usr/bin/env python3

from __future__ import annotations

import inspect
import sys


NICHE_RUNTIME = (
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/niche/runtime"
)

NICHE_TASKBOARD = (
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/niche/apps/taskboard"
)

sys.path.insert(
    0,
    NICHE_RUNTIME,
)

sys.path.insert(
    0,
    NICHE_TASKBOARD,
)

import living_task
import task_engine
import server


def show(
    label: str,
    value: object,
) -> None:
    print(
        label + ":",
        value,
    )


def main() -> None:
    show(
        "server.default_db",
        getattr(
            server,
            "default_db",
            "<missing>",
        ),
    )

    show(
        "task_engine.default_db",
        getattr(
            task_engine,
            "default_db",
            "<missing>",
        ),
    )

    show(
        "living_task.DEFAULT_DB",
        getattr(
            living_task,
            "DEFAULT_DB",
            "<missing>",
        ),
    )

    show(
        "living_task.DEFAULT_DATRIX",
        getattr(
            living_task,
            "DEFAULT_DATRIX",
            "<missing>",
        ),
    )

    show(
        "TaskboardServer.__init__",
        inspect.signature(
            server.TaskboardServer.__init__
        ),
    )

    show(
        "task_engine.engine",
        inspect.signature(
            task_engine.engine
        ),
    )

    show(
        "NicheTaskEngine.__init__",
        inspect.signature(
            task_engine.NicheTaskEngine.__init__
        ),
    )

    show(
        "living_task.engine",
        inspect.signature(
            living_task.engine
        ),
    )

    show(
        "LivingTaskEngine.__init__",
        inspect.signature(
            living_task.LivingTaskEngine.__init__
        ),
    )

    parser = server.build_parser()

    args = parser.parse_args(
        []
    )

    show(
        "taskboard_parser_default_db",
        getattr(
            args,
            "db",
            "<missing>",
        ),
    )


if __name__ == "__main__":
    main()
