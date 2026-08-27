#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

LIVING_MODULE = (
    ROOT
    / "runtime/scyon/living_engine.py"
)

FOCAL_PATH = (
    ROOT
    / "runtime/scyon/focals/living-structure.json"
)

DEFAULT_DATABASE = (
    ROOT
    / "runtime/scyon/state/living-structure.sqlite3"
)

DEFAULT_PROJECTION = (
    ROOT
    / "runtime/scyon/projections/living-structure/latest.json"
)

DEFAULT_STATE_PROJECTION = (
    ROOT
    / "runtime/scyon/projections/living-structure/state.json"
)


class StateError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise StateError(message)


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"missing JSON file: {path}",
    )

    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def load_living() -> Any:
    require(
        LIVING_MODULE.is_file(),
        f"LivingEngine missing: {LIVING_MODULE}",
    )

    specification = importlib.util.spec_from_file_location(
        "savant_living_engine_state",
        LIVING_MODULE,
    )

    require(
        specification is not None
        and specification.loader is not None,
        "cannot load LivingEngine",
    )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def integer(
    value: Any,
) -> int:
    if value is None:
        return 0

    if isinstance(value, bool):
        return int(value)

    return int(value)


@dataclass(
    frozen=True,
    slots=True,
)
class StructuralMetrics:
    file_count: int
    parse_errors: int
    ownership_conflicts: int
    unresolved_source_owners: int
    migration_candidates: int
    proposal_blocked: int
    proposal_collisions: int
    proposal_stage_moves: int
    proposal_present: bool

    @classmethod
    def from_projection(
        cls,
        projection: dict[str, Any],
    ) -> "StructuralMetrics":
        structure = projection.get(
            "structure",
            {},
        )

        proposal = projection.get(
            "migration_proposal",
            {},
        )

        require(
            isinstance(structure, dict),
            "structure projection must be object",
        )

        require(
            isinstance(proposal, dict),
            "migration proposal projection must be object",
        )

        structure_summary = structure.get(
            "summary",
            {},
        )

        proposal_summary = proposal.get(
            "summary",
            {},
        )

        if not isinstance(
            structure_summary,
            dict,
        ):
            structure_summary = {}

        if not isinstance(
            proposal_summary,
            dict,
        ):
            proposal_summary = {}

        return cls(
            file_count=integer(
                structure_summary.get(
                    "file_count"
                )
            ),
            parse_errors=integer(
                structure_summary.get(
                    "parse_error_count"
                )
            ),
            ownership_conflicts=integer(
                structure_summary.get(
                    "ownership_conflict_count"
                )
            ),
            unresolved_source_owners=integer(
                structure_summary.get(
                    "unresolved_source_owner_count"
                )
            ),
            migration_candidates=integer(
                structure_summary.get(
                    "migration_candidate_count"
                )
            ),
            proposal_blocked=integer(
                proposal_summary.get(
                    "blocked_count"
                )
            ),
            proposal_collisions=integer(
                proposal_summary.get(
                    "collision_count"
                )
            ),
            proposal_stage_moves=integer(
                proposal_summary.get(
                    "stage_move_count"
                )
            ),
            proposal_present=bool(
                proposal.get("manifest")
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "file_count": self.file_count,
            "parse_errors": self.parse_errors,
            "ownership_conflicts": (
                self.ownership_conflicts
            ),
            "unresolved_source_owners": (
                self.unresolved_source_owners
            ),
            "migration_candidates": (
                self.migration_candidates
            ),
            "proposal_blocked": (
                self.proposal_blocked
            ),
            "proposal_collisions": (
                self.proposal_collisions
            ),
            "proposal_stage_moves": (
                self.proposal_stage_moves
            ),
            "proposal_present": (
                self.proposal_present
            ),
        }


STATE_DEFINITIONS: tuple[
    dict[str, Any],
    ...,
] = (
    {
        "ordinal": 1,
        "id": "unobserved",
        "meaning": (
            "No valid structural observation "
            "is available."
        ),
    },
    {
        "ordinal": 2,
        "id": "invalid",
        "meaning": (
            "Observed structural evidence "
            "cannot pass validation."
        ),
    },
    {
        "ordinal": 3,
        "id": "parse-blocked",
        "meaning": (
            "Structural classification is "
            "blocked by parse failures."
        ),
    },
    {
        "ordinal": 4,
        "id": "ownership-blocked",
        "meaning": (
            "Structural classification is "
            "blocked by unresolved ownership."
        ),
    },
    {
        "ordinal": 5,
        "id": "collision-blocked",
        "meaning": (
            "A migration proposal exists but "
            "contains destination collisions."
        ),
    },
    {
        "ordinal": 6,
        "id": "proposal-pending",
        "meaning": (
            "Structural evidence is sufficiently "
            "classified to compile or refresh a "
            "non-mutating proposal."
        ),
    },
    {
        "ordinal": 7,
        "id": "proposal-blocked",
        "meaning": (
            "A proposal exists but still contains "
            "blocked artifacts."
        ),
    },
    {
        "ordinal": 8,
        "id": "review-ready",
        "meaning": (
            "The proposal has no known structural "
            "blockers and is ready for validation "
            "and authority review."
        ),
    },
    {
        "ordinal": 9,
        "id": "authority-required",
        "meaning": (
            "Technical prerequisites are satisfied; "
            "explicit accepted migration authority "
            "is still required before mutation."
        ),
    },
)


def state_ids() -> set[str]:
    return {
        str(item["id"])
        for item in STATE_DEFINITIONS
    }


def classify(
    metrics: StructuralMetrics,
    *,
    projection_valid: bool,
) -> tuple[str, list[str]]:
    if metrics.file_count <= 0:
        return (
            "unobserved",
            [
                "Produce a read-only Structure "
                "Intelligence observation."
            ],
        )

    if not projection_valid:
        return (
            "invalid",
            [
                "Repair projection or Scyon "
                "integrity before continuing."
            ],
        )

    if metrics.parse_errors > 0:
        return (
            "parse-blocked",
            [
                "Resolve parse errors without "
                "inventing ownership.",
                "Re-run Structure Intelligence.",
            ],
        )

    if (
        metrics.ownership_conflicts > 0
        or metrics.unresolved_source_owners > 0
    ):
        return (
            "ownership-blocked",
            [
                "Reconcile semantic ownership "
                "using accepted authority.",
                "Preserve unresolved artifacts "
                "in place.",
                "Re-run Structure Intelligence.",
            ],
        )

    if (
        metrics.proposal_present
        and metrics.proposal_collisions > 0
    ):
        return (
            "collision-blocked",
            [
                "Resolve canonical destination "
                "collisions.",
                "Recompile the non-mutating "
                "migration proposal.",
            ],
        )

    if not metrics.proposal_present:
        return (
            "proposal-pending",
            [
                "Compile a non-mutating migration "
                "proposal from this exact report."
            ],
        )

    if metrics.proposal_blocked > 0:
        return (
            "proposal-blocked",
            [
                "Resolve proposal blockers through "
                "authority, dependency, compatibility, "
                "or classification evidence.",
                "Do not execute staged moves.",
            ],
        )

    if metrics.proposal_stage_moves <= 0:
        return (
            "review-ready",
            [
                "Validate that the zero-move result "
                "is intentional and complete.",
                "Perform replay and behavior "
                "comparison.",
            ],
        )

    return (
        "authority-required",
        [
            "Perform final replay validation.",
            "Perform before/after identity and "
            "behavior comparison in simulation.",
            "Obtain explicit accepted migration "
            "authority before any physical mutation.",
        ],
    )


def latest_event_payloads(
    database: Path,
    event_type: str,
    *,
    limit: int = 2,
) -> list[dict[str, Any]]:
    if not database.is_file():
        return []

    connection = sqlite3.connect(
        str(database)
    )

    connection.row_factory = (
        sqlite3.Row
    )

    try:
        rows = connection.execute(
            """
            SELECT
                sequence,
                event_id,
                payload_json,
                digest,
                recorded_at
            FROM event
            WHERE event_type = ?
            ORDER BY sequence DESC
            LIMIT ?
            """,
            (
                event_type,
                limit,
            ),
        ).fetchall()

    finally:
        connection.close()

    result: list[
        dict[str, Any]
    ] = []

    for row in rows:
        payload = json.loads(
            row["payload_json"]
        )

        result.append(
            {
                "sequence": row[
                    "sequence"
                ],
                "event_id": row[
                    "event_id"
                ],
                "digest": row[
                    "digest"
                ],
                "recorded_at": row[
                    "recorded_at"
                ],
                "payload": payload,
            }
        )

    return result


def metric_delta(
    current: StructuralMetrics,
    previous_observation: dict[str, Any] | None,
) -> dict[str, int | None]:
    current_values = (
        current.as_dict()
    )

    previous_values: dict[
        str,
        Any,
    ] = {}

    if previous_observation:
        payload = previous_observation.get(
            "payload",
            {},
        )

        if isinstance(payload, dict):
            observation = payload.get(
                "observation",
                {},
            )

            if isinstance(
                observation,
                dict,
            ):
                summary = observation.get(
                    "summary",
                    {},
                )

                if isinstance(
                    summary,
                    dict,
                ):
                    previous_values = summary

    mapping = {
        "file_count": "file_count",
        "parse_errors": (
            "parse_error_count"
        ),
        "ownership_conflicts": (
            "ownership_conflict_count"
        ),
        "unresolved_source_owners": (
            "unresolved_source_owner_count"
        ),
        "migration_candidates": (
            "migration_candidate_count"
        ),
    }

    result: dict[
        str,
        int | None,
    ] = {}

    for current_name, previous_name in (
        mapping.items()
    ):
        if previous_name not in previous_values:
            result[current_name] = None
            continue

        result[current_name] = (
            integer(
                current_values[
                    current_name
                ]
            )
            - integer(
                previous_values[
                    previous_name
                ]
            )
        )

    return result


def trend_label(
    delta: int | None,
    *,
    lower_is_better: bool,
) -> str:
    if delta is None:
        return "unknown"

    if delta == 0:
        return "unchanged"

    if lower_is_better:
        return (
            "improved"
            if delta < 0
            else "regressed"
        )

    return (
        "increased"
        if delta > 0
        else "decreased"
    )


def build_state(
    projection: dict[str, Any],
    database: Path,
) -> dict[str, Any]:
    metrics = (
        StructuralMetrics.from_projection(
            projection
        )
    )

    checkpoint = projection.get(
        "checkpoint",
        {},
    )

    validation = (
        checkpoint.get(
            "validation",
            {},
        )
        if isinstance(
            checkpoint,
            dict,
        )
        else {}
    )

    projection_valid = bool(
        isinstance(
            validation,
            dict,
        )
        and validation.get(
            "valid"
        )
        is True
    )

    state_id, actions = classify(
        metrics,
        projection_valid=(
            projection_valid
        ),
    )

    require(
        state_id in state_ids(),
        f"illegal state: {state_id}",
    )

    observations = (
        latest_event_payloads(
            database,
            (
                "living.observation."
                "structure-intelligence"
            ),
            limit=2,
        )
    )

    previous = (
        observations[1]
        if len(observations) > 1
        else None
    )

    deltas = metric_delta(
        metrics,
        previous,
    )

    trends = {
        "parse_errors": trend_label(
            deltas[
                "parse_errors"
            ],
            lower_is_better=True,
        ),
        "ownership_conflicts": (
            trend_label(
                deltas[
                    "ownership_conflicts"
                ],
                lower_is_better=True,
            )
        ),
        "unresolved_source_owners": (
            trend_label(
                deltas[
                    "unresolved_source_owners"
                ],
                lower_is_better=True,
            )
        ),
        "migration_candidates": (
            trend_label(
                deltas[
                    "migration_candidates"
                ],
                lower_is_better=False,
            )
        ),
    }

    definition = next(
        item
        for item in STATE_DEFINITIONS
        if item["id"] == state_id
    )

    return {
        "schema": (
            "savant://runtime/scyon/"
            "living-structure-state/1.0.0"
        ),
        "authority_state": "projection",
        "rebuildable": True,
        "state": {
            "ordinal": definition[
                "ordinal"
            ],
            "id": state_id,
            "meaning": definition[
                "meaning"
            ],
        },
        "metrics": metrics.as_dict(),
        "delta_from_previous_structure_observation": (
            deltas
        ),
        "trends": trends,
        "next_legal_actions": actions,
        "hard_boundaries": {
            "migration_authorized": False,
            "physical_mutation_authorized": False,
            "destructive_mutation_authorized": False,
            "authority_rewrite_authorized": False,
            "historical_rewrite_authorized": False,
        },
        "state_taxonomy": list(
            STATE_DEFINITIONS
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Living Structure deterministic "
            "nine-state metabolism"
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )

    parser.add_argument(
        "--projection",
        type=Path,
        default=DEFAULT_PROJECTION,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_STATE_PROJECTION,
    )

    parser.add_argument(
        "command",
        choices=(
            "evaluate",
            "self-test",
        ),
    )

    arguments = parser.parse_args()

    if arguments.command == "self-test":
        synthetic = {
            "schema": (
                "savant://projection/"
                "living-structure/1.1.0"
            ),
            "checkpoint": {
                "validation": {
                    "valid": True,
                }
            },
            "structure": {
                "summary": {
                    "file_count": 100,
                    "parse_error_count": 0,
                    "ownership_conflict_count": 0,
                    "unresolved_source_owner_count": 0,
                    "migration_candidate_count": 5,
                }
            },
            "migration_proposal": {
                "manifest": {
                    "path": "synthetic",
                },
                "summary": {
                    "blocked_count": 0,
                    "collision_count": 0,
                    "stage_move_count": 5,
                },
            },
        }

        state = build_state(
            synthetic,
            Path(
                "/nonexistent/"
                "living-structure.sqlite3"
            ),
        )

        require(
            state["state"]["id"]
            == "authority-required",
            (
                "self-test did not reach "
                "authority-required"
            ),
        )

        require(
            state[
                "hard_boundaries"
            ][
                "migration_authorized"
            ]
            is False,
            (
                "self-test illegally "
                "authorized migration"
            ),
        )

        print(
            json.dumps(
                {
                    "self_test": "passed",
                    "state": state[
                        "state"
                    ],
                    "state_count": len(
                        STATE_DEFINITIONS
                    ),
                    "migration_authorized": False,
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    living = load_living()

    focal = (
        living.LivingFocal.from_path(
            FOCAL_PATH
        )
    )

    projection_path = (
        arguments.projection.resolve()
    )

    database = (
        arguments.database.resolve()
    )

    output = (
        arguments.output.resolve()
    )

    projection = load_json(
        projection_path
    )

    state = build_state(
        projection,
        database,
    )

    with living.LivingEngine(
        focal,
        database,
        root=ROOT,
    ) as engine:
        engine.bootstrap()

        observation = engine.observe(
            "structure-state",
            {
                "state": state["state"],
                "metrics": state["metrics"],
                "trends": state["trends"],
                "next_legal_actions": (
                    state[
                        "next_legal_actions"
                    ]
                ),
                "hard_boundaries": (
                    state[
                        "hard_boundaries"
                    ]
                ),
            },
            source=str(
                projection_path
            ),
            source_digest=(
                living.digest(
                    projection
                )
            ),
            dependencies=[
                (
                    "living.observation."
                    "structure-intelligence"
                ),
                (
                    "living.observation."
                    "structure-migration-proposal"
                ),
            ],
            authority_state="projection",
        )

        state[
            "scyon_observation"
        ] = observation

        state[
            "scyon_validation"
        ] = engine.kernel.validate()

        require(
            state[
                "scyon_validation"
            ][
                "valid"
            ]
            is True,
            "Scyon validation failed",
        )

    living.atomic_json(
        output,
        state,
    )

    print(
        json.dumps(
            state,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        sqlite3.DatabaseError,
        StateError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
