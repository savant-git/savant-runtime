#!/usr/bin/env python3
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "segue-reconciliation"
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


class SegueReconciliationError(RuntimeError):
    pass


def utc_now() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
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


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(
        value,
        dict,
    ):
        return {
            key: deterministic_projection(
                child
            )
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                child
            )
            for child in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return tuple(
            deterministic_projection(
                child
            )
            for child in value
        )

    return value


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(
                value
            )
        )
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


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
        raise SegueReconciliationError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                value
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(
            path
        )


def authority_rank(
    segue: dict[str, Any],
) -> tuple[int, int, str]:
    authority = segue.get(
        "authority",
        {},
    )

    if not isinstance(
        authority,
        dict,
    ):
        authority = {}

    state = authority.get(
        "state"
    )

    state_rank = {
        "authoritative": 0,
        "accepted": 1,
        "proposed": 2,
        "observed": 3,
        "unknown": 4,
        "rejected": 5,
        "superseded": 6,
    }.get(
        str(state),
        99,
    )

    tier = authority.get(
        "tier"
    )

    if not isinstance(
        tier,
        int,
    ):
        tier = 999

    identifier = str(
        segue.get(
            "id",
            "",
        )
    )

    return (
        state_rank,
        tier,
        identifier,
    )


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


def canonicalize_graph(
    graph: dict[str, Any],
) -> dict[str, Any]:
    canonical_graph = json.loads(
        json.dumps(
            graph
        )
    )

    segues = canonical_graph.get(
        "segues",
        [],
    )

    if not isinstance(
        segues,
        list,
    ):
        raise SegueReconciliationError(
            "Graph segues must be a list."
        )

    canonical_graph[
        "segues"
    ] = sorted(
        segues,
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

    return canonical_graph


def build_plan(
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
        raise SegueReconciliationError(
            "Graph segues must be a list."
        )

    canonical_graph = canonicalize_graph(
        graph
    )

    canonical_segues = canonical_graph[
        "segues"
    ]

    groups: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = collections.defaultdict(
        list
    )

    identifiers: set[str] = set()

    for segue in canonical_segues:
        if not isinstance(
            segue,
            dict,
        ):
            raise SegueReconciliationError(
                "Graph contains an invalid segue."
            )

        identifier = segue.get(
            "id"
        )

        if not isinstance(
            identifier,
            str,
        ):
            raise SegueReconciliationError(
                "Segue has no string identifier."
            )

        if identifier in identifiers:
            raise SegueReconciliationError(
                (
                    "Exact segue identity is duplicated: "
                    f"{identifier}"
                )
            )

        identifiers.add(
            identifier
        )

        groups[
            semantic_key(
                segue
            )
        ].append(
            segue
        )

    duplicate_groups = []

    retained_ids: set[str] = set()
    removal_ids: set[str] = set()

    for key, members in sorted(
        groups.items(),
        key=lambda item: item[0],
    ):
        ordered = sorted(
            members,
            key=authority_rank,
        )

        retained = ordered[0]

        retained_id = str(
            retained[
                "id"
            ]
        )

        retained_ids.add(
            retained_id
        )

        duplicates = ordered[
            1:
        ]

        for duplicate in duplicates:
            removal_ids.add(
                str(
                    duplicate[
                        "id"
                    ]
                )
            )

        if duplicates:
            duplicate_groups.append(
                {
                    "semantic_key": {
                        "type": key[0],
                        "source": key[1],
                        "target": key[2],
                    },
                    "retained": {
                        "id": retained_id,
                        "authority": retained.get(
                            "authority"
                        ),
                        "semantic_digest": (
                            semantic_digest(
                                retained
                            )
                        ),
                    },
                    "duplicates": [
                        {
                            "id": duplicate.get(
                                "id"
                            ),
                            "authority": duplicate.get(
                                "authority"
                            ),
                            "semantic_digest": (
                                semantic_digest(
                                    duplicate
                                )
                            ),
                            "exact_record_match": (
                                semantic_digest(
                                    duplicate
                                )
                                == semantic_digest(
                                    retained
                                )
                            ),
                        }
                        for duplicate in duplicates
                    ],
                }
            )

    proposed_segues = sorted(
        (
            segue
            for segue in canonical_segues
            if str(
                segue.get(
                    "id",
                    "",
                )
            )
            not in removal_ids
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

    proposal = json.loads(
        json.dumps(
            canonical_graph
        )
    )

    proposal[
        "segues"
    ] = proposed_segues

    plan: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "segue-reconciliation-plan/1.0.0"
        ),
        "operation": (
            "plan_duplicate_segue_reconciliation"
        ),
        "generated_at": utc_now(),
        "passed": True,
        "apply_authorized": False,
        "authority_note": (
            "This plan does not mutate authority. "
            "Removal requires explicit accepted decision."
        ),
        "graph": {
            "path": relative_path(
                GRAPH_PATH
            ),
            "sha256": sha256_path(
                GRAPH_PATH
            ),
            "semantic_digest": (
                semantic_digest(
                    canonical_graph
                )
            ),
        },
        "statistics": {
            "original_segue_count": len(
                canonical_segues
            ),
            "semantic_relationship_count": len(
                groups
            ),
            "duplicate_group_count": len(
                duplicate_groups
            ),
            "proposed_removal_count": len(
                removal_ids
            ),
            "proposed_segue_count": len(
                proposed_segues
            ),
        },
        "duplicate_groups": (
            duplicate_groups
        ),
        "retained_ids": sorted(
            retained_ids
        ),
        "proposed_removal_ids": sorted(
            removal_ids
        ),
        "proposal": {
            "graph_semantic_digest": (
                semantic_digest(
                    proposal
                )
            ),
            "segues_semantic_digest": (
                semantic_digest(
                    proposed_segues
                )
            ),
        },
    }

    plan[
        "semantic_digest"
    ] = semantic_digest(
        plan
    )

    return plan


def main() -> int:
    try:
        graph = load_json(
            GRAPH_PATH
        )

        plan = build_plan(
            graph
        )

        REPORT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        run_id = timestamp()

        historical = (
            REPORT_ROOT
            / (
                f"{run_id}__"
                "segue-reconciliation-plan.json"
            )
        )

        latest = (
            REPORT_ROOT
            / "latest.json"
        )

        atomic_write_json(
            historical,
            plan,
        )

        atomic_write_json(
            latest,
            plan,
        )

        plan[
            "reports"
        ] = {
            "historical": relative_path(
                historical
            ),
            "latest": relative_path(
                latest
            ),
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "plan_duplicate_"
                        "segue_reconciliation"
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
            plan,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
