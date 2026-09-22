#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


runtime_root = Path(
    "/root/savant-runtime"
)

scanner_path = (
    runtime_root
    / "assurance"
    / "convergence"
    / "modularity"
    / "scanners"
    / "inventory_modular_primitive_convergence.py"
)

report_path = (
    runtime_root
    / "assurance"
    / "convergence"
    / "modularity"
    / "reports"
    / "modular-primitive-convergence.json"
)

vessel_prefix = (
    "ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/"
    "exiles/underscore/rubric/vessel/"
)

completed_groups = {
    "primitive-1d91efc1ad6348bb23b2",
    "primitive-6dcbfaa4de7a5965d3f9",
    "primitive-fe195d9501d9ce175a66",
}


def run_inventory() -> None:
    completed = subprocess.run(
        [
            "python3",
            str(scanner_path),
            "inventory",
            "--root",
            str(runtime_root),
            "--output",
            str(report_path),
        ],
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "convergence inventory failed with "
            f"exit status {completed.returncode}"
        )


def walk(
    value: Any,
):
    if isinstance(
        value,
        dict,
    ):
        yield value

        for child in value.values():
            yield from walk(
                child
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            yield from walk(
                child
            )


def vessel_paths(
    group: dict[str, Any],
) -> list[str]:
    members = group.get(
        "members"
    )

    if not isinstance(
        members,
        list,
    ):
        return []

    result: list[str] = []

    for member in members:
        if not isinstance(
            member,
            dict,
        ):
            continue

        path = member.get(
            "path"
        )

        if not isinstance(
            path,
            str,
        ):
            continue

        if path.startswith(
            vessel_prefix
        ):
            result.append(
                path
            )

    return result


def candidate_groups(
    report: Any,
) -> list[dict[str, Any]]:
    candidates: list[
        dict[str, Any]
    ] = []

    for value in walk(
        report
    ):
        group_id = value.get(
            "group_id"
        )

        if not isinstance(
            group_id,
            str,
        ):
            continue

        if group_id in completed_groups:
            continue

        if value.get(
            "disposition"
        ) != "instance":
            continue

        paths = vessel_paths(
            value
        )

        if not paths:
            continue

        owner_hint = value.get(
            "owner_hint"
        )

        if not isinstance(
            owner_hint,
            dict,
        ):
            continue

        if owner_hint.get(
            "classification"
        ) != "existing_rubric_scope":
            continue

        candidates.append(
            {
                "group_id":
                    group_id,
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
                    owner_hint,
                "vessel_paths":
                    paths,
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(
                item.get(
                    "occurrence_count"
                )
                or 0
            ),
            str(
                item.get(
                    "group_id"
                )
            ),
        )
    )

    return candidates


def main() -> int:
    if not scanner_path.is_file():
        raise RuntimeError(
            "convergence scanner unavailable: "
            + str(scanner_path)
        )

    run_inventory()

    with report_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        report = json.load(
            handle
        )

    serialized = json.dumps(
        report,
        sort_keys=True,
    )

    load_json_group_present = (
        "primitive-fe195d9501d9ce175a66"
        in serialized
    )

    candidates = candidate_groups(
        report
    )

    result = {
        "schema":
            "savant.assurance."
            "vessel-convergence-advance.v1",
        "authority_effect":
            "none",
        "load_json_convergence": (
            "failed"
            if load_json_group_present
            else "passed"
        ),
        "completed_group_present":
            load_json_group_present,
        "next_instance_family": (
            candidates[0]
            if candidates
            else None
        ),
        "remaining_instance_family_count":
            len(candidates),
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    if load_json_group_present:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
