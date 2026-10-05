#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from collections import defaultdict
from pathlib import Path
from typing import Any


runtime_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/"
    "segue/gates/_template/segue/"
    "innates/_template/segue/"
    "exiles/niche/runtime"
)

schema = (
    "savant://runtime/niche/"
    "decomposition-reconciler/1.0.0"
)

completion_schema = (
    "savant://runtime/niche/"
    "completion-engine/1.0.0"
)

owner = "exile:niche"


if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )


from task_engine import engine  # noqa: E402


def completion_meta(
    task: Any,
) -> dict[str, Any]:
    slots = getattr(
        task,
        "extension_slots",
        {},
    )

    if not isinstance(
        slots,
        dict,
    ):
        return {}

    value = slots.get(
        "completion",
        {},
    )

    if not isinstance(
        value,
        dict,
    ):
        return {}

    if value.get(
        "schema"
    ) != completion_schema:
        return {}

    return value


def authoritative_tasks() -> dict[
    str,
    Any,
]:
    return {
        task.task_id: task
        for task
        in engine.runtime.tasks()
    }


def desired_children(
    tasks: dict[str, Any],
) -> dict[
    str,
    tuple[str, ...],
]:
    grouped: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for task_id, task in tasks.items():
        meta = completion_meta(
            task
        )

        if not meta:
            continue

        parent_id = str(
            meta.get(
                "parent_id"
            )
            or ""
        ).strip()

        if not parent_id:
            continue

        if parent_id == task_id:
            continue

        if parent_id not in tasks:
            continue

        parent_meta = completion_meta(
            tasks[parent_id]
        )

        if not parent_meta:
            continue

        grouped[
            parent_id
        ].add(
            task_id
        )

    result: dict[
        str,
        tuple[str, ...],
    ] = {}

    for task_id, task in tasks.items():
        if not completion_meta(
            task
        ):
            continue

        result[
            task_id
        ] = tuple(
            sorted(
                grouped.get(
                    task_id,
                    set(),
                )
            )
        )

    return result


def current_children(
    task: Any,
) -> tuple[str, ...]:
    value = getattr(
        task,
        "decomposition_children",
        (),
    )

    return tuple(
        sorted(
            {
                str(item).strip()
                for item in value
                if str(item).strip()
            }
        )
    )


def plan() -> dict[str, Any]:
    tasks = authoritative_tasks()

    desired = desired_children(
        tasks
    )

    amendments: list[
        dict[str, Any]
    ] = []

    unchanged: list[str] = []

    for task_id in sorted(
        desired
    ):
        task = tasks[
            task_id
        ]

        before = current_children(
            task
        )

        after = desired[
            task_id
        ]

        if before == after:
            unchanged.append(
                task_id
            )
            continue

        amendments.append(
            {
                "task_id":
                    task_id,

                "before":
                    list(
                        before
                    ),

                "after":
                    list(
                        after
                    ),

                "added":
                    sorted(
                        set(after)
                        - set(before)
                    ),

                "removed":
                    sorted(
                        set(before)
                        - set(after)
                    ),
            }
        )

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "completion_task_count":
            len(desired),

        "amendment_count":
            len(amendments),

        "unchanged_count":
            len(unchanged),

        "amendments":
            amendments,

        "unchanged":
            unchanged,
    }


def apply() -> dict[str, Any]:
    planned = plan()

    amended: list[str] = []
    failed: list[
        dict[str, str]
    ] = []

    for amendment in planned[
        "amendments"
    ]:
        task_id = amendment[
            "task_id"
        ]

        try:
            engine.amend(
                task_id,
                {
                    "decomposition_children":
                        amendment[
                            "after"
                        ],
                },
            )

            amended.append(
                task_id
            )

        except Exception as exc:
            failed.append(
                {
                    "task_id":
                        task_id,

                    "error":
                        str(exc),
                }
            )

            break

    post = plan()

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "task-amendment",

        "requested_amendment_count":
            planned[
                "amendment_count"
            ],

        "amended_count":
            len(amended),

        "failed_count":
            len(failed),

        "remaining_amendment_count":
            post[
                "amendment_count"
            ],

        "amended":
            amended,

        "failed":
            failed,

        "healthy":
            (
                not failed
                and post[
                    "amendment_count"
                ] == 0
            ),

        "niche":
            engine.health(),
    }


def health() -> dict[str, Any]:
    planned = plan()

    niche = engine.health()

    return {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            "none",

        "healthy":
            bool(
                niche.get(
                    "healthy",
                    False,
                )
            ),

        "completion_task_count":
            planned[
                "completion_task_count"
            ],

        "pending_amendment_count":
            planned[
                "amendment_count"
            ],

        "lineage_reconciled":
            (
                planned[
                    "amendment_count"
                ] == 0
            ),

        "niche":
            niche,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=(
            "decomposition_reconciler"
        )
    )

    commands = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    commands.add_parser(
        "preview"
    )

    commands.add_parser(
        "apply"
    )

    commands.add_parser(
        "health"
    )

    args = parser.parse_args()

    if args.command == "preview":
        payload = plan()
        exit_code = 0

    elif args.command == "apply":
        payload = apply()

        exit_code = (
            0
            if payload[
                "healthy"
            ]
            else 1
        )

    elif args.command == "health":
        payload = health()

        exit_code = (
            0
            if payload[
                "healthy"
            ]
            else 1
        )

    else:
        return 2

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
