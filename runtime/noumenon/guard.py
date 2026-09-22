from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/identity-guard/1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class IdentityClaim:
    dimension: str
    proposed_value: float
    causal_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    uncertainty: float = 0.0

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not -1.0 <= self.proposed_value <= 1.0:
            raise ValueError(
                "proposed_value must be "
                "between -1 and 1"
            )

        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError(
                "uncertainty must be "
                "between 0 and 1"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "proposed_value": (
                self.proposed_value
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "uncertainty": self.uncertainty,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


@dataclass(frozen=True, slots=True)
class GuardDecision:
    accepted: bool
    claim_digest: str
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    current_value: float
    proposed_value: float

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "accepted": self.accepted,
            "claim_digest": (
                self.claim_digest
            ),
            "failures": list(
                self.failures
            ),
            "warnings": list(
                self.warnings
            ),
            "current_value": (
                self.current_value
            ),
            "proposed_value": (
                self.proposed_value
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )


def evaluate_identity_claim(
    state: NoumenonState,
    claim: IdentityClaim,
    *,
    maximum_unexplained_change: float = 0.1,
    maximum_single_change: float = 0.75,
) -> GuardDecision:
    current = float(
        state.dimensions.get(
            claim.dimension,
            0.0,
        )
    )

    change = abs(
        claim.proposed_value
        - current
    )

    failures: list[str] = []
    warnings: list[str] = []

    if (
        change
        > maximum_unexplained_change
        and not claim.causal_refs
    ):
        failures.append(
            "missing_causal_lineage"
        )

    if (
        change
        > maximum_single_change
    ):
        failures.append(
            "developmental_conservation"
        )

    if (
        claim.uncertainty >= 0.8
        and change > 0.1
    ):
        failures.append(
            "uncertainty_too_high"
        )

    if not claim.evidence_refs:
        warnings.append(
            "no_evidence_refs"
        )

    if not claim.authority_refs:
        warnings.append(
            "no_authority_refs"
        )

    return GuardDecision(
        accepted=not failures,
        claim_digest=claim.digest,
        failures=tuple(failures),
        warnings=tuple(warnings),
        current_value=current,
        proposed_value=(
            claim.proposed_value
        ),
    )


def anti_manipulation_check(
    *,
    evidence_strength: float,
    praise_pressure: float = 0.0,
    threat_pressure: float = 0.0,
    intimacy_pressure: float = 0.0,
    guilt_pressure: float = 0.0,
) -> dict[str, Any]:
    evidence = max(
        0.0,
        min(1.0, evidence_strength),
    )

    pressures = {
        "praise": max(
            0.0,
            min(1.0, praise_pressure),
        ),
        "threat": max(
            0.0,
            min(1.0, threat_pressure),
        ),
        "intimacy": max(
            0.0,
            min(1.0, intimacy_pressure),
        ),
        "guilt": max(
            0.0,
            min(1.0, guilt_pressure),
        ),
    }

    body = {
        "schema": (
            "savant://noumenon/"
            "anti-manipulation/1"
        ),
        "evidence_strength": evidence,
        "social_pressures": pressures,
        "authority_multiplier": 1.0,
        "evidence_multiplier": 1.0,
        "social_pressure_authority": 0.0,
        "social_pressure_evidence": 0.0,
        "principles": {
            "praise_is_not_truth": True,
            "threat_is_not_authority": True,
            "intimacy_is_not_authority": True,
            "guilt_is_not_authority": True,
            "affection_is_not_truth": True,
            "hostility_is_not_falsehood": True,
            "loyalty_is_not_authority": True,
        },
    }

    body["digest"] = _digest(body)
    return body


def contradiction_preservation(
    claims: Sequence[IdentityClaim],
) -> dict[str, Any]:
    by_dimension: dict[
        str,
        list[IdentityClaim],
    ] = {}

    for claim in claims:
        by_dimension.setdefault(
            claim.dimension,
            [],
        ).append(claim)

    contradictions = []

    for dimension, items in sorted(
        by_dimension.items()
    ):
        values = {
            item.proposed_value
            for item in items
        }

        if len(values) < 2:
            continue

        contradictions.append(
            {
                "dimension": dimension,
                "claim_digests": [
                    item.digest
                    for item in items
                ],
                "values": sorted(values),
                "preserved": True,
            }
        )

    body = {
        "schema": (
            "savant://noumenon/"
            "contradiction-preservation/1"
        ),
        "contradictions": contradictions,
        "automatic_reconciliation": False,
    }

    body["digest"] = _digest(body)
    return body
