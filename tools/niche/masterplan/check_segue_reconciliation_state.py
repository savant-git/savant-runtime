#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

DECISION_REPORT_PATH = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "decision-acceptance"
    / "latest.json"
)

APPLICATION_REPORT_PATH = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "segue-reconciliation"
    / "applications"
    / "latest.json"
)


def load_json(
    path: Path,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

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


def decision_id(
    value: dict[str, Any] | None,
) -> str | None:
    if value is None:
        return None

    for candidate in (
        value.get("decision_id"),
        value.get("id"),
    ):
        if isinstance(
            candidate,
            str,
        ) and candidate:
            return candidate

    nested = value.get(
        "decision"
    )

    if isinstance(
        nested,
        dict,
    ):
        candidate = nested.get(
            "id"
        )

        if isinstance(
            candidate,
            str,
        ) and candidate:
            return candidate

    return None


def duplicate_summary(
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
            "Graph segues are not a list."
        )

    groups: dict[
        tuple[str, str, str],
        list[str],
    ] = {}

    for segue in segues:
        if not isinstance(
            segue,
            dict,
        ):
            continue

        key = (
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

        groups.setdefault(
            key,
            [],
        ).append(
            str(
                segue.get(
                    "id",
                    "",
                )
            )
        )

    duplicates = {
        "|".join(key): sorted(
            identifiers
        )
        for key, identifiers in sorted(
            groups.items()
        )
        if len(
            identifiers
        ) > 1
    }

    return {
        "segue_count": len(
            segues
        ),
        "semantic_relationship_count": len(
            groups
        ),
        "duplicate_relationship_count": len(
            duplicates
        ),
        "duplicate_record_count": sum(
            len(
                identifiers
            ) - 1
            for identifiers
            in duplicates.values()
        ),
        "duplicates": duplicates,
    }


def main() -> int:
    graph = load_json(
        GRAPH_PATH
    )

    if graph is None:
        raise SystemExit(
            f"ERROR: graph does not exist: {GRAPH_PATH}"
        )

    decision_report = load_json(
        DECISION_REPORT_PATH
    )

    application_report = load_json(
        APPLICATION_REPORT_PATH
    )

    accepted_id = decision_id(
        decision_report
    )

    application_id = decision_id(
        application_report
    )

    output = {
        "graph": duplicate_summary(
            graph
        ),
        "accepted_decision": {
            "exists": (
                decision_report
                is not None
            ),
            "decision_id": (
                accepted_id
            ),
            "passed": (
                decision_report.get(
                    "passed"
                )
                if decision_report
                is not None
                else None
            ),
        },
        "application": {
            "exists": (
                application_report
                is not None
            ),
            "decision_id": (
                application_id
            ),
            "passed": (
                application_report.get(
                    "passed"
                )
                if application_report
                is not None
                else None
            ),
            "applied": (
                application_report.get(
                    "applied"
                )
                if application_report
                is not None
                else None
            ),
            "removed_count": (
                application_report.get(
                    "removed_count"
                )
                if application_report
                is not None
                else None
            ),
        },
    }

    output[
        "reconciliation_complete"
    ] = (
        output[
            "graph"
        ][
            "duplicate_relationship_count"
        ]
        == 0
        and output[
            "application"
        ][
            "passed"
        ]
        is True
        and output[
            "application"
        ][
            "applied"
        ]
        is True
    )

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if output[
            "reconciliation_complete"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
