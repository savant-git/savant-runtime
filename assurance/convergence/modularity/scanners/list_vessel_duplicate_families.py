#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


report_path = Path(
    "/root/savant-runtime/assurance/convergence/modularity/reports/"
    "modular-primitive-convergence.json"
)

vessel_prefix = (
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/underscore/rubric/vessel/"
)


def emit_group(
    value: dict[str, Any],
) -> None:
    members = value.get("members")

    if not isinstance(
        members,
        list,
    ):
        return

    paths = [
        member.get(
            "path",
            "",
        )
        for member in members
        if isinstance(
            member,
            dict,
        )
    ]

    vessel_paths = [
        path
        for path in paths
        if (
            isinstance(
                path,
                str,
            )
            and path.startswith(
                vessel_prefix
            )
        )
    ]

    if not vessel_paths:
        return

    print(
        json.dumps(
            {
                "group_id":
                    value.get(
                        "group_id"
                    ),
                "disposition":
                    value.get(
                        "disposition"
                    ),
                "names":
                    value.get(
                        "names"
                    ),
                "file_count":
                    value.get(
                        "file_count"
                    ),
                "occurrence_count":
                    value.get(
                        "occurrence_count"
                    ),
                "narrowest_common_scope":
                    value.get(
                        "narrowest_common_scope"
                    ),
                "owner_hint":
                    value.get(
                        "owner_hint"
                    ),
                "vessel_paths":
                    vessel_paths,
            },
            indent=2,
            sort_keys=True,
        )
    )


def walk(
    value: Any,
) -> None:
    if isinstance(
        value,
        dict,
    ):
        emit_group(
            value
        )

        for child in value.values():
            walk(
                child
            )

        return

    if isinstance(
        value,
        list,
    ):
        for child in value:
            walk(
                child
            )


def main() -> int:
    if not report_path.is_file():
        raise SystemExit(
            "convergence report unavailable: "
            + str(report_path)
        )

    with report_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        report = json.load(
            handle
        )

    walk(
        report
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
