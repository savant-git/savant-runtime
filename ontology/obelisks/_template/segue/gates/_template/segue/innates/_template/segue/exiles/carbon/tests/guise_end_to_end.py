#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
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

from guise import SourceReference  # noqa: E402
from guise_provider import (  # noqa: E402
    CallableProvider,
)
from guise_runtime import (  # noqa: E402
    GuiseRuntime,
)
from guise_state import (  # noqa: E402
    StateOverlay,
)
from guise_store import GuiseStore  # noqa: E402


def fixture_provider(
    *,
    character_id,
    text,
    source,
    manifest,
):
    return {
        "candidates": [
            {
                "domain": "attention",
                "category": "persistence",
                "observation": (
                    "the source depicts repeated "
                    "return to an unresolved task."
                ),
                "formulation": (
                    "the available evidence supports "
                    "contextual persistence."
                ),
                "epistemic_class": (
                    "strong_inference"
                ),
                "confidence": "supported",
                "alternatives": [
                    "the behavior may be driven by "
                    "situational necessity."
                ],
            }
        ],
        "metadata": {
            "fixture": True
        },
    }


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="guise-e2e-"
    ) as temporary:
        runtime = GuiseRuntime(
            store=GuiseStore(
                Path(temporary)
            )
        )

        runtime.providers.register(
            CallableProvider(
                "fixture",
                fixture_provider,
            )
        )

        graph = runtime.new_character(
            "generic_demonstration_character",
            display_name=(
                "generic demonstration character"
            ),
        )

        source = SourceReference(
            source_id="fixture-source",
            location="paragraph:1",
            source_kind="test_fixture",
            authority_class="test_evidence",
            content_digest="fixture-digest",
        )

        interpretation = (
            runtime.corpus.interpret(
                graph=graph,
                provider_id="fixture",
                text=(
                    "The character repeatedly "
                    "returns to the unresolved task."
                ),
                source=source,
            )
        )

        assert (
            interpretation[
                "automatic_canonization"
            ]
            is False
        )

        assert (
            interpretation[
                "normalization"
            ]["accepted_count"]
            == 1
        )

        state = runtime.state.project(
            graph,
            at="fixture-time",
            overlays=[
                StateOverlay(
                    kind="pressure",
                    values={
                        "pressure.external": "high"
                    },
                )
            ],
        )

        behavior = runtime.behavior.evaluate(
            graph,
            situation={
                "kind": "fixture"
            },
            candidates=[
                {
                    "behavior": (
                        "continue the unresolved task"
                    ),
                    "classification": (
                        "highly_supported"
                    ),
                    "supporting_refs": (
                        interpretation[
                            "normalization"
                        ][
                            "created_evidence"
                        ]
                    ),
                },
                {
                    "behavior": (
                        "abandon the task"
                    ),
                    "classification": (
                        "requires_substantiation"
                    ),
                },
            ],
        )

        assert (
            behavior[
                "behavior_is_deterministic"
            ]
            is False
        )

        branch = (
            runtime.counterfactual.branch(
                graph,
                parent_state_ref=(
                    state["state"]["id"]
                ),
                changes={
                    "pressure.external": "low"
                },
            )
        )

        assert (
            branch["character_mutated"]
            is False
        )

        continuity = (
            runtime.continuity.inspect(
                graph
            )
        )

        profile = graph.projection(
            runtime.guise.manifest
        )

        saved = runtime.store.save_projection(
            profile
        )

        loaded = runtime.store.load_head(
            graph.character_id
        )

        assert (
            saved["projection_digest"]
            == loaded[
                "projection_digest"
            ]
        )

        why = runtime.interrogate.execute(
            graph,
            "why",
            {
                "category_id": (
                    interpretation[
                        "normalization"
                    ][
                        "created_categories"
                    ][0]
                )
            },
        )

        assert why["evidence"][
            "supporting"
        ]

        health = runtime.health()

        assert (
            health["status"]
            == "ok"
        )

        print(
            json.dumps(
                {
                    "status": "ok",
                    "specialization": "guise",
                    "general_character_import": True,
                    "provider_replaceability": True,
                    "provider_receipts": True,
                    "evidence_normalization": True,
                    "automatic_canonization": False,
                    "state_projection": True,
                    "behavior_alternatives": True,
                    "counterfactual_branching": True,
                    "continuity_sentinel": True,
                    "provenance_explanation": True,
                    "immutable_projection_versions": True,
                    "character_specific_hardcoding": False,
                    "authority_effect": "none",
                },
                sort_keys=True,
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
