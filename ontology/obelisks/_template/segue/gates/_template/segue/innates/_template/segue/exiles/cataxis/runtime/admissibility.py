#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from spacetime import OWNER

SCHEMA = "savant://cataxis/admissibility/1.0.0"


class AdmissibilityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    constraint_id: str
    accepted: bool
    observed: float | None = None
    expected: float | None = None
    tolerance: float | None = None
    violation: float | None = None
    reason: str | None = None
    metadata: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class AdmissibilityReceipt:
    accepted: bool
    results: tuple[ConstraintResult, ...]
    violations: tuple[str, ...]
    owner: str = OWNER
    authority_effect: str = "none"

    def projection(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = (
            datetime.now(UTC).isoformat()
        )
        payload["digest"] = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        return payload


def _finite(
    value: Any,
    name: str,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AdmissibilityError(
            f"{name} must be numeric"
        ) from exc

    if not math.isfinite(number):
        raise AdmissibilityError(
            f"{name} must be finite"
        )

    return number


def conserved(
    *,
    constraint_id: str,
    before: float,
    after: float,
    absolute_tolerance: float = 1e-9,
    relative_tolerance: float = 1e-12,
    metadata: Mapping[str, Any] | None = None,
) -> ConstraintResult:
    initial = _finite(
        before,
        "before",
    )

    final = _finite(
        after,
        "after",
    )

    absolute = abs(
        _finite(
            absolute_tolerance,
            "absolute_tolerance",
        )
    )

    relative = abs(
        _finite(
            relative_tolerance,
            "relative_tolerance",
        )
    )

    tolerance = max(
        absolute,
        relative
        * max(
            abs(initial),
            abs(final),
            1.0,
        ),
    )

    violation = abs(
        final - initial
    )

    accepted = (
        violation <= tolerance
    )

    return ConstraintResult(
        constraint_id=constraint_id,
        accepted=accepted,
        observed=final,
        expected=initial,
        tolerance=tolerance,
        violation=violation,
        reason=(
            None
            if accepted
            else "conservation_violation"
        ),
        metadata=dict(
            metadata or {}
        ),
    )


def bounded(
    *,
    constraint_id: str,
    observed: float,
    minimum: float | None = None,
    maximum: float | None = None,
    tolerance: float = 0.0,
    metadata: Mapping[str, Any] | None = None,
) -> ConstraintResult:
    value = _finite(
        observed,
        "observed",
    )

    slack = abs(
        _finite(
            tolerance,
            "tolerance",
        )
    )

    if (
        minimum is None
        and maximum is None
    ):
        raise AdmissibilityError(
            "at least one bound is required"
        )

    minimum_value = (
        None
        if minimum is None
        else _finite(
            minimum,
            "minimum",
        )
    )

    maximum_value = (
        None
        if maximum is None
        else _finite(
            maximum,
            "maximum",
        )
    )

    if (
        minimum_value is not None
        and maximum_value is not None
        and minimum_value
        > maximum_value
    ):
        raise AdmissibilityError(
            "minimum exceeds maximum"
        )

    lower_violation = (
        0.0
        if minimum_value is None
        else max(
            0.0,
            minimum_value
            - value
            - slack,
        )
    )

    upper_violation = (
        0.0
        if maximum_value is None
        else max(
            0.0,
            value
            - maximum_value
            - slack,
        )
    )

    violation = max(
        lower_violation,
        upper_violation,
    )

    accepted = (
        violation <= 0.0
    )

    return ConstraintResult(
        constraint_id=constraint_id,
        accepted=accepted,
        observed=value,
        tolerance=slack,
        violation=violation,
        reason=(
            None
            if accepted
            else "bound_violation"
        ),
        metadata={
            **dict(metadata or {}),
            "minimum": minimum_value,
            "maximum": maximum_value,
        },
    )


def nonnegative(
    *,
    constraint_id: str,
    observed: float,
    tolerance: float = 1e-12,
) -> ConstraintResult:
    return bounded(
        constraint_id=constraint_id,
        observed=observed,
        minimum=0.0,
        tolerance=tolerance,
    )


def finite_constraint(
    *,
    constraint_id: str,
    observed: Any,
) -> ConstraintResult:
    try:
        value = float(observed)
        accepted = math.isfinite(value)
    except (TypeError, ValueError):
        value = None
        accepted = False

    return ConstraintResult(
        constraint_id=constraint_id,
        accepted=accepted,
        observed=value,
        violation=(
            0.0
            if accepted
            else math.inf
        ),
        reason=(
            None
            if accepted
            else "nonfinite_state"
        ),
    )


def causal_speed(
    *,
    speed_mps: float,
    maximum_speed_mps: float,
    tolerance_mps: float = 1e-9,
) -> ConstraintResult:
    speed = abs(
        _finite(
            speed_mps,
            "speed_mps",
        )
    )

    maximum = abs(
        _finite(
            maximum_speed_mps,
            "maximum_speed_mps",
        )
    )

    if maximum <= 0:
        raise AdmissibilityError(
            "maximum speed must be positive"
        )

    return bounded(
        constraint_id="causal_speed",
        observed=speed,
        minimum=0.0,
        maximum=maximum,
        tolerance=tolerance_mps,
    )


def entropy_nondecrease(
    *,
    entropy_before_j_k: float,
    entropy_after_j_k: float,
    tolerance_j_k: float = 1e-12,
) -> ConstraintResult:
    before = _finite(
        entropy_before_j_k,
        "entropy_before_j_k",
    )

    after = _finite(
        entropy_after_j_k,
        "entropy_after_j_k",
    )

    tolerance = abs(
        _finite(
            tolerance_j_k,
            "tolerance_j_k",
        )
    )

    violation = max(
        0.0,
        before - after - tolerance,
    )

    accepted = (
        violation <= 0.0
    )

    return ConstraintResult(
        constraint_id=(
            "entropy_nondecrease"
        ),
        accepted=accepted,
        observed=after,
        expected=before,
        tolerance=tolerance,
        violation=violation,
        reason=(
            None
            if accepted
            else "second_law_violation"
        ),
    )


def probability_normalization(
    probabilities: Sequence[float],
    *,
    tolerance: float = 1e-12,
) -> ConstraintResult:
    values = tuple(
        _finite(
            value,
            "probability",
        )
        for value in probabilities
    )

    negative = any(
        value < -tolerance
        for value in values
    )

    total = sum(values)

    violation = max(
        abs(total - 1.0),
        max(
            (
                -value
                for value in values
                if value < 0
            ),
            default=0.0,
        ),
    )

    accepted = (
        not negative
        and abs(total - 1.0)
        <= tolerance
    )

    return ConstraintResult(
        constraint_id=(
            "probability_normalization"
        ),
        accepted=accepted,
        observed=total,
        expected=1.0,
        tolerance=tolerance,
        violation=violation,
        reason=(
            None
            if accepted
            else "probability_violation"
        ),
    )


def evaluate(
    results: Sequence[ConstraintResult],
) -> AdmissibilityReceipt:
    source = tuple(results)

    violations = tuple(
        result.constraint_id
        for result in source
        if not result.accepted
    )

    return AdmissibilityReceipt(
        accepted=not violations,
        results=source,
        violations=violations,
    )


def capabilities() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "primitive": "physics",
        "authority_effect": "none",
        "capabilities": [
            "physical_admissibility",
            "conservation_constraints",
            "bounded_constraints",
            "finite_state_constraints",
            "nonnegative_constraints",
            "causal_speed_constraints",
            "entropy_constraints",
            "probability_normalization_constraints",
            "constraint_receipts",
            "violation_provenance",
            "deterministic_acceptance",
            "carbon_simulation_guard",
            "mobius_consequence_guard",
        ],
    }
