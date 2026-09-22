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


@dataclass(frozen=True)
class NarrativeDebt:
    character_id: str
    description: str
    origin_refs: tuple[str, ...] = ()
    consequence_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    status: str = "open"
    temporal_ref: str | None = None

    @property
    def id(self) -> str:
        return stable_id(
            "character-narrative-debt",
            {
                "character_id": self.character_id,
                "description": self.description,
                "origin_refs": list(
                    self.origin_refs
                ),
                "consequence_refs": list(
                    self.consequence_refs
                ),
                "relationship_refs": list(
                    self.relationship_refs
                ),
                "status": self.status,
                "temporal_ref": (
                    self.temporal_ref
                ),
            },
        )

    def projection(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": "narrative_debt",
            "character_id": self.character_id,
            "description": self.description,
            "origin_refs": list(
                self.origin_refs
            ),
            "consequence_refs": list(
                self.consequence_refs
            ),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "status": self.status,
            "temporal_ref": self.temporal_ref,
            "authority_effect": "none",
        }


class NarrativeDebtLedger:
    def __init__(self) -> None:
        self._debts: dict[
            str,
            NarrativeDebt,
        ] = {}

    def add(
        self,
        debt: NarrativeDebt,
    ) -> NarrativeDebt:
        self._debts[debt.id] = debt
        return debt

    def project(
        self,
        graph: CharacterGraph,
        *,
        status: str | None = None,
    ) -> dict[str, Any]:
        debts = [
            debt
            for debt in self._debts.values()
            if (
                debt.character_id
                == graph.character_id
                and (
                    status is None
                    or debt.status == status
                )
            )
        ]

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "narrative_debt_projection"
            ),
            "character_id": (
                graph.character_id
            ),
            "status_filter": status,
            "debts": [
                debt.projection()
                for debt in sorted(
                    debts,
                    key=lambda item: (
                        item.status,
                        item.id,
                    ),
                )
            ],
            "debt_count": len(debts),
            "automatic_resolution": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )

        return result
