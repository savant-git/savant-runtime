from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.integration import (
    DevelopmentalIntegration,
    MechanismProjection,
    compare_integrations,
    integrate,
    integration_projection,
)


SCHEMA = "savant://noumenon/integration-runtime/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class IntegrationTransition:
    predecessor_ref: str | None
    successor_ref: str
    noumenon_id: str
    predecessor_generation: int | None
    successor_generation: int
    changed_mechanisms: tuple[str, ...]
    retained_mechanisms: tuple[str, ...]
    added_mechanisms: tuple[str, ...]
    removed_mechanisms: tuple[str, ...]
    causal_refs: tuple[str, ...]

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "predecessor_ref": self.predecessor_ref,
            "successor_ref": self.successor_ref,
            "noumenon_id": self.noumenon_id,
            "predecessor_generation": (
                self.predecessor_generation
            ),
            "successor_generation": (
                self.successor_generation
            ),
            "changed_mechanisms": list(
                self.changed_mechanisms
            ),
            "retained_mechanisms": list(
                self.retained_mechanisms
            ),
            "added_mechanisms": list(
                self.added_mechanisms
            ),
            "removed_mechanisms": list(
                self.removed_mechanisms
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "authority_transferred": False,
            "automatic_identity_mutation": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


@dataclass(frozen=True, slots=True)
class IntegrationRuntimeResult:
    integration: DevelopmentalIntegration
    transition: IntegrationTransition

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "integration": integration_projection(
                self.integration
            ),
            "transition": (
                self.transition.projection()
            ),
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


def establish_integration(
    *,
    noumenon_id: str,
    generation: int,
    mechanisms: Sequence[
        MechanismProjection
    ],
    causal_refs: Sequence[str],
) -> IntegrationRuntimeResult:
    if not causal_refs:
        raise ValueError(
            "integration establishment "
            "requires causal refs"
        )

    current = integrate(
        noumenon_id,
        generation,
        mechanisms,
        causal_refs=causal_refs,
    )

    current_ref = str(
        current.projection()["digest"]
    )

    transition = IntegrationTransition(
        predecessor_ref=None,
        successor_ref=current_ref,
        noumenon_id=noumenon_id,
        predecessor_generation=None,
        successor_generation=generation,
        changed_mechanisms=(),
        retained_mechanisms=(),
        added_mechanisms=tuple(
            sorted(
                item.mechanism
                for item in mechanisms
            )
        ),
        removed_mechanisms=(),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *causal_refs,
                    current_ref,
                    *current.causal_refs,
                )
            )
        ),
    )

    return IntegrationRuntimeResult(
        integration=current,
        transition=transition,
    )


def advance_integration(
    predecessor: DevelopmentalIntegration,
    *,
    generation: int,
    mechanisms: Sequence[
        MechanismProjection
    ],
    causal_refs: Sequence[str],
) -> IntegrationRuntimeResult:
    if generation != (
        predecessor.generation + 1
    ):
        raise ValueError(
            "integration generation must "
            "advance exactly once"
        )

    if not causal_refs:
        raise ValueError(
            "integration advancement "
            "requires causal refs"
        )

    predecessor_ref = str(
        predecessor.projection()["digest"]
    )

    successor = integrate(
        predecessor.noumenon_id,
        generation,
        mechanisms,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    predecessor_ref,
                    *causal_refs,
                )
            )
        ),
    )

    successor_ref = str(
        successor.projection()["digest"]
    )

    comparison = compare_integrations(
        predecessor,
        successor,
    )

    transition = IntegrationTransition(
        predecessor_ref=predecessor_ref,
        successor_ref=successor_ref,
        noumenon_id=predecessor.noumenon_id,
        predecessor_generation=(
            predecessor.generation
        ),
        successor_generation=generation,
        changed_mechanisms=tuple(
            comparison[
                "changed_mechanisms"
            ]
        ),
        retained_mechanisms=tuple(
            comparison[
                "retained_mechanisms"
            ]
        ),
        added_mechanisms=tuple(
            comparison[
                "added_mechanisms"
            ]
        ),
        removed_mechanisms=tuple(
            comparison[
                "removed_mechanisms"
            ]
        ),
        causal_refs=tuple(
            dict.fromkeys(
                (
                    predecessor_ref,
                    successor_ref,
                    *causal_refs,
                    *successor.causal_refs,
                )
            )
        ),
    )

    return IntegrationRuntimeResult(
        integration=successor,
        transition=transition,
    )


def validate_transition(
    predecessor: DevelopmentalIntegration,
    result: IntegrationRuntimeResult,
) -> bool:
    transition = result.transition
    successor = result.integration

    predecessor_ref = str(
        predecessor.projection()["digest"]
    )

    successor_ref = str(
        successor.projection()["digest"]
    )

    if (
        predecessor.noumenon_id
        != successor.noumenon_id
    ):
        return False

    if (
        successor.generation
        != predecessor.generation + 1
    ):
        return False

    if (
        transition.predecessor_ref
        != predecessor_ref
    ):
        return False

    if (
        transition.successor_ref
        != successor_ref
    ):
        return False

    if (
        transition.noumenon_id
        != successor.noumenon_id
    ):
        return False

    if (
        predecessor_ref
        not in transition.causal_refs
    ):
        return False

    if (
        successor_ref
        not in transition.causal_refs
    ):
        return False

    return True


def runtime_projection(
    result: IntegrationRuntimeResult,
) -> Mapping[str, Any]:
    projection = result.projection()

    return {
        **projection,
        "persistent_identity": (
            result.integration.noumenon_id
        ),
        "generation": (
            result.integration.generation
        ),
        "mechanism_count": len(
            result.integration.mechanisms
        ),
        "lineage_preserved": True,
        "mechanisms_remain_derived": True,
        "authority_remains_external": True,
        "model_independent": True,
        "provider_independent": True,
    }
