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
class CharacterMotif:
    character_id: str
    motif_ref: str
    manifestation_refs: tuple[str, ...] = ()
    relationship_refs: tuple[str, ...] = ()
    temporal_refs: tuple[str, ...] = ()
    meaning_candidates: tuple[str, ...] = ()
    counter_refs: tuple[str, ...] = ()
    epistemic_class: str = "unknown"

    @property
    def id(self) -> str:
        return stable_id(
            "character-motif",
            {
                "character_id": self.character_id,
                "motif_ref": self.motif_ref,
                "manifestation_refs": list(
                    self.manifestation_refs
                ),
                "relationship_refs": list(
                    self.relationship_refs
                ),
                "temporal_refs": list(
                    self.temporal_refs
                ),
                "meaning_candidates": list(
                    self.meaning_candidates
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
            "kind": "character_motif",
            "character_id": self.character_id,
            "motif_ref": self.motif_ref,
            "manifestation_refs": list(
                self.manifestation_refs
            ),
            "relationship_refs": list(
                self.relationship_refs
            ),
            "temporal_refs": list(
                self.temporal_refs
            ),
            "meaning_candidates": list(
                self.meaning_candidates
            ),
            "counter_refs": list(
                self.counter_refs
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "authority_effect": "none",
        }


class CharacterMotifIndex:
    def __init__(self) -> None:
        self._motifs: dict[
            str,
            CharacterMotif,
        ] = {}

    def add(
        self,
        motif: CharacterMotif,
    ) -> CharacterMotif:
        self._motifs[motif.id] = motif
        return motif

    def project(
        self,
        graph: CharacterGraph,
    ) -> dict[str, Any]:
        motifs = sorted(
            (
                motif
                for motif in self._motifs.values()
                if (
                    motif.character_id
                    == graph.character_id
                )
            ),
            key=lambda item: (
                item.motif_ref,
                item.id,
            ),
        )

        result = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": "motif_projection",
            "character_id": (
                graph.character_id
            ),
            "motifs": [
                motif.projection()
                for motif in motifs
            ],
            "motif_count": len(motifs),
            "meaning_is_inferred": True,
            "automatic_symbolism": False,
            "character_mutated": False,
            "authority_effect": "none",
        }

        result["projection_digest"] = (
            digest(result)
        )
        return result
