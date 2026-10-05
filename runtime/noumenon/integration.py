from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/developmental-integration/1"

MECHANISMS = frozenset(
    {
        "admission",
        "affect",
        "appraisal",
        "bandwidth",
        "branch",
        "cognition",
        "coherence",
        "commitment",
        "conscience",
        "development",
        "drift",
        "dynamics",
        "identity",
        "inheritance",
        "memory_dynamics",
        "metabolism",
        "narrative",
        "path_dependence",
        "prediction",
        "projection",
        "prospective",
        "recovery",
        "relationship",
        "relational_trajectory",
        "residue",
        "resonance",
        "salience",
        "significance",
        "succession",
        "taste",
        "tension",
        "transference",
        "values",
    }
)


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
class MechanismProjection:
    mechanism: str
    projection: Mapping[str, Any]
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mechanism not in MECHANISMS:
            raise ValueError(
                "unsupported noumenon mechanism"
            )

        if not self.projection:
            raise ValueError(
                "mechanism projection is required"
            )

    @property
    def digest(self) -> str:
        return _digest(
            {
                "mechanism": self.mechanism,
                "projection": self.projection,
                "causal_refs": list(
                    self.causal_refs
                ),
            }
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-mechanism-projection:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class DevelopmentalIntegration:
    noumenon_id: str
    generation: int
    mechanisms: tuple[
        MechanismProjection,
        ...
    ]
    causal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        if self.generation < 0:
            raise ValueError(
                "generation cannot be negative"
            )

        names = [
            item.mechanism
            for item in self.mechanisms
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "duplicate mechanism projection"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "generation": self.generation,
            "mechanisms": {
                item.mechanism: {
                    "projection": (
                        item.projection
                    ),
                    "projection_ref": (
                        item.id
                    ),
                    "causal_refs": list(
                        item.causal_refs
                    ),
                }
                for item in sorted(
                    self.mechanisms,
                    key=lambda value: (
                        value.mechanism
                    ),
                )
            },
            "causal_refs": list(
                self.causal_refs
            ),
            "integration_owner": "noumenon",
            "substance_owners_preserved": True,
            "authority_transferred": False,
            "contradictions_preserved": True,
            "automatic_identity_mutation": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)

        return body


def mechanism_projection(
    mechanism: str,
    projection: Mapping[str, Any],
    *,
    causal_refs: Sequence[str] = (),
) -> MechanismProjection:
    return MechanismProjection(
        mechanism=mechanism,
        projection=dict(projection),
        causal_refs=tuple(
            dict.fromkeys(causal_refs)
        ),
    )


def integrate(
    noumenon_id: str,
    generation: int,
    projections: Sequence[
        MechanismProjection
    ],
    *,
    causal_refs: Sequence[str] = (),
) -> DevelopmentalIntegration:
    ordered = tuple(
        sorted(
            projections,
            key=lambda item: (
                item.mechanism,
                item.id,
            ),
        )
    )

    combined_causal_refs: list[str] = list(
        causal_refs
    )

    for item in ordered:
        combined_causal_refs.extend(
            (
                item.id,
                *item.causal_refs,
            )
        )

    return DevelopmentalIntegration(
        noumenon_id=noumenon_id,
        generation=generation,
        mechanisms=ordered,
        causal_refs=tuple(
            dict.fromkeys(
                combined_causal_refs
            )
        ),
    )


def mechanism_refs(
    integration: DevelopmentalIntegration,
) -> Mapping[str, str]:
    return {
        item.mechanism: item.id
        for item in integration.mechanisms
    }


def integration_digest(
    integration: DevelopmentalIntegration,
) -> str:
    return str(
        integration.projection()["digest"]
    )


def compare_integrations(
    predecessor: DevelopmentalIntegration,
    successor: DevelopmentalIntegration,
) -> Mapping[str, Any]:
    if (
        predecessor.noumenon_id
        != successor.noumenon_id
    ):
        raise ValueError(
            "cannot compare different "
            "noumenon identities"
        )

    previous = mechanism_refs(
        predecessor
    )

    current = mechanism_refs(
        successor
    )

    names = sorted(
        set(previous)
        | set(current)
    )

    changed = tuple(
        name
        for name in names
        if previous.get(name)
        != current.get(name)
    )

    retained = tuple(
        name
        for name in names
        if (
            name in previous
            and name in current
            and previous[name]
            == current[name]
        )
    )

    added = tuple(
        name
        for name in names
        if (
            name not in previous
            and name in current
        )
    )

    removed = tuple(
        name
        for name in names
        if (
            name in previous
            and name not in current
        )
    )

    return {
        "schema": SCHEMA,
        "noumenon_id": (
            predecessor.noumenon_id
        ),
        "predecessor_generation": (
            predecessor.generation
        ),
        "successor_generation": (
            successor.generation
        ),
        "changed_mechanisms": list(
            changed
        ),
        "retained_mechanisms": list(
            retained
        ),
        "added_mechanisms": list(
            added
        ),
        "removed_mechanisms": list(
            removed
        ),
        "predecessor_digest": (
            integration_digest(
                predecessor
            )
        ),
        "successor_digest": (
            integration_digest(
                successor
            )
        ),
        "authority_effect": "none",
        "derived": True,
        "authoritative": False,
    }


def integration_projection(
    integration: DevelopmentalIntegration,
) -> Mapping[str, Any]:
    projection = integration.projection()

    return {
        **projection,
        "mechanism_count": len(
            integration.mechanisms
        ),
        "model_is_noumenon": False,
        "provider_is_noumenon": False,
        "integration_absorbs_authority": False,
        "experience_equals_identity": False,
        "development_requires_causal_lineage": True,
        "same_experience_can_diverge": True,
        "persistent_individuality_preserved": True,
    }
