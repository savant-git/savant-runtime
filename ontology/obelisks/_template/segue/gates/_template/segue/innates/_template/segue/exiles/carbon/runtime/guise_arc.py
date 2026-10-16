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
class ArcState:
    character_id: str
    dimension: str
    state: Any
    at: str | None = None
    phase: str | None = None
    evidence_refs: tuple[str, ...] = ()
    counter_refs: tuple[str, ...] = ()
    epistemic_class: str = "unknown"

    @property
    def id(self) -> str:
        return stable_id(
            "character-arc-state",
            {
                "character_id": self.character_id,
                "dimension": self.dimension,
                "state": self.state,
                "at": self.at,
                "phase": self.phase,
                "evidence_refs": list(
                    self.evidence_refs
                ),
                "counter_refs": list(
                    self.counter_refs
                ),
                "epistemic_class": (
                    self.epistemic_class
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_arc_state",
            "character_id": self.character_id,
            "dimension": self.dimension,
            "state": self.state,
            "at": self.at,
            "phase": self.phase,
            "evidence_refs": list(
                self.evidence_refs
            ),
            "counter_refs": list(
                self.counter_refs
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


@dataclass(frozen=True)
class ArcTransition:
    character_id: str
    dimension: str
    left_ref: str
    right_ref: str
    cause_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    reversible: bool | None = None
    epistemic_class: str = "unknown"

    @property
    def id(self) -> str:
        return stable_id(
            "character-arc-transition",
            {
                "character_id": self.character_id,
                "dimension": self.dimension,
                "left_ref": self.left_ref,
                "right_ref": self.right_ref,
                "cause_refs": list(
                    self.cause_refs
                ),
                "relationship_refs": list(
                    self.relationship_refs
                ),
                "reversible": self.reversible,
                "epistemic_class": (
                    self.epistemic_class
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": (
                "character_arc_transition"
            ),
            "character_id": self.character_id,
            "dimension": self.dimension,
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "cause_refs": list(
                self.cause_refs
            ),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "reversible": self.reversible,
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


class CharacterArcGraph:
    def __init__(self) -> None:
        self._states: dict[
            str,
            ArcState,
        ] = {}
        self._transitions: dict[
            str,
            ArcTransition,
        ] = {}

    def add_state(
        self,
        state: ArcState,
    ) -> ArcState:
        self._states[state.id] = state
        return state

    def add_transition(
        self,
        transition: ArcTransition,
    ) -> ArcTransition:
        self._transitions[
            transition.id
        ] = transition
        return transition

    def project(
        self,
        graph: CharacterGraph,
        *,
        dimension: str | None = None,
    ) -> dict[str, Any]:
        states = [
            state
            for state in self._states.values()
            if (
                state.character_id
                == graph.character_id
                and (
                    dimension is None
                    or state.dimension
                    == dimension
                )
            )
        ]

        state_ids = {
            state.id
            for state in states
        }

        transitions = [
            transition
            for transition
            in self._transitions.values()
            if (
                transition.character_id
                == graph.character_id
                and (
                    dimension is None
                    or transition.dimension
                    == dimension
                )
                and (
                    transition.left_ref
                    in state_ids
                    or transition.right_ref
                    in state_ids
                )
            )
        ]

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "arc_projection",
            "character_id": (
                graph.character_id
            ),
            "dimension": dimension,
            "states": [
                state.projection()
                for state in sorted(
                    states,
                    key=lambda item: (
                        item.at or "",
                        item.phase or "",
                        item.id,
                    ),
                )
            ],
            "transitions": [
                transition.projection()
                for transition in sorted(
                    transitions,
                    key=lambda item: (
                        item.dimension,
                        item.id,
                    ),
                )
            ],
            "linear_arc_required": False,
            "regression_supported": True,
            "recurrence_supported": True,
            "contradiction_supported": True,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result
