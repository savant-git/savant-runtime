#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    GuiseError,
    digest,
    stable_id,
)


class GuiseTemporalError(GuiseError):
    pass


@dataclass(frozen=True)
class TemporalAssertion:
    character_id: str
    subject_ref: str
    predicate: str
    value: Any
    valid_from: str | None = None
    valid_to: str | None = None
    known_from: str | None = None
    known_to: str | None = None
    source_refs: tuple[str, ...] = ()
    epistemic_class: str = "unknown"

    @property
    def id(self) -> str:
        return stable_id(
            "temporal-assertion",
            {
                "character_id": self.character_id,
                "subject_ref": self.subject_ref,
                "predicate": self.predicate,
                "value": self.value,
                "valid_from": self.valid_from,
                "valid_to": self.valid_to,
                "known_from": self.known_from,
                "known_to": self.known_to,
                "source_refs": list(
                    self.source_refs
                ),
                "epistemic_class": (
                    self.epistemic_class
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "temporal_assertion",
            "character_id": self.character_id,
            "subject_ref": self.subject_ref,
            "predicate": self.predicate,
            "value": self.value,
            "valid_time": {
                "from": self.valid_from,
                "to": self.valid_to,
            },
            "knowledge_time": {
                "from": self.known_from,
                "to": self.known_to,
            },
            "source_refs": list(
                self.source_refs
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


class CharacterTemporalIndex:
    def __init__(self) -> None:
        self._assertions: dict[
            str,
            TemporalAssertion,
        ] = {}

    def add(
        self,
        assertion: TemporalAssertion,
    ) -> TemporalAssertion:
        self._assertions[
            assertion.id
        ] = assertion
        return assertion

    def all(
        self,
        character_id: str,
    ) -> list[TemporalAssertion]:
        return sorted(
            (
                assertion
                for assertion
                in self._assertions.values()
                if (
                    assertion.character_id
                    == character_id
                )
            ),
            key=lambda item: (
                item.valid_from or "",
                item.known_from or "",
                item.id,
            ),
        )

    def project(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        assertions = [
            item.projection()
            for item in self.all(
                graph.character_id
            )
        ]

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "temporal_projection"
            ),
            "character_id": (
                graph.character_id
            ),
            "assertions": assertions,
            "assertion_count": len(
                assertions
            ),
            "bitemporal": True,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result
