#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "post-vessel-convergence-advance.v1"
)

authority_effect = "none"

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

vessel_scope = (
    "ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/"
    "_template/segue/exiles/underscore/"
    "rubric/vessel"
)

parked_scope_fragments = (
    "/chimera/",
    "/carbon/",
)

completed_groups = {
    "primitive-1d91efc1ad6348bb23b2",
    "primitive-6dcbfaa4de7a5965d3f9",
    "primitive-fe195d9501d9ce175a66",
    "primitive-1116a2b273621880eb9d",
    "primitive-3f3b4fc22afa44f7e588",
    "primitive-6f61211d73cc5f32637f",
    "primitive-cfb51b345c26d3cb3451",
}

deferred_groups = {
    "primitive-8a77c7ebf848b79ebc94",
    "primitive-33d60b578eb52d9f677b",
    "primitive-5bd045779f6b51a6e6ae",
    "primitive-8981ccee0859a6a45e9a",
    "primitive-de8cf653831eae4e1fa4",
    "primitive-53e2d9b8b8b3fb30a9a8",
    "primitive-1124a9a42d33de6a972c",
    "primitive-8152f6a957b02b897096",
}


def run_inventory() -> None:
    if not scanner_path.is_file():
        raise RuntimeError(
            "convergence scanner unavailable"
        )

    command = [
        sys.executable,
        str(scanner_path),
        "inventory",
        "--root",
        str(runtime_root),
        "--output",
        str(report_path),
    ]

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        error = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or (
                "inventory scanner exited "
                f"{completed.returncode}"
            )
        )

        raise RuntimeError(
            error
        )


def load_report() -> dict[str, Any]:
    if not report_path.is_file():
        raise RuntimeError(
            "convergence report unavailable"
        )

    with report_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(
            handle
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "convergence report must be object"
        )

    return payload


def report_groups(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    candidate_keys = (
        "duplicate_implementation_groups",
        "groups",
        "primitive_groups",
        "duplicates",
    )

    for key in candidate_keys:
        value = report.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return [
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            ]

    for value in report.values():
        if not isinstance(
            value,
            list,
        ):
            continue

        objects = [
            item
            for item in value
            if isinstance(
                item,
                dict,
            )
        ]

        if not objects:
            continue

        if any(
            (
                "group_id" in item
                and "disposition" in item
            )
            for item in objects
        ):
            return objects

    raise RuntimeError(
        "unable to locate primitive groups "
        "in convergence report"
    )


def member_paths(
    group: dict[str, Any],
) -> list[str]:
    result: list[str] = []

    direct_paths = group.get(
        "paths"
    )

    if isinstance(
        direct_paths,
        list,
    ):
        for value in direct_paths:
            if isinstance(
                value,
                str,
            ):
                result.append(
                    value
                )

    members = group.get(
        "members"
    )

    if isinstance(
        members,
        list,
    ):
        for member in members:
            if isinstance(
                member,
                str,
            ):
                result.append(
                    member
                )

            elif isinstance(
                member,
                dict,
            ):
                for key in (
                    "path",
                    "file",
                    "relative_path",
                ):
                    value = member.get(
                        key
                    )

                    if isinstance(
                        value,
                        str,
                    ):
                        result.append(
                            value
                        )
                        break

    return sorted(
        set(
            result
        )
    )


def is_parked(
    paths: list[str],
) -> bool:
    for path in paths:
        normalized = (
            "/"
            + path.strip("/")
            + "/"
        )

        if any(
            fragment in normalized
            for fragment
            in parked_scope_fragments
        ):
            return True

    return False


def is_vessel_only(
    paths: list[str],
) -> bool:
    if not paths:
        return False

    return all(
        path.startswith(
            vessel_scope
        )
        for path in paths
    )


def owner_classification(
    group: dict[str, Any],
) -> str | None:
    owner_hint = group.get(
        "owner_hint"
    )

    if not isinstance(
        owner_hint,
        dict,
    ):
        return None

    value = owner_hint.get(
        "classification"
    )

    if isinstance(
        value,
        str,
    ):
        return value

    return None


def owner_scope(
    group: dict[str, Any],
) -> str | None:
    owner_hint = group.get(
        "owner_hint"
    )

    if not isinstance(
        owner_hint,
        dict,
    ):
        return None

    value = owner_hint.get(
        "scope"
    )

    if isinstance(
        value,
        str,
    ):
        return value

    return None


def occurrence_count(
    group: dict[str, Any],
) -> int:
    value = group.get(
        "occurrence_count"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    paths = member_paths(
        group
    )

    return len(
        paths
    )


def file_count(
    group: dict[str, Any],
) -> int:
    value = group.get(
        "file_count"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    return len(
        member_paths(
            group
        )
    )


def names(
    group: dict[str, Any],
) -> list[str]:
    value = group.get(
        "names"
    )

    if isinstance(
        value,
        list,
    ):
        return sorted(
            item
            for item in value
            if isinstance(
                item,
                str,
            )
        )

    value = group.get(
        "name"
    )

    if isinstance(
        value,
        str,
    ):
        return [
            value
        ]

    return []


def eligible(
    group: dict[str, Any],
) -> bool:
    group_id = group.get(
        "group_id"
    )

    if not isinstance(
        group_id,
        str,
    ):
        return False

    if (
        group_id in completed_groups
        or group_id in deferred_groups
    ):
        return False

    if group.get(
        "disposition"
    ) != "instance":
        return False

    if (
        owner_classification(
            group
        )
        != "existing_rubric_scope"
    ):
        return False

    paths = member_paths(
        group
    )

    if not paths:
        return False

    if is_vessel_only(
        paths
    ):
        return False

    if is_parked(
        paths
    ):
        return False

    return True


def candidate_view(
    group: dict[str, Any],
) -> dict[str, Any]:
    return {
        "group_id":
            group.get(
                "group_id"
            ),
        "names":
            names(
                group
            ),
        "disposition":
            group.get(
                "disposition"
            ),
        "file_count":
            file_count(
                group
            ),
        "occurrence_count":
            occurrence_count(
                group
            ),
        "narrowest_common_scope":
            group.get(
                "narrowest_common_scope"
            ),
        "owner_hint": {
            "classification":
                owner_classification(
                    group
                ),
            "scope":
                owner_scope(
                    group
                ),
            "authority_effect":
                "none",
        },
        "paths":
            member_paths(
                group
            ),
    }


def main() -> int:
    try:
        run_inventory()

        report = load_report()

        groups = report_groups(
            report
        )

        candidates = [
            group
            for group in groups
            if eligible(
                group
            )
        ]

        candidates.sort(
            key=lambda group: (
                -occurrence_count(
                    group
                ),
                str(
                    group.get(
                        "group_id",
                        "",
                    )
                ),
            )
        )

        next_family = (
            candidate_view(
                candidates[0]
            )
            if candidates
            else None
        )

        result = {
            "schema":
                schema_version,
            "authority_effect":
                authority_effect,
            "vessel_instance_convergence":
                "complete",
            "next_instance_family":
                next_family,
            "eligible_family_count":
                len(
                    candidates
                ),
            "completed_group_count":
                len(
                    completed_groups
                ),
            "deferred_group_count":
                len(
                    deferred_groups
                ),
        }

    except Exception as exc:
        result = {
            "schema":
                schema_version,
            "authority_effect":
                authority_effect,
            "status":
                "failed",
            "error":
                str(exc),
        }

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
