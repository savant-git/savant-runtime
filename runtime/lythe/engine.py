#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/lythe/instances/filament.json"
)


LYTHE_PIPELINE = (
    "admission",
    "identity_resolution",
    "authority_resolution",

    "source_resolution",
    "dependency_resolution",
    "specification_resolution",

    "path_resolution",
    "field_selection",
    "transformation_resolution",

    "derivation",
    "normalization",
    "ordering",

    "fingerprinting",
    "freshness_analysis",
    "rebuild_analysis",

    "projection",
    "validation",
    "receipt_generation",
)


LYTHE_ABILITIES = (
    "projection_identity",
    "specification_identity",
    "source_fingerprinting",

    "dependency_fingerprinting",
    "path_extraction",
    "field_selection",

    "field_renaming",
    "constant_injection",
    "value_normalization",

    "stable_ordering",
    "deterministic_derivation",
    "projection_fingerprinting",

    "freshness_analysis",
    "staleness_detection",
    "rebuild_eligibility",

    "derivation_explanation",
    "projection_receipt",
    "determinism_verification",
)


LYTHE_HEALTH_DIMENSIONS = (
    "instance_integrity",
    "source_integrity",
    "dependency_integrity",

    "specification_integrity",
    "determinism_integrity",
    "freshness_integrity",

    "rebuildability_integrity",
    "authority_boundary",
    "filament_integration",
)


LYTHE_VALIDATION_DIMENSIONS = (
    "identity",
    "source",
    "dependencies",

    "specification",
    "paths",
    "transforms",

    "determinism",
    "freshness",
    "integration",
)


LYTHE_PROJECTIONS = (
    "projection_spec",
    "derived_view",
    "source_fingerprint",

    "dependency_fingerprint",
    "freshness_report",
    "staleness_report",

    "rebuild_report",
    "derivation_receipt",
    "derivation_health",
)


class LytheError(RuntimeError):
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
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def resolve_path(
    value: Any,
    path: str,
) -> Any:
    if path in ("", "."):
        return value

    current = value

    for segment in path.split("."):
        if not segment:
            continue

        if isinstance(current, Mapping):
            if segment not in current:
                raise LytheError(
                    f"missing mapping path: {path}"
                )

            current = current[segment]
            continue

        if isinstance(
            current,
            Sequence,
        ) and not isinstance(
            current,
            (str, bytes, bytearray),
        ):
            try:
                index = int(segment)
            except ValueError as exc:
                raise LytheError(
                    f"non-numeric sequence path: {path}"
                ) from exc

            try:
                current = current[index]
            except IndexError as exc:
                raise LytheError(
                    f"sequence path out of range: {path}"
                ) from exc

            continue

        raise LytheError(
            f"path cannot traverse value: {path}"
        )

    return current


def normalize_value(
    value: Any,
) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): normalize_value(item)
            for key, item
            in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [
            normalize_value(item)
            for item in value
        ]

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class DerivationSpec:
    spec_id: str
    source_id: str
    fields: Mapping[str, str]
    constants: Mapping[str, Any]
    metadata: Mapping[str, Any]

    def __post_init__(
        self,
    ) -> None:
        if not self.spec_id.strip():
            raise LytheError(
                "spec_id is required"
            )

        if not self.source_id.strip():
            raise LytheError(
                "source_id is required"
            )

        if not self.fields:
            raise LytheError(
                "at least one field mapping is required"
            )

        for target, source in self.fields.items():
            if (
                not str(target).strip()
                or not str(source).strip()
            ):
                raise LytheError(
                    "field mappings must be non-empty"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "spec_id": self.spec_id,
            "source_id": self.source_id,
            "fields": dict(self.fields),
            "constants": dict(self.constants),
            "metadata": dict(self.metadata),
            "authoritative": False,
        }

        payload["digest"] = digest(payload)

        return payload


