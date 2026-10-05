#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    GuiseError,
    digest,
    stable_id,
)


MEMORY_STATES = {
    "remembers",
    "forgot",
    "misremembers",
    "uncertain",
    "suppressed",
    "unknown",
}


class GuiseMemoryError(GuiseError):
    pass


@dataclass(frozen=True)
class MemoryAssertion:
    character_id: str
    event_ref: str
    memory_state: str
    remembered_content: str | None = None
    canonical_event_ref: str | None = None
    at: str | None = None
    learned_at: str | None = None
    evidence_refs: tuple[str, ...] = ()
    counter_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    epistemic_class: str = "unknown"

    def __post_init__(self) -> None:
        if self.memory_state not in MEMORY_STATES:
            raise GuiseMemoryError(
                f"unsupported memory state: {self.memory_state}"
            )

    @property
    def id(self) -> str:
        return stable_id(
            "character-memory",
            {
                "character_id": self.character_id,
                "event_ref": self.event_ref,
                "memory_state": self.memory_state,
                "remembered_content": self.remembered_content,
                "canonical_event_ref": self.canonical_event_ref,
                "at": self.at,
                "learned_at": self.learned_at,
                "evidence_refs": list(self.evidence_refs),
                "counter_refs": list(self.counter_refs),
                "source_refs": list(self.source_refs),
                "epistemic_class": self.epistemic_class,
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_memory",
            "character_id": self.character_id,
            "event_ref": self.event_ref,
            "memory_state": self.memory_state,
            "remembered_content": self.remembered_content,
            "canonical_event_ref": self.canonical_event_ref,
            "at": self.at,
            "learned_at": self.learned_at,
            "evidence_refs": list(self.evidence_refs),
            "counter_refs": list(self.counter_refs),
            "source_refs": list(self.source_refs),
            "epistemic_class": self.epistemic_class,
            "authority_effect": "none",
        }


class CharacterMemoryLedger:
    def __init__(self) -> None:
        self._assertions: dict[str, MemoryAssertion] = {}

    def add(
        self,
        assertion: MemoryAssertion,
    ) -> MemoryAssertion:
        self._assertions[assertion.id] = assertion
        return assertion

    def all(
        self,
        character_id: str,
    ) -> list[MemoryAssertion]:
        return sorted(
            (
                assertion
                for assertion in self._assertions.values()
                if assertion.character_id == character_id
            ),
            key=lambda item: (
                item.at or "",
                item.learned_at or "",
                item.id,
            ),
        )

    def for_event(
        self,
        character_id: str,
        event_ref: str,
    ) -> list[MemoryAssertion]:
        return [
            assertion
            for assertion in self.all(character_id)
            if assertion.event_ref == event_ref
        ]

    def project(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        assertions = [
            assertion.projection()
            for assertion in self.all(graph.character_id)
        ]

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "memory_projection",
            "character_id": graph.character_id,
            "memories": assertions,
            "memory_count": len(assertions),
            "memory_separate_from_truth": True,
            "misremembering_preserved": True,
            "forgetting_preserved": True,
            "uncertainty_preserved": True,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = digest(result)
        return result
