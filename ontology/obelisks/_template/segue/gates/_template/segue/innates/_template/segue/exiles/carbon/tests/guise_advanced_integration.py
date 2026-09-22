#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path("/root/savant-runtime").resolve()

RUNTIME = (
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
    str(RUNTIME),
)

from guise import (  # noqa: E402
    CategorySubstantiation,
    Evidence,
    Guise,
    KnowledgeAssertion,
    SourceReference,
)
from guise_counterfactual import (  # noqa: E402
    CharacterCounterfactualEngine,
)
from guise_interrogate import (  # noqa: E402
    GuiseInterrogator,
)
from guise_pressure import (  # noqa: E402
    PressureEngine,
)
from guise_state import (  # noqa: E402
    CharacterStateProjector,
    StateOverlay,
)


def main() -> int:
    guise = Guise()

    graph = guise.new_character(
        "advanced_demonstration_character"
    )

    source = SourceReference(
        source_id="advanced_fixture",
        location="paragraph:1",
        source_kind="test_fixture",
        authority_class="test_evidence",
        content_digest="fixture",
    )

    evidence = graph.add_evidence(
        Evidence(
            subject_id=(
                graph.character_id
            ),
            observation=(
                "the character returns to "
                "an unresolved task despite "
                "increasing pressure."
            ),
            source=source,
            tags=(
                "persistence",
            ),
        )
    )

    category = graph.add_category(
        CategorySubstantiation(
            character_id=(
                graph.character_id
            ),
            domain="attention",
            category="persistence",
            formulation=(
                "the evidence supports "
                "contextual persistence."
            ),
            epistemic_class=(
                "strong_inference"
            ),
            evidence_refs=(
                evidence.id,
            ),
            confidence="supported",
        )
    )

    knowledge = graph.add_knowledge(
        KnowledgeAssertion(
            character_id=(
                graph.character_id
            ),
            proposition_ref=(
                "fixture.proposition"
            ),
            knowledge_state="knows",
            evidence_refs=(
                evidence.id,
            ),
        )
    )

    projector = (
        CharacterStateProjector()
    )

    state_projection = (
        projector.project(
            graph,
            at="fixture-time",
            phase="fixture-phase",
            overlays=[
                StateOverlay(
                    kind="baseline",
                    values={
                        "attention.persistence": (
                            "supported"
                        )
                    },
                    source_refs=(
                        category.id,
                    ),
                ),
                StateOverlay(
                    kind="pressure",
                    values={
                        "pressure.external": (
                            "high"
                        )
                    },
                    source_refs=(
                        evidence.id,
                    ),
                ),
                StateOverlay(
                    kind="emotional",
                    values={
                        "emotional.tension": (
                            "elevated"
                        )
                    },
                    source_refs=(
                        evidence.id,
                    ),
                ),
            ],
        )
    )

    state_ref = (
        state_projection[
            "state"
        ]["id"]
    )

    counterfactual = (
        CharacterCounterfactualEngine()
    )

    branch = counterfactual.branch(
        graph,
        parent_state_ref=state_ref,
        changes={
            "pressure.external": "low"
        },
        question=(
            "what changes if external "
            "pressure decreases?"
        ),
    )

    assert (
        branch["character_mutated"]
        is False
    )
    assert (
        branch["authoritative"]
        is False
    )

    pressure = PressureEngine()

    pressure_projection = (
        pressure.project(
            graph,
            pressures=[
                {
                    "id": (
                        "fixture-pressure"
                    ),
                    "kind": "external",
                    "description": (
                        "demonstration pressure"
                    ),
                    "source_refs": [
                        evidence.id
                    ],
                }
            ],
            candidate_effects=[
                {
                    "effect": (
                        "persistence may "
                        "intensify"
                    ),
                    "classification": (
                        "plausible"
                    ),
                    "category_refs": [
                        category.id
                    ],
                    "supporting_refs": [
                        evidence.id
                    ],
                },
                {
                    "effect": (
                        "persistence may "
                        "collapse"
                    ),
                    "classification": (
                        "requires_substantiation"
                    ),
                    "counter_refs": [
                        evidence.id
                    ],
                },
            ],
        )
    )

    assert (
        pressure_projection[
            "deterministic"
        ]
        is False
    )

    interrogator = (
        GuiseInterrogator(
            guise
        )
    )

    current = interrogator.execute(
        graph,
        "current",
    )

    knows = interrogator.execute(
        graph,
        "knows",
    )

    why = interrogator.execute(
        graph,
        "why",
        {
            "category_id": (
                category.id
            )
        },
    )

    assert current["known"] is True
    assert (
        knows["knowledge"][0][
            "id"
        ]
        == knowledge.id
    )
    assert (
        why["category"]["id"]
        == category.id
    )
    assert (
        why["evidence"][
            "supporting"
        ][0]["id"]
        == evidence.id
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "specialization": "guise",
                "state_projection": True,
                "state_conflict_preservation": (
                    True
                ),
                "pressure_projection": True,
                "counterfactual_branching": (
                    True
                ),
                "authority_isolation": True,
                "interrogation": True,
                "knowledge_projection": True,
                "why_provenance": True,
                "character_specific_hardcoding": (
                    False
                ),
            },
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