class Lythe:
    schema = "savant://runtime/lythe/1.0.0"
    substrate_id = "living:lythe"

    def __init__(
        self,
        instance_path: Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise LytheError(
                "instance path must be absolute"
            )

        self.instance_path = (
            instance_path.resolve()
        )

        self.instance = self._load_json(
            self.instance_path
        )

        self._validate_instance()

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise LytheError(
                f"missing file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise LytheError(
                f"invalid JSON: {path}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise LytheError(
                f"invalid object: {path}"
            )

        return payload

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get("substrate")
            != "lythe"
        ):
            raise LytheError(
                "invalid Lythe substrate"
            )

        if (
            self.instance.get("authoritative")
            is not False
        ):
            raise LytheError(
                "Lythe projections must remain "
                "non-authoritative"
            )

        if (
            self.instance.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise LytheError(
                "Lythe mutation must remain disabled"
            )

        if (
            self.instance.get(
                "projection_execution_authorized"
            )
            is not False
        ):
            raise LytheError(
                "Filament owns projection execution"
            )

        policy = self.instance.get(
            "policy",
            {},
        )

        if len(policy) != 9:
            raise LytheError(
                "Lythe policy must contain 9 controls"
            )

        if not all(
            isinstance(value, bool)
            for value in policy.values()
        ):
            raise LytheError(
                "Lythe policy controls must be boolean"
            )

        groups = self.instance.get(
            "enhancement_groups",
            {},
        )

        if len(groups) != 9:
            raise LytheError(
                "Lythe requires 9 enhancement groups"
            )

        for name, values in groups.items():
            if (
                not isinstance(values, list)
                or len(values) != 3
                or not all(
                    isinstance(value, str)
                    and value.strip()
                    for value in values
                )
            ):
                raise LytheError(
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

    def derive(
        self,
        source: Mapping[str, Any],
        spec: DerivationSpec,
        *,
        dependencies: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        source_before = digest(source)

        result: dict[str, Any] = {}

        provenance_paths: dict[
            str,
            str,
        ] = {}

        for target_name, source_path in sorted(
            spec.fields.items()
        ):
            result[
                target_name
            ] = normalize_value(
                resolve_path(
                    source,
                    source_path,
                )
            )

            provenance_paths[
                target_name
            ] = source_path

        for name, value in sorted(
            spec.constants.items()
        ):
            if name in result:
                raise LytheError(
                    "constant collides with "
                    f"derived field: {name}"
                )

            result[name] = normalize_value(
                value
            )

        normalized = normalize_value(
            result
        )

        source_after = digest(source)

        if source_before != source_after:
            raise LytheError(
                "source mutation detected"
            )

        dependency_payload = (
            normalize_value(
                dependencies or {}
            )
        )

        source_digest = digest(source)
        dependency_digest = digest(
            dependency_payload
        )
        spec_digest = digest(
            spec.projection()
        )

        projection_material = {
            "spec_id": spec.spec_id,
            "source_id": spec.source_id,
            "source_digest": source_digest,
            "dependency_digest": dependency_digest,
            "spec_digest": spec_digest,
            "value": normalized,
        }

        projection_id = (
            "projection:"
            + digest(
                projection_material
            )[:24]
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/derived-view/1.0.0"
            ),
            "projection_id": projection_id,
            "spec_id": spec.spec_id,
            "source_id": spec.source_id,
            "source_digest": source_digest,
            "dependency_digest": dependency_digest,
            "spec_digest": spec_digest,
            "value": normalized,
            "field_provenance": provenance_paths,
            "metadata": dict(spec.metadata),
            "authoritative": False,
            "rebuildable": True,
            "mutation_performed": False,
            "execution_authorized": False,
        }

        payload["projection_digest"] = digest(
            payload
        )

        return payload

    def freshness(
        self,
        projection: Mapping[str, Any],
        source: Mapping[str, Any],
        *,
        dependencies: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        current_source_digest = digest(
            source
        )

        current_dependency_digest = digest(
            normalize_value(
                dependencies or {}
            )
        )

        source_match = (
            projection.get(
                "source_digest"
            )
            == current_source_digest
        )

        dependency_match = (
            projection.get(
                "dependency_digest"
            )
            == current_dependency_digest
        )

        fresh = (
            source_match
            and dependency_match
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/freshness/1.0.0"
            ),
            "projection_id": projection.get(
                "projection_id"
            ),
            "fresh": fresh,
            "stale": not fresh,
            "source_match": source_match,
            "dependency_match": dependency_match,
            "current_source_digest": (
                current_source_digest
            ),
            "current_dependency_digest": (
                current_dependency_digest
            ),
            "authoritative": False,
        }

        payload["digest"] = digest(payload)

        return payload

    def rebuild_report(
        self,
        projection: Mapping[str, Any],
        source: Mapping[str, Any],
        *,
        dependencies: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        freshness = self.freshness(
            projection,
            source,
            dependencies=dependencies,
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/rebuild/1.0.0"
            ),
            "projection_id": projection.get(
                "projection_id"
            ),
            "rebuild_required": (
                freshness["stale"]
            ),
            "rebuild_allowed": True,
            "projection_disposable": True,
            "source_authority_preserved": True,
            "execution_owner": "exile:filament",
            "execution_authorized_here": False,
            "freshness": freshness,
            "authoritative": False,
        }

        payload["digest"] = digest(payload)

        return payload

    def verify_determinism(
        self,
        source: Mapping[str, Any],
        spec: DerivationSpec,
        *,
        dependencies: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        first = self.derive(
            source,
            spec,
            dependencies=dependencies,
        )

        second = self.derive(
            source,
            spec,
            dependencies=dependencies,
        )

        equivalent = (
            first["projection_digest"]
            == second["projection_digest"]
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/determinism/1.0.0"
            ),
            "first_digest": (
                first["projection_digest"]
            ),
            "second_digest": (
                second["projection_digest"]
            ),
            "deterministic": equivalent,
            "authoritative": False,
        }

        payload["digest"] = digest(payload)

        return payload

    def receipt(
        self,
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/receipt/1.0.0"
            ),
            "projection_id": projection.get(
                "projection_id"
            ),
            "spec_id": projection.get(
                "spec_id"
            ),
            "source_id": projection.get(
                "source_id"
            ),
            "source_digest": projection.get(
                "source_digest"
            ),
            "dependency_digest": (
                projection.get(
                    "dependency_digest"
                )
            ),
            "projection_digest": (
                projection.get(
                    "projection_digest"
                )
            ),
            "rebuildable": True,
            "authoritative": False,
            "execution_owner": "exile:filament",
        }

        payload["digest"] = digest(payload)

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        policy = self.instance["policy"]

        dimensions = {
            "instance_integrity": True,
            "source_integrity": (
                policy[
                    "source_mutation_forbidden"
                ]
            ),
            "dependency_integrity": (
                policy[
                    "dependency_sensitive"
                ]
            ),
            "specification_integrity": True,
            "determinism_integrity": (
                policy["deterministic"]
            ),
            "freshness_integrity": (
                policy[
                    "freshness_sensitive"
                ]
            ),
            "rebuildability_integrity": (
                policy["rebuildable"]
            ),
            "authority_boundary": (
                self.instance[
                    "authoritative"
                ]
                is False
                and self.instance[
                    "mutation_authorized"
                ]
                is False
            ),
            "filament_integration": (
                self.instance["owner"]
                == "exile:filament"
                and self.instance[
                    "projection_execution_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "lythe/health/1.0.0"
            ),
            "dimensions": {
                name: {
                    "healthy": bool(value)
                }
                for name, value
                in dimensions.items()
            },
            "healthy": all(
                dimensions.values()
            ),
        }

        payload["digest"] = digest(payload)

        return payload

    def validate(
        self,
    ) -> dict[str, Any]:
        checks = {
            "abilities": (
                len(LYTHE_ABILITIES) == 18
            ),
            "pipeline": (
                len(LYTHE_PIPELINE) == 18
            ),
            "health_dimensions": (
                len(
                    LYTHE_HEALTH_DIMENSIONS
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    LYTHE_VALIDATION_DIMENSIONS
                )
                == 9
            ),
            "projections": (
                len(LYTHE_PROJECTIONS) == 9
            ),
            "enhancements": (
                self.enhancement_count == 27
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
            "execution_boundary": (
                self.instance[
                    "projection_execution_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "lythe/1.0.0"
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
            "projection_execution_authorized": False,
            "projection_execution_owner": "exile:filament",
        }

        payload["digest"] = digest(payload)

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "substrate_id": self.substrate_id,
            "name": "Lythe",
            "role": (
                "living deterministic "
                "derivation substrate"
            ),
            "owner": self.instance["owner"],
            "instance": self.instance,
            "abilities": list(
                LYTHE_ABILITIES
            ),
            "pipeline": list(
                LYTHE_PIPELINE
            ),
            "health_dimensions": list(
                LYTHE_HEALTH_DIMENSIONS
            ),
            "validation_dimensions": list(
                LYTHE_VALIDATION_DIMENSIONS
            ),
            "projections": list(
                LYTHE_PROJECTIONS
            ),
            "enhancement_count": (
                self.enhancement_count
            ),
            "authoritative": False,
            "mutation_authorized": False,
            "projection_execution_authorized": False,
            "projection_execution_owner": "exile:filament",
        }

        payload["digest"] = digest(payload)

        return payload
