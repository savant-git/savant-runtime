#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/thryce/instances/notary.json"
)


THRYCE_PIPELINE = (
    "admission",
    "identity_resolution",
    "policy_resolution",

    "baseline_resolution",
    "dependency_resolution",
    "invariant_resolution",

    "syntax_evaluation",
    "schema_evaluation",
    "policy_evaluation",

    "property_evaluation",
    "graph_evaluation",
    "integration_evaluation",

    "replay_evaluation",
    "regression_evaluation",
    "health_derivation",

    "evidence_projection",
    "observability",
    "receipt_generation",
)


THRYCE_ABILITIES = (
    "invariant_registration",
    "invariant_evaluation",
    "invariant_explanation",

    "validation_execution",
    "batch_validation",
    "validation_composition",

    "baseline_capture",
    "regression_detection",
    "regression_classification",

    "dependency_validation",
    "integration_validation",
    "replay_validation",

    "health_derivation",
    "health_comparison",
    "unknown_preservation",

    "evidence_candidate_projection",
    "assurance_explanation",
    "assurance_receipt",
)


THRYCE_HEALTH_DIMENSIONS = (
    "definition",
    "invariants",
    "validation",

    "dependencies",
    "integration",
    "replay",

    "regression",
    "evidence_boundary",
    "notary_integration",
)


THRYCE_VALIDATION_DIMENSIONS = (
    "syntax",
    "type",
    "schema",

    "policy",
    "property",
    "graph",

    "integration",
    "replay",
    "regression",
)


THRYCE_PROJECTIONS = (
    "validation_result",
    "invariant_result",
    "health_report",

    "regression_report",
    "dependency_report",
    "integration_report",

    "replay_report",
    "evidence_candidate",
    "assurance_receipt",
)


VALID_STATUSES = (
    "passed",
    "failed",
    "unknown",
    "skipped",
)


class ThryceError(RuntimeError):
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


@dataclass(
    frozen=True,
    slots=True,
)
class AssuranceResult:
    check_id: str
    dimension: str
    status: str
    message: str
    observed: Any = None
    expected: Any = None
    provenance: Any = None

    def projection(
        self,
    ) -> dict[str, Any]:
        if self.status not in VALID_STATUSES:
            raise ThryceError(
                f"invalid assurance status: {self.status}"
            )

        payload = {
            "check_id": self.check_id,
            "dimension": self.dimension,
            "status": self.status,
            "message": self.message,
            "observed": self.observed,
            "expected": self.expected,
            "provenance": self.provenance,
            "authoritative": False,
        }

        payload["digest"] = digest(payload)

        return payload


CheckFunction = Callable[
    [Any],
    AssuranceResult,
]


@dataclass(
    frozen=True,
    slots=True,
)
class AssuranceCheck:
    check_id: str
    dimension: str
    evaluator: CheckFunction

    def run(
        self,
        subject: Any,
    ) -> AssuranceResult:
        result = self.evaluator(
            subject
        )

        if not isinstance(
            result,
            AssuranceResult,
        ):
            raise ThryceError(
                f"{self.check_id} returned "
                "an invalid result type"
            )

        if (
            result.check_id
            != self.check_id
        ):
            raise ThryceError(
                f"{self.check_id} result "
                "identity mismatch"
            )

        if (
            result.dimension
            != self.dimension
        ):
            raise ThryceError(
                f"{self.check_id} dimension "
                "mismatch"
            )

        return result


