#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

PYTHON = (
    ROOT
    / "bin"
    / "identity-quality-python"
)

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

TEST_PATH = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
    / "tests"
    / "test_masterplan_segue_reconciliation.py"
)

PLANNER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "plan_duplicate_segue_reconciliation.py"
)

APPLIER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "apply_duplicate_segue_reconciliation.py"
)

INSPECTOR = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "inspect_duplicate_segues.py"
)

STATE_CHECKER = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "check_segue_reconciliation_state.py"
)

REQUIRED_FILES = (
    GRAPH_PATH,
    TEST_PATH,
    PLANNER,
    APPLIER,
    INSPECTOR,
    STATE_CHECKER,
)


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            value
        )
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def execute(
    command: list[str],
) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": (
            completed.returncode == 0
        ),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def semantic_key(
    segue: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        str(
            segue.get(
                "type",
                "",
            )
        ),
        str(
            segue.get(
                "source",
                "",
            )
        ),
        str(
            segue.get(
                "target",
                "",
            )
        ),
    )


def inspect_graph(
    graph: dict[str, Any],
) -> dict[str, Any]:
    segues = graph.get(
        "segues",
        [],
    )

    if not isinstance(
        segues,
        list,
    ):
        raise ValueError(
            "Graph segues are invalid."
        )

    identities: set[str] = set()

    groups: dict[
        tuple[str, str, str],
        list[str],
    ] = {}

    invalid_records: list[int] = []
    duplicate_identities: list[str] = []

    for index, segue in enumerate(
        segues
    ):
        if not isinstance(
            segue,
            dict,
        ):
            invalid_records.append(
                index
            )

            continue

        identifier = segue.get(
            "id"
        )

        if not isinstance(
            identifier,
            str,
        ) or not identifier:
            invalid_records.append(
                index
            )

            continue

        if identifier in identities:
            duplicate_identities.append(
                identifier
            )

        identities.add(
            identifier
        )

        groups.setdefault(
            semantic_key(
                segue
            ),
            [],
        ).append(
            identifier
        )

    duplicate_relationships = {
        "|".join(
            key
        ): sorted(
            identifiers
        )
        for key, identifiers in sorted(
            groups.items(),
            key=lambda item: item[0],
        )
        if len(
            identifiers
        ) > 1
    }

    return {
        "passed": (
            not invalid_records
            and not duplicate_identities
        ),
        "segue_count": len(
            segues
        ),
        "identity_count": len(
            identities
        ),
        "semantic_relationship_count": len(
            groups
        ),
        "duplicate_relationship_count": len(
            duplicate_relationships
        ),
        "duplicate_record_count": sum(
            len(
                identifiers
            ) - 1
            for identifiers
            in duplicate_relationships.values()
        ),
        "invalid_record_indexes": (
            invalid_records
        ),
        "duplicate_identities": sorted(
            set(
                duplicate_identities
            )
        ),
        "duplicate_relationships": (
            duplicate_relationships
        ),
        "segues_digest": semantic_digest(
            sorted(
                (
                    segue
                    for segue in segues
                    if isinstance(
                        segue,
                        dict,
                    )
                ),
                key=lambda segue: (
                    semantic_key(
                        segue
                    ),
                    str(
                        segue.get(
                            "id",
                            "",
                        )
                    ),
                ),
            )
        ),
    }


def file_status() -> dict[str, Any]:
    missing = [
        str(
            path
        )
        for path in REQUIRED_FILES
        if not path.is_file()
    ]

    return {
        "passed": not missing,
        "required_count": len(
            REQUIRED_FILES
        ),
        "missing": missing,
    }


def main() -> int:
    try:
        files = file_status()

        if not files[
            "passed"
        ]:
            result = {
                "schema": (
                    "savant://niche/masterplan/"
                    "segue-reconciliation-verification/"
                    "1.0.0"
                ),
                "operation": (
                    "verify_segue_reconciliation"
                ),
                "passed": False,
                "files": files,
                "graph": None,
                "stages": [],
            }

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )

            return 1

        graph = load_json(
            GRAPH_PATH
        )

        graph_status = inspect_graph(
            graph
        )

        stages: list[
            dict[str, Any]
        ] = []

        stage_definitions = (
            (
                "compile",
                [
                    str(
                        PYTHON
                    ),
                    "-m",
                    "py_compile",
                    str(
                        PLANNER
                    ),
                    str(
                        APPLIER
                    ),
                    str(
                        INSPECTOR
                    ),
                    str(
                        STATE_CHECKER
                    ),
                    str(
                        TEST_PATH
                    ),
                ],
            ),
            (
                "tests",
                [
                    str(
                        PYTHON
                    ),
                    "-m",
                    "pytest",
                    "-q",
                    str(
                        TEST_PATH
                    ),
                ],
            ),
            (
                "inspection",
                [
                    str(
                        PYTHON
                    ),
                    str(
                        INSPECTOR
                    ),
                ],
            ),
        )

        for stage_id, command in (
            stage_definitions
        ):
            stage = execute(
                command
            )

            stage[
                "stage_id"
            ] = stage_id

            stages.append(
                stage
            )

            if not stage[
                "passed"
            ]:
                break

        passed = all(
            (
                files[
                    "passed"
                ],
                graph_status[
                    "passed"
                ],
                len(
                    stages
                )
                == len(
                    stage_definitions
                ),
                all(
                    stage[
                        "passed"
                    ]
                    for stage in stages
                ),
            )
        )

        result = {
            "schema": (
                "savant://niche/masterplan/"
                "segue-reconciliation-verification/"
                "1.0.0"
            ),
            "operation": (
                "verify_segue_reconciliation"
            ),
            "passed": passed,
            "files": files,
            "graph": graph_status,
            "stages": stages,
            "statistics": {
                "planned_stage_count": len(
                    stage_definitions
                ),
                "executed_stage_count": len(
                    stages
                ),
                "passed_stage_count": sum(
                    stage[
                        "passed"
                    ]
                    for stage in stages
                ),
            },
        }

        result[
            "semantic_digest"
        ] = semantic_digest(
            result
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "verify_segue_reconciliation"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if result[
            "passed"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
