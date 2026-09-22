#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
    stable_id,
)


@dataclass(frozen=True)
class RelationshipState:
    character_id: str
    other_ref: str
    dimensions: Mapping[str, Any]
    at: str | None = None
    phase: str | None = None
    evidence_refs: tuple[str, ...] = ()
    counter_refs: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return stable_id(
            "relationship-state",
            {
                "character_id": self.character_id,
                "other_ref": self.other_ref,
                "dimensions": dict(
                    self.dimensions
                ),
                "at": self.at,
                "phase": self.phase,
                "evidence_refs": list(
                    self.evidence_refs
                ),
                "counter_refs": list(
                    self.counter_refs
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "relationship_state",
            "character_id": self.character_id,
            "other_ref": self.other_ref,
            "dimensions": dict(
                self.dimensions
            ),
            "at": self.at,
            "phase": self.phase,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "counter_refs": list(
                self.counter_refs
            ),
            "authoritative": False,
            "authority_effect": "none",
        }


class CharacterRelationshipEngine:
    def __init__(self) -> None:
        self._states: dict[
            str,
            RelationshipState,
        ] = {}

    def add(
        self,
        state: RelationshipState,
    ) -> RelationshipState:
        self._states[state.id] = state
        return state

    def between(
        self,
        character_id: str,
        other_ref: str,
    ) -> list[RelationshipState]:
        return sorted(
            (
                state
                for state
                in self._states.values()
                if (
                    state.character_id
                    == character_id
                    and state.other_ref
                    == other_ref
                )
            ),
            key=lambda state: (
                state.at or "",
                state.phase or "",
                state.id,
            ),
        )

    def project(
        self,
        graph: CharacterGraph,
        *,
        other_ref: str,
    ) -> dict[str, Any]:
        states = [
            state.projection()
            for state in self.between(
                graph.character_id,
                other_ref,
            )
        ]

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "relationship_projection"
            ),
            "character_id": (
                graph.character_id
            ),
            "other_ref": other_ref,
            "states": states,
            "state_count": len(states),
            "relationship_is_dynamic": True,
            "relationship_is_contextual": True,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result

    def condition_behavior(
        self,
        graph: CharacterGraph,
        *,
        other_ref: str,
        behavior_candidates: Sequence[
            Mapping[str, Any]
        ],
    ) -> dict[str, Any]:
        relationship_refs = [
            state.id
            for state in self.between(
                graph.character_id,
                other_ref,
            )
        ]

        candidates = []

        for candidate in behavior_candidates:
            item = dict(candidate)
            item.setdefault(
                "relationship_refs",
                relationship_refs,
            )
            item.setdefault(
                "classification",
                "requires_substantiation",
            )
            candidates.append(item)

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "relationship_conditioned_behavior"
            ),
            "character_id": (
                graph.character_id
            ),
            "other_ref": other_ref,
            "relationship_refs": (
                relationship_refs
            ),
            "candidates": candidates,
            "deterministic": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result