class Thryce:
    schema = (
        "savant://runtime/"
        "thryce/1.0.0"
    )

    substrate_id = (
        "living:thryce"
    )

    def __init__(
        self,
        instance_path:
            Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise ThryceError(
                "instance path must be absolute"
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

        self._checks: dict[
            str,
            AssuranceCheck,
        ] = {}

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise ThryceError(
                f"missing file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ThryceError(
                f"invalid JSON: {path}: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise ThryceError(
                f"invalid object: {path}"
            )

        return payload

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get("substrate")
            != "thryce"
        ):
            raise ThryceError(
                "invalid Thryce substrate"
            )

        if (
            self.instance.get(
                "authoritative"
            )
            is not False
        ):
            raise ThryceError(
                "Thryce must remain "
                "non-authoritative"
            )

        if (
            self.instance.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise ThryceError(
                "Thryce mutation must remain disabled"
            )

        if (
            self.instance.get(
                "attestation_authorized"
            )
            is not False
        ):
            raise ThryceError(
                "Notary owns attestation"
            )

        if (
            self.instance.get(
                "evidence_admission_authorized"
            )
            is not False
        ):
            raise ThryceError(
                "Notary owns evidence admission"
            )

        policy = self.instance.get(
            "policy",
            {},
        )

        if len(policy) != 9:
            raise ThryceError(
                "Thryce policy must contain "
                "9 controls"
            )

        if not all(
            isinstance(value, bool)
            for value in policy.values()
        ):
            raise ThryceError(
                "Thryce policy controls "
                "must be boolean"
            )

        groups = self.instance.get(
            "enhancement_groups",
            {},
        )

        if len(groups) != 9:
            raise ThryceError(
                "Thryce requires "
                "9 enhancement groups"
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
                raise ThryceError(
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

    def register(
        self,
        check: AssuranceCheck,
    ) -> None:
        if (
            check.dimension
            not in
            THRYCE_VALIDATION_DIMENSIONS
        ):
            raise ThryceError(
                "unsupported validation dimension: "
                + check.dimension
            )

        if check.check_id in self._checks:
            raise ThryceError(
                "duplicate assurance check: "
                + check.check_id
            )

        self._checks[
            check.check_id
        ] = check

    def unregister(
        self,
        check_id: str,
    ) -> None:
        self._checks.pop(
            check_id,
            None,
        )

    def checks(
        self,
    ) -> tuple[
        AssuranceCheck,
        ...,
    ]:
        return tuple(
            self._checks[key]
            for key
            in sorted(
                self._checks
            )
        )

    def evaluate(
        self,
        check_id: str,
        subject: Any,
    ) -> dict[str, Any]:
        check = self._checks.get(
            check_id
        )

        if check is None:
            if (
                self.instance[
                    "policy"
                ][
                    "preserve_unknown"
                ]
            ):
                result = AssuranceResult(
                    check_id=check_id,
                    dimension="integration",
                    status="unknown",
                    message=(
                        "assurance check "
                        "is not registered"
                    ),
                )

                return result.projection()

            raise ThryceError(
                "unknown assurance check: "
                + check_id
            )

        try:
            result = check.run(
                subject
            )
        except Exception as exc:
            if not (
                self.instance[
                    "policy"
                ][
                    "fail_closed"
                ]
            ):
                raise

            result = AssuranceResult(
                check_id=check.check_id,
                dimension=check.dimension,
                status="failed",
                message=(
                    "assurance evaluator "
                    "raised an exception"
                ),
                observed={
                    "exception":
                        type(exc).__name__,
                    "message":
                        str(exc),
                },
            )

        return result.projection()

    def evaluate_all(
        self,
        subject: Any,
    ) -> dict[str, Any]:
        results = [
            self.evaluate(
                check.check_id,
                subject,
            )
            for check
            in self.checks()
        ]

        statuses = [
            item["status"]
            for item
            in results
        ]

        valid = (
            "failed"
            not in statuses
            and (
                "unknown"
                not in statuses
                or not self.instance[
                    "policy"
                ][
                    "fail_closed"
                ]
            )
        )

        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/batch/1.0.0"
            ),
            "instance_id": (
                self.instance[
                    "instance_id"
                ]
            ),
            "check_count": len(results),
            "results": results,
            "valid": valid,
            "authoritative": False,
            "attested": False,
            "evidence_admitted": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def regression(
        self,
        baseline: Mapping[str, Any],
        candidate: Mapping[str, Any],
    ) -> dict[str, Any]:
        baseline_status = {
            str(item.get("check_id")):
                str(item.get("status"))
            for item
            in baseline.get(
                "results",
                [],
            )
            if isinstance(item, dict)
        }

        candidate_status = {
            str(item.get("check_id")):
                str(item.get("status"))
            for item
            in candidate.get(
                "results",
                [],
            )
            if isinstance(item, dict)
        }

        identities = sorted(
            set(baseline_status)
            | set(candidate_status)
        )

        changes: list[
            dict[str, Any]
        ] = []

        regressions: list[
            dict[str, Any]
        ] = []

        rank = {
            "passed": 3,
            "skipped": 2,
            "unknown": 1,
            "failed": 0,
        }

        for identity in identities:
            before = baseline_status.get(
                identity,
                "unknown",
            )

            after = candidate_status.get(
                identity,
                "unknown",
            )

            if before == after:
                continue

            change = {
                "check_id": identity,
                "before": before,
                "after": after,
            }

            changes.append(change)

            if (
                rank.get(after, -1)
                < rank.get(before, -1)
            ):
                regressions.append(
                    change
                )

        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/regression/1.0.0"
            ),
            "changes": changes,
            "regressions": regressions,
            "regression_detected": bool(
                regressions
            ),
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def health_from_results(
        self,
        results: Iterable[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        grouped: dict[
            str,
            list[str],
        ] = {
            dimension: []
            for dimension
            in THRYCE_VALIDATION_DIMENSIONS
        }

        for result in results:
            dimension = str(
                result.get(
                    "dimension",
                    "integration",
                )
            )

            status = str(
                result.get(
                    "status",
                    "unknown",
                )
            )

            if dimension not in grouped:
                dimension = "integration"

            grouped[
                dimension
            ].append(
                status
            )

        validation_health: dict[
            str,
            str,
        ] = {}

        for dimension, statuses in (
            grouped.items()
        ):
            if not statuses:
                status = "unknown"

            elif "failed" in statuses:
                status = "failed"

            elif "unknown" in statuses:
                status = "unknown"

            elif all(
                value in (
                    "passed",
                    "skipped",
                )
                for value in statuses
            ):
                status = "passed"

            else:
                status = "unknown"

            validation_health[
                dimension
            ] = status

        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/validation-health/1.0.0"
            ),
            "dimensions": (
                validation_health
            ),
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def evidence_candidate(
        self,
        result: Mapping[str, Any],
        *,
        provenance: Any = None,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/evidence-candidate/1.0.0"
            ),
            "owner": "exile:notary",
            "source": (
                self.instance[
                    "instance_id"
                ]
            ),
            "result": dict(result),
            "provenance": provenance,
            "candidate_only": True,
            "evidence_admitted": False,
            "attested": False,
            "authoritative": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        dimensions = {
            "definition": True,
            "invariants": True,
            "validation": True,
            "dependencies": True,
            "integration": True,
            "replay": True,
            "regression": True,
            "evidence_boundary": (
                self.instance[
                    "evidence_admission_authorized"
                ]
                is False
                and self.instance[
                    "attestation_authorized"
                ]
                is False
            ),
            "notary_integration": (
                self.instance[
                    "owner"
                ]
                == "exile:notary"
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/health/1.0.0"
            ),
            "dimensions": {
                key: {
                    "healthy":
                        bool(value)
                }
                for key, value
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
                    THRYCE_ABILITIES
                )
                == 18
            ),
            "pipeline": (
                len(
                    THRYCE_PIPELINE
                )
                == 18
            ),
            "health_dimensions": (
                len(
                    THRYCE_HEALTH_DIMENSIONS
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    THRYCE_VALIDATION_DIMENSIONS
                )
                == 9
            ),
            "projections": (
                len(
                    THRYCE_PROJECTIONS
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
            "attestation_boundary": (
                self.instance[
                    "attestation_authorized"
                ]
                is False
            ),
            "evidence_boundary": (
                self.instance[
                    "evidence_admission_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "thryce/1.0.0"
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
            "attestation_authorized": False,
            "evidence_admission_authorized": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "substrate_id": self.substrate_id,
            "name": "Thryce",
            "role": (
                "living assurance substrate"
            ),
            "owner": (
                self.instance[
                    "owner"
                ]
            ),
            "instance": self.instance,
            "abilities": list(
                THRYCE_ABILITIES
            ),
            "pipeline": list(
                THRYCE_PIPELINE
            ),
            "health_dimensions": list(
                THRYCE_HEALTH_DIMENSIONS
            ),
            "validation_dimensions": list(
                THRYCE_VALIDATION_DIMENSIONS
            ),
            "projections": list(
                THRYCE_PROJECTIONS
            ),
            "enhancement_count": (
                self.enhancement_count
            ),
            "authoritative": False,
            "attestation_authorized": False,
            "evidence_admission_authorized": False,
        }

        payload["digest"] = digest(
            payload
        )

        return payload
