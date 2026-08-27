#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/spyral/instances/system.json"
)


SPYRAL_PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",

    "baseline_resolution",
    "target_resolution",
    "dependency_resolution",

    "compatibility_analysis",
    "impact_analysis",
    "precondition_analysis",

    "transition_planning",
    "migration_planning",
    "supersession_planning",

    "recovery_planning",
    "replay_analysis",
    "determinism_analysis",

    "projection",
    "validation",
    "attestation",
)


SPYRAL_ABILITIES = (
    "transition_identity",
    "baseline_capture",
    "target_capture",

    "compatibility_analysis",
    "dependency_analysis",
    "impact_analysis",

    "precondition_analysis",
    "transition_planning",
    "migration_planning",

    "supersession_planning",
    "lineage_preservation",
    "provenance_preservation",

    "rollback_planning",
    "recovery_validation",
    "replay_validation",

    "transition_explanation",
    "transition_receipt",
    "evolution_projection",
)


SPYRAL_HEALTH_DIMENSIONS = (
    "instance_integrity",
    "identity_preservation",
    "lineage_preservation",

    "provenance_preservation",
    "compatibility_integrity",
    "recovery_integrity",

    "replay_integrity",
    "mutation_boundary",
    "coda_integration",
)


SPYRAL_VALIDATION_DIMENSIONS = (
    "identity",
    "authority",
    "baseline",

    "target",
    "compatibility",
    "dependencies",

    "recovery",
    "replay",
    "integration",
)


SPYRAL_PROJECTIONS = (
    "transition_plan",
    "migration_manifest",
    "compatibility_report",

    "impact_report",
    "supersession_map",
    "lineage_projection",

    "recovery_plan",
    "replay_report",
    "evolution_health",
)


COMPATIBILITY_STATES = (
    "compatible",
    "conditionally-compatible",
    "breaking",
    "unknown",
)


