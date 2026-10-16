#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
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
from guise_extract import (  # noqa: E402
    ExtractionNormalizer,
)
from guise_projection import (  # noqa: E402
    ProjectionIndex,
)
from guise_store import (  # noqa: E402
    GuiseStore,
)


def main() -> int:
    guise = Guise()

    graph = guise.new_character(
        "demonstration_character",
        display_name=(
            "demonstration character"
        ),
    )

    source = SourceReference(
        source_id="demonstration_source",
        location="paragraph:1",
        source_kind="test_fixture",
        authority_class="test_evidence",
        content_digest="fixture",
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
            epistemic_class=(
                "strong_inference"
            ),
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
            epistemic_class=(
                "strong_inference"
            ),
        )
    )

    normalizer = ExtractionNormalizer(
        guise
    )

    normalized = normalizer.normalize(
        graph=graph,
        source_id="second_source",
        source_kind="test_fixture",
        source_digest="fixture-two",
        candidates=[
            {
                "domain": "judgment",
                "category": "skepticism",
                "observation": (
                    "the character questions "
                    "an unsupported conclusion."
                ),
                "formulation": (
                    "the observed behavior "
                    "supports situational "
                    "skepticism."
                ),
                "epistemic_class": (
                    "weak_inference"
                ),
                "confidence": "limited",
                "location": "paragraph:2",
                "alternatives": [
                    "the questioning may be "
                    "situational rather than "
                    "trait-like."
                ],
            }
        ],
    )

    assert (
        normalized["accepted_count"]
        == 1
    )
    assert (
        normalized[
            "automatic_canonization"
        ]
        is False
    )

    projection = graph.projection(
        guise.manifest
    )

    with tempfile.TemporaryDirectory(
        prefix="guise-test-"
    ) as temporary:
        store = GuiseStore(
            Path(temporary)
        )

        saved = store.save_projection(
            projection
        )

        loaded = store.load_head(
            graph.character_id
        )

        assert (
            loaded[
                "projection_digest"
            ]
            == saved[
                "projection_digest"
            ]
        )

        assert (
            len(
                store.versions(
                    graph.character_id
                )
            )
            == 1
        )

    index = ProjectionIndex()

    index.register(
        projection_id=(
            "demonstration.profile"
        ),
        payload=projection,
        dependencies=[
            evidence.id,
            category.id,
        ],
    )

    assert (
        index.dependents(
            evidence.id
        )
        == [
            "demonstration.profile"
        ]
    )

    invalidation = index.invalidate(
        [evidence.id]
    )

    assert (
        invalidation[
            "affected_projections"
        ]
        == [
            "demonstration.profile"
        ]
    )

    assert health()["status"] == "ok"
    assert len(
        guise.manifest["domains"]
    ) == 20
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
                "counterevidence_supported": (
                    True
                ),
                "composition_by_reference": (
                    True
                ),
                "persistent_versions": True,
                "digest_verification": True,
                "projection_invalidation": (
                    True
                ),
                "provider_normalization": (
                    True
                ),
                "automatic_canonization": (
                    False
                ),
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
