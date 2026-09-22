#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    CharacterGraph,
    digest,
    stable_id,
)


ECHO_KINDS = {
    "echo",
    "parallel",
    "inversion",
    "contrast",
    "recurrence",
}


@dataclass(frozen=True)
class CharacterEcho:
    left_character_ref: str
    right_character_ref: str
    kind: str
    dimension_ref: str
    evidence_refs: tuple[str, ...] = ()
    counter_refs: tuple[str, ...] = ()
    interpretation: str | None = None
    epistemic_class: str = "hypothesis"

    def __post_init__(self) -> None:
        if self.kind not in ECHO_KINDS:
            raise ValueError(
                f"unsupported echo kind: "
                f"{self.kind}"
            )

    @property
    def id(self) -> str:
        return stable_id(
            "character-echo",
            {
                "left_character_ref": (
                    self.left_character_ref
                ),
                "right_character_ref": (
                    self.right_character_ref
                ),
                "kind": self.kind,
                "dimension_ref": (
                    self.dimension_ref
                ),
                "evidence_refs": list(
                    self.evidence_refs
                ),
                "counter_refs": list(
                    self.counter_refs
                ),
                "interpretation": (
                    self.interpretation
                ),
                "epistemic_class": (
                    self.epistemic_class
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "character_echo",
            "echo_kind": self.kind,
            "left_character_ref": (
                self.left_character_ref
            ),
            "right_character_ref": (
                self.right_character_ref
            ),
            "dimension_ref": (
                self.dimension_ref
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "counter_refs": list(
                self.counter_refs
            ),
            "interpretation": (
                self.interpretation
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


class CharacterEchoIndex:
    def __init__(self) -> None:
        self._echoes: dict[
            str,
            CharacterEcho,
        ] = {}

    def add(
        self,
        echo: CharacterEcho,
    ) -> CharacterEcho:
        self._echoes[echo.id] = echo
        return echo

    def project(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        echoes = sorted(
            (
                echo
                for echo in self._echoes.values()
                if graph.character_id in {
                    echo.left_character_ref,
                    echo.right_character_ref,
                }
            ),
            key=lambda item: (
                item.kind,
                item.dimension_ref,
                item.id,
            ),
        )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "echo_projection",
            "character_id": (
                graph.character_id
            ),
            "echoes": [
                echo.projection()
                for echo in echoes
            ],
            "echo_count": len(echoes),
            "parallel_is_identity": False,
            "inversion_is_deterministic": False,
            "automatic_acceptance": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )
        return result
