#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path("/root/savant-runtime").resolve()

CARBON_RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "carbon"
    / "runtime"
).resolve()

sys.path.insert(
    0,
    str(CARBON_RUNTIME),
)

from guise import (  # noqa: E402
    CategorySubstantiation,
    Evidence,
    Guise,
    Relationship,
    SourceReference,
    TemporalScope,
    health,
)


def main() -> int:
    guise = Guise()

    graph = guise.new_character(
        "demonstration_character",
        display_name="demonstration character",
    )

    source = SourceReference(
        source_id="demonstration_source",
        location="paragraph:1",
        source_kind="test_fixture",
        authority_class="test_evidence",
    )

    evidence = graph.add_evidence(
        Evidence(
            subject_id=graph.character_id,
            observation=(
                "the character repeatedly returns "
                "to an unresolved problem."
            ),
            source=source,
            epistemic_class="observation",
            temporal=TemporalScope(
                phase="demonstration_phase"
            ),
            tags=("persistence",),
        )
    )

    category = graph.add_category(
        CategorySubstantiation(
            character_id=graph.character_id,
            domain="attention",
            category="persistence",
            formulation=(
                "available evidence supports "
                "persistent return to unresolved "
                "problems without establishing "
                "universality across contexts."
            ),
            epistemic_class="strong_inference",
            evidence_refs=(evidence.id,),
            confidence="supported",
        )
    )

    relationship = graph.add_relationship(
        Relationship(
            left_id=category.id,
            segue="manifests",
            right_id=evidence.id,
            scope=graph.character_id,
            evidence_refs=(evidence.id,),
            epistemic_class="strong_inference",
        )
    )

    projection = graph.projection(
        guise.manifest
    )

    assert health()["status"] == "ok"
    assert len(guise.manifest["domains"]) == 20
    assert (
        guise.manifest[
            "category_placements"
        ]
        == 100
    )
    assert evidence.id in graph.evidence
    assert category.id in graph.categories
    assert (
        relationship.id
        in graph.relationships
    )
    assert (
        projection["character_id"]
        == "demonstration_character"
    )
    assert (
        projection["authority_effect"]
        == "none"
    )
    assert (
        projection["authoritative"]
        is False
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "specialization": "guise",
                "domains": 20,
                "category_placements": 100,
                "evidence_preserved": True,
                "composition_by_reference": True,
                "character_specific_hardcoding": (
                    False
                ),
                "projection_digest": (
                    projection[
                        "projection_digest"
                    ]
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