class SpyralError(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_version(
    value: Any,
) -> tuple[int, ...] | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    match = re.fullmatch(
        r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?",
        text,
    )

    if match is None:
        return None

    return tuple(
        int(part or 0)
        for part in match.groups()
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Compatibility:
    state: str
    reasons: tuple[str, ...]
    source_version: str | None = None
    target_version: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.state
            not in COMPATIBILITY_STATES
        ):
            raise SpyralError(
                "invalid compatibility state: "
                + self.state
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "state": self.state,
            "reasons": list(
                self.reasons
            ),
            "source_version":
                self.source_version,
            "target_version":
                self.target_version,
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class Transition:
    transition_id: str
    subject_id: str
    baseline: Mapping[str, Any]
    target: Mapping[str, Any]
    dependencies: tuple[str, ...]
    compatibility: Compatibility
    migration_steps: tuple[
        Mapping[str, Any],
        ...
    ]
    recovery_steps: tuple[
        Mapping[str, Any],
        ...
    ]
    supersedes: str | None
    lineage: Any
    provenance: Any

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "transition_id":
                self.transition_id,
            "subject_id":
                self.subject_id,
            "baseline":
                dict(self.baseline),
            "target":
                dict(self.target),
            "dependencies":
                list(self.dependencies),
            "compatibility":
                self.compatibility
                .projection(),
            "migration_steps": [
                dict(step)
                for step
                in self.migration_steps
            ],
            "recovery_steps": [
                dict(step)
                for step
                in self.recovery_steps
            ],
            "supersedes":
                self.supersedes,
            "lineage":
                self.lineage,
            "provenance":
                self.provenance,
            "authoritative":
                False,
            "mutation_performed":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class Spyral:
    schema = (
        "savant://runtime/"
        "spyral/1.0.0"
    )

    substrate_id = (
        "living:spyral"
    )

    def __init__(
        self,
        instance_path:
            Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise SpyralError(
                "instance path must "
                "be absolute"
            )

        self.instance_path = (
            instance_path.resolve()
        )

        self.instance = (
            self._load_json(
                self.instance_path
            )
        )

        self._validate_instance()

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise SpyralError(
                f"missing file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise SpyralError(
                f"invalid JSON: {path}: "
                f"{exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise SpyralError(
                f"invalid object: {path}"
            )

        return payload

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get(
                "substrate"
            )
            != "spyral"
        ):
            raise SpyralError(
                "invalid Spyral substrate"
            )

        if (
            self.instance.get(
                "authoritative"
            )
            is not False
        ):
            raise SpyralError(
                "Spyral must remain "
                "non-authoritative"
            )

        if (
            self.instance.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise SpyralError(
                "Spyral mutation must "
                "remain disabled"
            )

        if (
            self.instance.get(
                "migration_execution_authorized"
            )
            is not False
        ):
            raise SpyralError(
                "Spyral plans migration; "
                "it does not execute mutation"
            )

        policy = self.instance.get(
            "policy",
            {},
        )

        if len(policy) != 9:
            raise SpyralError(
                "Spyral policy must "
                "contain 9 controls"
            )

        if not all(
            isinstance(value, bool)
            for value
            in policy.values()
        ):
            raise SpyralError(
                "Spyral policy controls "
                "must be boolean"
            )

        groups = self.instance.get(
            "enhancement_groups",
            {},
        )

        if len(groups) != 9:
            raise SpyralError(
                "Spyral requires "
                "9 enhancement groups"
            )

        for name, values in (
            groups.items()
        ):
            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values) != 3
                or not all(
                    isinstance(
                        value,
                        str,
                    )
                    and value.strip()
                    for value in values
                )
            ):
                raise SpyralError(
                    f"{name} must contain "
                    "exactly 3 enhancements"
                )

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.instance[
                "enhancement_groups"
            ].values()
        )

    def compatibility(
        self,
        baseline:
            Mapping[str, Any],
        target:
            Mapping[str, Any],
    ) -> Compatibility:
        reasons: list[str] = []

        baseline_id = (
            baseline.get("id")
            or baseline.get(
                "identity"
            )
        )

        target_id = (
            target.get("id")
            or target.get(
                "identity"
            )
        )

        if (
            self.instance[
                "policy"
            ][
                "preserve_identity"
            ]
            and baseline_id
            and target_id
            and baseline_id
            != target_id
        ):
            return Compatibility(
                state="breaking",
                reasons=(
                    "semantic identity changes",
                ),
                source_version=str(
                    baseline.get(
                        "version"
                    )
                )
                if baseline.get(
                    "version"
                )
                is not None
                else None,
                target_version=str(
                    target.get(
                        "version"
                    )
                )
                if target.get(
                    "version"
                )
                is not None
                else None,
            )

        before = normalize_version(
            baseline.get(
                "version"
            )
        )

        after = normalize_version(
            target.get(
                "version"
            )
        )

        if (
            before is None
            or after is None
        ):
            reasons.append(
                "version compatibility "
                "cannot be fully established"
            )

            state = "unknown"

        elif after < before:
            reasons.append(
                "target version precedes "
                "baseline version"
            )

            state = (
                "conditionally-compatible"
            )

        elif (
            after[0]
            > before[0]
        ):
            reasons.append(
                "major version changes"
            )

            state = (
                "conditionally-compatible"
            )

        else:
            reasons.append(
                "identity is preserved "
                "and version transition "
                "does not cross a major boundary"
            )

            state = "compatible"

        baseline_schema = (
            baseline.get(
                "schema"
            )
        )

        target_schema = (
            target.get(
                "schema"
            )
        )

        if (
            baseline_schema
            and target_schema
            and baseline_schema
            != target_schema
        ):
            reasons.append(
                "schema identity changes"
            )

            if state == "compatible":
                state = (
                    "conditionally-compatible"
                )

        return Compatibility(
            state=state,
            reasons=tuple(
                reasons
            ),
            source_version=(
                str(
                    baseline.get(
                        "version"
                    )
                )
                if baseline.get(
                    "version"
                )
                is not None
                else None
            ),
            target_version=(
                str(
                    target.get(
                        "version"
                    )
                )
                if target.get(
                    "version"
                )
                is not None
                else None
            ),
        )

    @staticmethod
    def _normalize_steps(
        values:
            Iterable[
                Mapping[str, Any]
            ],
    ) -> tuple[
        Mapping[str, Any],
        ...,
    ]:
        result: list[
            Mapping[str, Any]
        ] = []

        for ordinal, value in (
            enumerate(
                values,
                start=1,
            )
        ):
            if not isinstance(
                value,
                Mapping,
            ):
                raise SpyralError(
                    "transition steps "
                    "must be mappings"
                )

            step = dict(
                value
            )

            step.setdefault(
                "ordinal",
                ordinal,
            )

            step.setdefault(
                "mutation_authorized",
                False,
            )

            result.append(
                step
            )

        return tuple(
            result
        )

    def plan(
        self,
        *,
        subject_id: str,
        baseline:
            Mapping[str, Any],
        target:
            Mapping[str, Any],
        dependencies:
            Iterable[str] = (),
        migration_steps:
            Iterable[
                Mapping[str, Any]
            ] = (),
        recovery_steps:
            Iterable[
                Mapping[str, Any]
            ] = (),
        supersedes:
            str | None = None,
        lineage: Any = None,
        provenance: Any = None,
    ) -> Transition:
        subject_id = (
            subject_id.strip()
        )

        if not subject_id:
            raise SpyralError(
                "subject_id is required"
            )

        compatibility = (
            self.compatibility(
                baseline,
                target,
            )
        )

        migrations = (
            self._normalize_steps(
                migration_steps
            )
        )

        recovery = (
            self._normalize_steps(
                recovery_steps
            )
        )

        if (
            migrations
            and self.instance[
                "policy"
            ][
                "require_recovery_path"
            ]
            and not recovery
        ):
            raise SpyralError(
                "migration plan requires "
                "a recovery path"
            )

        dependency_values = tuple(
            sorted(
                {
                    str(value).strip()
                    for value
                    in dependencies
                    if str(value)
                    .strip()
                }
            )
        )

        identity_material = {
            "subject_id":
                subject_id,
            "baseline":
                dict(baseline),
            "target":
                dict(target),
            "dependencies":
                dependency_values,
            "migration_steps": [
                dict(value)
                for value
                in migrations
            ],
            "recovery_steps": [
                dict(value)
                for value
                in recovery
            ],
            "supersedes":
                supersedes,
            "lineage":
                lineage,
            "provenance":
                provenance,
        }

        transition_id = (
            "transition:"
            + digest(
                identity_material
            )[:24]
        )

        return Transition(
            transition_id=(
                transition_id
            ),
            subject_id=subject_id,
            baseline=dict(
                baseline
            ),
            target=dict(
                target
            ),
            dependencies=(
                dependency_values
            ),
            compatibility=(
                compatibility
            ),
            migration_steps=(
                migrations
            ),
            recovery_steps=(
                recovery
            ),
            supersedes=(
                supersedes
            ),
            lineage=lineage,
            provenance=provenance,
        )

    def migration_manifest(
        self,
        transition: Transition,
    ) -> dict[str, Any]:
        projection = (
            transition.projection()
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "spyral/migration-manifest/"
                "1.0.0"
            ),
            "instance_id": (
                self.instance[
                    "instance_id"
                ]
            ),
            "transition_id": (
                transition.transition_id
            ),
            "subject_id": (
                transition.subject_id
            ),
            "compatibility": (
                transition
                .compatibility
                .projection()
            ),
            "dependencies": list(
                transition.dependencies
            ),
            "steps": [
                dict(value)
                for value
                in transition
                .migration_steps
            ],
            "recovery": [
                dict(value)
                for value
                in transition
                .recovery_steps
            ],
            "source_digest": digest(
                transition.baseline
            ),
            "target_digest": digest(
                transition.target
            ),
            "transition_digest": (
                projection[
                    "digest"
                ]
            ),
            "manifest_is_projection":
                True,
            "mutation_authorized":
                False,
            "execution_authorized":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def recovery_plan(
        self,
        transition: Transition,
    ) -> dict[str, Any]:
        complete = (
            not transition
            .migration_steps
            or bool(
                transition
                .recovery_steps
            )
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "spyral/recovery/1.0.0"
            ),
            "transition_id": (
                transition.transition_id
            ),
            "steps": [
                dict(value)
                for value
                in transition
                .recovery_steps
            ],
            "complete": complete,
            "authoritative": False,
            "execution_authorized":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def replay_fingerprint(
        self,
        transition: Transition,
    ) -> str:
        return digest(
            {
                "transition":
                    transition
                    .projection(),
                "instance":
                    self.instance[
                        "instance_id"
                    ],
                "schema":
                    self.schema,
            }
        )

    def compare_replay(
        self,
        left: Transition,
        right: Transition,
    ) -> dict[str, Any]:
        left_digest = (
            self.replay_fingerprint(
                left
            )
        )

        right_digest = (
            self.replay_fingerprint(
                right
            )
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "spyral/replay/1.0.0"
            ),
            "left":
                left_digest,
            "right":
                right_digest,
            "diverged": (
                left_digest
                != right_digest
            ),
            "blocking": (
                left_digest
                != right_digest
            ),
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def impact(
        self,
        transition: Transition,
    ) -> dict[str, Any]:
        before = dict(
            transition.baseline
        )

        after = dict(
            transition.target
        )

        keys = sorted(
            set(before)
            | set(after)
        )

        changes = []

        for key in keys:
            left = before.get(
                key
            )

            right = after.get(
                key
            )

            if left == right:
                continue

            changes.append(
                {
                    "field": key,
                    "before": left,
                    "after": right,
                }
            )

        payload = {
            "schema": (
                "savant://runtime/"
                "spyral/impact/1.0.0"
            ),
            "transition_id":
                transition.transition_id,
            "change_count":
                len(changes),
            "changes":
                changes,
            "dependencies":
                list(
                    transition
                    .dependencies
                ),
            "compatibility":
                transition
                .compatibility
                .projection(),
            "authoritative":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        dimensions = {
            "instance_integrity":
                True,

            "identity_preservation": (
                self.instance[
                    "policy"
                ][
                    "preserve_identity"
                ]
            ),

            "lineage_preservation": (
                self.instance[
                    "policy"
                ][
                    "preserve_lineage"
                ]
            ),

            "provenance_preservation": (
                self.instance[
                    "policy"
                ][
                    "preserve_provenance"
                ]
            ),

            "compatibility_integrity": (
                self.instance[
                    "policy"
                ][
                    "require_compatibility_analysis"
                ]
            ),

            "recovery_integrity": (
                self.instance[
                    "policy"
                ][
                    "require_recovery_path"
                ]
            ),

            "replay_integrity":
                True,

            "mutation_boundary": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
                and self.instance[
                    "migration_execution_authorized"
                ]
                is False
            ),

            "coda_integration": (
                self.instance[
                    "owner"
                ]
                == "exile:coda"
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "spyral/health/1.0.0"
            ),
            "dimensions": {
                name: {
                    "healthy":
                        bool(value)
                }
                for name, value
                in dimensions.items()
            },
            "healthy": all(
                dimensions.values()
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def validate(
        self,
    ) -> dict[str, Any]:
        checks = {
            "abilities": (
                len(
                    SPYRAL_ABILITIES
                )
                == 18
            ),

            "pipeline": (
                len(
                    SPYRAL_PIPELINE
                )
                == 18
            ),

            "health_dimensions": (
                len(
                    SPYRAL_HEALTH_DIMENSIONS
                )
                == 9
            ),

            "validation_dimensions": (
                len(
                    SPYRAL_VALIDATION_DIMENSIONS
                )
                == 9
            ),

            "projections": (
                len(
                    SPYRAL_PROJECTIONS
                )
                == 9
            ),

            "enhancements": (
                self.enhancement_count
                == 27
            ),

            "non_authoritative": (
                self.instance[
                    "authoritative"
                ]
                is False
            ),

            "mutation_forbidden": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
            ),

            "migration_execution_forbidden": (
                self.instance[
                    "migration_execution_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "spyral/1.0.0"
            ),
            "valid": all(
                checks.values()
            ),
            "checks": checks,
            "ability_count": 18,
            "pipeline_stage_count": 18,
            "health_dimension_count": 9,
            "validation_dimension_count": 9,
            "projection_count": 9,
            "enhancement_count": 27,
            "authoritative": False,
            "mutation_authorized": False,
            "migration_execution_authorized":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema":
                self.schema,

            "substrate_id":
                self.substrate_id,

            "name":
                "Spyral",

            "role": (
                "living evolution "
                "substrate"
            ),

            "owner": (
                self.instance[
                    "owner"
                ]
            ),

            "instance":
                self.instance,

            "abilities":
                list(
                    SPYRAL_ABILITIES
                ),

            "pipeline":
                list(
                    SPYRAL_PIPELINE
                ),

            "health_dimensions":
                list(
                    SPYRAL_HEALTH_DIMENSIONS
                ),

            "validation_dimensions":
                list(
                    SPYRAL_VALIDATION_DIMENSIONS
                ),

            "projections":
                list(
                    SPYRAL_PROJECTIONS
                ),

            "enhancement_count":
                self.enhancement_count,

            "authoritative":
                False,

            "mutation_authorized":
                False,

            "migration_execution_authorized":
                False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload
