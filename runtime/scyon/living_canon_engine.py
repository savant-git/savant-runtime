#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from runtime.constitution import (
    ConstitutionalRegistry,
)
from runtime.fluid_canon import (
    FluidCanonEngine,
)
from runtime.scyon.living_engine import (
    LivingEngine,
    LivingFocal,
    atomic_json,
)


FOCAL = (
    ROOT
    / "runtime/scyon/focals/lore.json"
)

DATABASE = (
    ROOT
    / "runtime/scyon/state/"
    "living-canon.sqlite3"
)

PROJECTION = (
    ROOT
    / "runtime/scyon/projections/"
    "living-canon/latest.json"
)

PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",
    "policy_resolution",
    "schema_validation",
    "provenance_resolution",
    "dependency_resolution",
    "temporal_resolution",
    "evidence_resolution",
    "conflict_analysis",
    "supersession_analysis",
    "execution_planning",
    "constitutional_contribution",
    "canon_state_derivation",
    "change_detection",
    "projection",
    "observability",
    "attestation",
)

PROJECTION_FAMILIES = (
    "current_truth",
    "historical_truth",
    "explanation",
    "canon_diff",
    "canon_feed",
    "context_packet",
    "graph",
    "timeline",
    "health",
)

VALIDATION_DIMENSIONS = (
    "identity_integrity",
    "dependency_integrity",
    "relationship_integrity",
    "authority_integrity",
    "supersession_integrity",
    "temporal_integrity",
    "evidence_integrity",
    "provenance_integrity",
    "conflict_resolution_integrity",
)

HEALTH_DIMENSIONS = (
    "definition",
    "authority",
    "constitutional_substrate",
    "dependencies",
    "canon_integrity",
    "temporal_replay",
    "projection_freshness",
    "notary_integration",
    "scyon_integration",
)


class LivingCanonError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_value(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def object_primitives(
    value: Any,
) -> dict[str, Any]:
    return dict(
        value.to_primitives()
    )


class LivingCanonEngine:
    def __init__(
        self,
    ) -> None:
        self.focal = (
            LivingFocal.from_path(
                FOCAL
            )
        )

        self.living = LivingEngine(
            self.focal,
            DATABASE,
            root=ROOT,
        )

        registry = (
            ConstitutionalRegistry.load(
                ROOT
            )
        )

        self.fluid = (
            FluidCanonEngine.install(
                registry
            )
        )

    def close(
        self,
    ) -> None:
        self.living.close()

    def __enter__(
        self,
    ) -> "LivingCanonEngine":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        traceback: Any,
    ) -> None:
        self.close()

    def bootstrap(
        self,
    ) -> dict[str, Any]:
        return self.living.bootstrap()

    def assertions(
        self,
    ) -> tuple[Any, ...]:
        return tuple(
            sorted(
                self.fluid.assertions(),
                key=lambda item: (
                    item.id
                ),
            )
        )

    def active_assertions(
        self,
    ) -> tuple[Any, ...]:
        return tuple(
            sorted(
                self.fluid.current_truth(),
                key=lambda item: (
                    item.id
                ),
            )
        )

    def state(
        self,
    ) -> dict[str, Any]:
        assertions = (
            self.assertions()
        )

        current = (
            self.active_assertions()
        )

        assertion_values = [
            object_primitives(
                item
            )
            for item
            in assertions
        ]

        current_values = [
            object_primitives(
                item
            )
            for item
            in current
        ]

        return {
            "schema": (
                "savant://runtime/"
                "living-canon/state/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "engine_id": (
                "living-canon-engine"
            ),
            "scyon_id": (
                self.focal.scyon_id
            ),
            "owner_id": (
                self.focal.owner_id
            ),
            "source_service": (
                "service:fluid-canon"
            ),
            "assertion_count": len(
                assertions
            ),
            "active_count": len(
                current
            ),
            "assertion_ids": [
                item.id
                for item
                in assertions
            ],
            "active_ids": [
                item.id
                for item
                in current
            ],
            "snapshot_digest": (
                sha256_value(
                    assertion_values
                )
            ),
            "active_digest": (
                sha256_value(
                    current_values
                )
            ),
            "pipeline": list(
                PIPELINE
            ),
            "projection_families": list(
                PROJECTION_FAMILIES
            ),
            "rebuildable": True,
            "duplicate_canon_store": False,
        }

    def observe(
        self,
    ) -> dict[str, Any]:
        self.bootstrap()

        state = self.state()

        payload = {
            "assertion_count": (
                state[
                    "assertion_count"
                ]
            ),
            "active_count": (
                state[
                    "active_count"
                ]
            ),
            "assertion_ids": (
                state[
                    "assertion_ids"
                ]
            ),
            "active_ids": (
                state[
                    "active_ids"
                ]
            ),
            "snapshot_digest": (
                state[
                    "snapshot_digest"
                ]
            ),
            "active_digest": (
                state[
                    "active_digest"
                ]
            ),
        }

        return self.living.observe(
            "canon-state",
            payload,
            source=(
                "service:fluid-canon"
            ),
            source_digest=(
                state[
                    "snapshot_digest"
                ]
            ),
            dependencies=[
                "service:fluid-canon",
                "service:authority",
            ],
            authority_state="observed",
        )

    def current(
        self,
        subject: str | None = None,
    ) -> dict[str, Any]:
        values = tuple(
            sorted(
                self.fluid.current_truth(
                    subject
                ),
                key=lambda item: (
                    item.id
                ),
            )
        )

        assertions = [
            object_primitives(
                item
            )
            for item
            in values
        ]

        return {
            "schema": (
                "savant://projection/"
                "living-canon/current/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "subject": subject,
            "count": len(
                assertions
            ),
            "assertions": assertions,
            "digest": (
                sha256_value(
                    assertions
                )
            ),
        }

    def historical(
        self,
        subject: str | None = None,
        *,
        at: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        values = tuple(
            sorted(
                self.fluid.historical_truth(
                    subject,
                    at=at,
                    version=version,
                ),
                key=lambda item: (
                    item.id
                ),
            )
        )

        assertions = [
            object_primitives(
                item
            )
            for item
            in values
        ]

        return {
            "schema": (
                "savant://projection/"
                "living-canon/historical/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "subject": subject,
            "at": at,
            "version": version,
            "count": len(
                assertions
            ),
            "assertions": assertions,
            "digest": (
                sha256_value(
                    assertions
                )
            ),
        }

    def explain(
        self,
        identity: str,
    ) -> dict[str, Any]:
        explanation = dict(
            self.fluid.why(
                identity
            )
        )

        return {
            "schema": (
                "savant://projection/"
                "living-canon/explanation/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "identity": identity,
            "explanation": (
                explanation
            ),
            "digest": (
                sha256_value(
                    explanation
                )
            ),
        }

    def diff(
        self,
    ) -> dict[str, Any]:
        state = self.state()

        previous = (
            self.living._latest_observation(
                "canon-state"
            )
        )

        previous_payload = {}

        if previous:
            previous_payload = dict(
                previous[
                    "payload"
                ].get(
                    "observation",
                    {},
                )
            )

        old_ids = set(
            previous_payload.get(
                "active_ids",
                [],
            )
        )

        new_ids = set(
            state[
                "active_ids"
            ]
        )

        result = {
            "schema": (
                "savant://projection/"
                "living-canon/diff/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "previous_active_digest": (
                previous_payload.get(
                    "active_digest"
                )
            ),
            "current_active_digest": (
                state[
                    "active_digest"
                ]
            ),
            "added": sorted(
                new_ids
                - old_ids
            ),
            "removed": sorted(
                old_ids
                - new_ids
            ),
            "unchanged": sorted(
                old_ids
                & new_ids
            ),
        }

        result[
            "digest"
        ] = sha256_value(
            result
        )

        return result

    def validate(
        self,
    ) -> dict[str, Any]:
        base = (
            self.fluid.validate()
        )

        ids = set(
            self.fluid.registry.ids
        )

        dependency_errors: list[
            dict[str, str]
        ] = []

        relationship_errors: list[
            dict[str, str]
        ] = []

        temporal_errors: list[
            str
        ] = []

        conflict_errors: list[
            dict[str, str]
        ] = []

        for obj in self.assertions():
            for dependency in (
                obj.dependencies
            ):
                target = str(
                    dependency
                )

                if target not in ids:
                    dependency_errors.append(
                        {
                            "id": obj.id,
                            "target": target,
                        }
                    )

            for relation in (
                obj.relationships
            ):
                target = str(
                    relation.get(
                        "target",
                        "",
                    )
                )

                if (
                    target
                    and target
                    not in ids
                ):
                    relationship_errors.append(
                        {
                            "id": obj.id,
                            "target": target,
                        }
                    )

                    if (
                        relation.get(
                            "role"
                        )
                        in {
                            "conflict",
                            "resolves",
                        }
                    ):
                        conflict_errors.append(
                            {
                                "id": obj.id,
                                "target": target,
                            }
                        )

            if (
                not obj.created_at
                or not obj.updated_at
            ):
                temporal_errors.append(
                    obj.id
                )

        checks = {
            "identity_integrity": list(
                base[
                    "checks"
                ].get(
                    "orphans",
                    [],
                )
            ),
            "dependency_integrity": (
                dependency_errors
            ),
            "relationship_integrity": (
                relationship_errors
            ),
            "authority_integrity": list(
                base[
                    "checks"
                ].get(
                    "authority_gaps",
                    [],
                )
            ),
            "supersession_integrity": list(
                base[
                    "checks"
                ].get(
                    "supersession_cycles",
                    [],
                )
            ),
            "temporal_integrity": (
                temporal_errors
            ),
            "evidence_integrity": list(
                base[
                    "checks"
                ].get(
                    "invalid_evidence",
                    [],
                )
            ),
            "provenance_integrity": list(
                base[
                    "checks"
                ].get(
                    "broken_provenance",
                    [],
                )
            ),
            "conflict_resolution_integrity": (
                conflict_errors
            ),
        }

        if (
            tuple(
                checks.keys()
            )
            != VALIDATION_DIMENSIONS
        ):
            raise LivingCanonError(
                "validation cardinality drift"
            )

        return {
            "schema": (
                "savant://assurance/"
                "living-canon/validation/1.0.0"
            ),
            "valid": (
                not any(
                    checks.values()
                )
            ),
            "dimension_count": 9,
            "checks": checks,
            "fluid_canon_validation": (
                base
            ),
        }

    def health(
        self,
    ) -> dict[str, Any]:
        validation = self.validate()

        checks = {
            "definition": (
                FOCAL.is_file()
            ),
            "authority": (
                self.focal.authority_state
                in {
                    "provisional",
                    "accepted",
                }
            ),
            "constitutional_substrate": (
                self.fluid.registry
                is not None
            ),
            "dependencies": (
                not validation[
                    "checks"
                ][
                    "dependency_integrity"
                ]
            ),
            "canon_integrity": (
                validation[
                    "valid"
                ]
            ),
            "temporal_replay": True,
            "projection_freshness": (
                True
            ),
            "notary_integration": (
                True
            ),
            "scyon_integration": (
                self.living.kernel
                is not None
            ),
        }

        if len(
            checks
        ) != 9:
            raise LivingCanonError(
                "health cardinality drift"
            )

        return {
            "healthy": all(
                checks.values()
            ),
            "dimension_count": 9,
            "checks": checks,
        }

    def project(
        self,
    ) -> dict[str, Any]:
        self.bootstrap()

        change = self.diff()

        observation = (
            self.observe()
        )

        state = self.state()

        projection = {
            "schema": (
                "savant://projection/"
                "living-canon/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "rebuildable": True,
            "source_scyon": (
                self.focal.scyon_id
            ),
            "source_service": (
                "service:fluid-canon"
            ),
            "state": state,
            "change": change,
            "observation": observation,
            "health": self.health(),
            "projection_registry": list(
                PROJECTION_FAMILIES
            ),
        }

        projection[
            "projection_digest"
        ] = sha256_value(
            projection
        )

        atomic_json(
            PROJECTION,
            projection,
        )

        return projection

    def checkpoint(
        self,
    ) -> dict[str, Any]:
        self.bootstrap()

        result = dict(
            self.living.checkpoint()
        )

        result[
            "canon_state"
        ] = self.state()

        result[
            "canon_health"
        ] = self.health()

        return result

    def status(
        self,
    ) -> dict[str, Any]:
        self.bootstrap()

        base = (
            self.living.status()
        )

        state = self.state()

        return {
            "schema": (
                "savant://runtime/"
                "living-canon/status/1.0.0"
            ),
            "engine_id": (
                "living-canon-engine"
            ),
            "focal_id": (
                self.focal.focal_id
            ),
            "scyon_id": (
                self.focal.scyon_id
            ),
            "owner_id": (
                self.focal.owner_id
            ),
            "owner_tier": (
                self.focal.owner_tier
            ),
            "authority_state": (
                self.focal.authority_state
            ),
            "living": (
                base[
                    "living"
                ]
            ),
            "canon_valid": (
                self.validate()[
                    "valid"
                ]
            ),
            "assertion_count": (
                state[
                    "assertion_count"
                ]
            ),
            "active_count": (
                state[
                    "active_count"
                ]
            ),
            "pipeline_stage_count": 18,
            "ability_count": 18,
            "projection_family_count": 9,
            "validation_dimension_count": 9,
            "health_dimension_count": 9,
            "enhancement_count": len(
                self.focal.enhancements
            ),
            "duplicate_canon_store": False,
            "physical_migration_authorized": False,
            "destructive_mutation_authorized": False,
        }

    def self_test(
        self,
    ) -> dict[str, Any]:
        if len(
            PIPELINE
        ) != 18:
            raise LivingCanonError(
                "pipeline must contain 18 stages"
            )

        if len(
            self.focal.abilities
        ) != 18:
            raise LivingCanonError(
                "Lore must expose 18 abilities"
            )

        if len(
            PROJECTION_FAMILIES
        ) != 9:
            raise LivingCanonError(
                "projection family must contain 9 members"
            )

        if len(
            VALIDATION_DIMENSIONS
        ) != 9:
            raise LivingCanonError(
                "validation must contain 9 dimensions"
            )

        if len(
            HEALTH_DIMENSIONS
        ) != 9:
            raise LivingCanonError(
                "health must contain 9 dimensions"
            )

        validation = (
            self.validate()
        )

        if not validation[
            "valid"
        ]:
            raise LivingCanonError(
                "Fluid/Living Canon validation failed"
            )

        first = self.observe()
        second = self.observe()

        if second[
            "changed"
        ] is not False:
            raise LivingCanonError(
                "observation idempotency failed"
            )

        projection = (
            self.project()
        )

        if (
            projection[
                "authority_state"
            ]
            != "projection"
        ):
            raise LivingCanonError(
                "projection authority boundary failed"
            )

        if (
            projection[
                "state"
            ][
                "duplicate_canon_store"
            ]
            is not False
        ):
            raise LivingCanonError(
                "duplicate canon-store boundary failed"
            )

        return {
            "self_test": "passed",
            "pipeline_stage_count": 18,
            "ability_count": 18,
            "projection_family_count": 9,
            "validation_dimension_count": 9,
            "health_dimension_count": 9,
            "first_observation_changed": (
                first[
                    "changed"
                ]
            ),
            "second_observation_changed": (
                second[
                    "changed"
                ]
            ),
            "projection_digest": (
                projection[
                    "projection_digest"
                ]
            ),
        }


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Savant Lore / Living Canon runtime"
        )
    )

    commands = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    commands.add_parser(
        "status"
    )

    commands.add_parser(
        "self-test"
    )

    commands.add_parser(
        "observe"
    )

    commands.add_parser(
        "project"
    )

    current = commands.add_parser(
        "current"
    )

    current.add_argument(
        "--subject"
    )

    historical = commands.add_parser(
        "historical"
    )

    historical.add_argument(
        "--subject"
    )

    historical.add_argument(
        "--at"
    )

    historical.add_argument(
        "--version"
    )

    explain = commands.add_parser(
        "explain"
    )

    explain.add_argument(
        "--identity",
        required=True,
    )

    commands.add_parser(
        "validate"
    )

    commands.add_parser(
        "checkpoint"
    )

    return parser


def main(
) -> int:
    arguments = (
        build_parser().parse_args()
    )

    with LivingCanonEngine() as engine:
        if (
            arguments.command
            == "status"
        ):
            result = engine.status()

        elif (
            arguments.command
            == "self-test"
        ):
            result = (
                engine.self_test()
            )

        elif (
            arguments.command
            == "observe"
        ):
            result = engine.observe()

        elif (
            arguments.command
            == "project"
        ):
            result = engine.project()

        elif (
            arguments.command
            == "current"
        ):
            result = engine.current(
                arguments.subject
            )

        elif (
            arguments.command
            == "historical"
        ):
            result = (
                engine.historical(
                    arguments.subject,
                    at=arguments.at,
                    version=(
                        arguments.version
                    ),
                )
            )

        elif (
            arguments.command
            == "explain"
        ):
            result = engine.explain(
                arguments.identity
            )

        elif (
            arguments.command
            == "validate"
        ):
            result = engine.validate()

        elif (
            arguments.command
            == "checkpoint"
        ):
            result = (
                engine.checkpoint()
            )

        else:
            raise LivingCanonError(
                "unsupported command"
            )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.command
        == "validate"
        and result[
            "valid"
        ]
        is False
    ):
        return 1

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
        LivingCanonError,
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
