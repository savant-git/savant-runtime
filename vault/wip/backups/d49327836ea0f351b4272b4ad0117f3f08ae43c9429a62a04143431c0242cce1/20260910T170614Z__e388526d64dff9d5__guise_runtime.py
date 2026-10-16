#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from guise import Guise
from guise_arc import CharacterArcGraph
from guise_behavior import (
    CharacterBehaviorEngine,
)
from guise_compare import CharacterComparator
from guise_continuity import (
    GuiseContinuitySentinel,
    KnowledgeLeakDetector,
)
from guise_counterfactual import (
    CharacterCounterfactualEngine,
)
from guise_debt import NarrativeDebtLedger
from guise_falsify import CharacterFalsifier
from guise_generate import GuiseGenerator
from guise_interrogate import GuiseInterrogator
from guise_pressure import PressureEngine
from guise_projection import ProjectionIndex
from guise_provider import (
    GuiseCorpusInterpreter,
    GuiseProviderRegistry,
)
from guise_reconcile import (
    MinimumDifferenceReconciler,
)
from guise_relationship import (
    CharacterRelationshipEngine,
)
from guise_scene import CharacterSceneProjector
from guise_state import CharacterStateProjector
from guise_store import GuiseStore
from guise_temporal import CharacterTemporalIndex


class GuiseRuntime:
    def __init__(
        self,
        *,
        guise: Guise | None = None,
        store: GuiseStore | None = None,
        providers: GuiseProviderRegistry | None = None,
    ) -> None:
        self.guise = guise or Guise()
        self.store = store or GuiseStore()
        self.providers = (
            providers
            or GuiseProviderRegistry()
        )

        self.state = CharacterStateProjector()
        self.temporal = CharacterTemporalIndex()
        self.relationship = (
            CharacterRelationshipEngine()
        )
        self.arc = CharacterArcGraph()
        self.debt = NarrativeDebtLedger()
        self.scene = CharacterSceneProjector()
        self.compare = CharacterComparator(
            self.guise
        )

        self.counterfactual = (
            CharacterCounterfactualEngine()
        )
        self.interrogate = GuiseInterrogator(
            self.guise
        )
        self.pressure = PressureEngine()
        self.behavior = CharacterBehaviorEngine()
        self.falsify = CharacterFalsifier()
        self.reconcile = (
            MinimumDifferenceReconciler()
        )
        self.continuity = (
            GuiseContinuitySentinel()
        )
        self.knowledge_leaks = (
            KnowledgeLeakDetector()
        )
        self.projections = ProjectionIndex()

        self.corpus = GuiseCorpusInterpreter(
            self.guise,
            self.providers,
        )

        self.generate = GuiseGenerator(
            self.guise,
            self.providers,
        )

    def new_character(
        self,
        character_id: str,
        *,
        display_name: str | None = None,
    ) -> Any:
        return self.guise.new_character(
            character_id,
            display_name=display_name,
        )

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "owner": "carbon",
            "specialization": "guise",
            "provider_registry": (
                self.providers.status()
            ),
            "store": self.store.status(),
            "projection_index": (
                self.projections.status()
            ),
            "bitemporal_model": True,
            "relationship_conditioning": True,
            "arc_graph": True,
            "narrative_debt": True,
            "scene_projection": True,
            "cross_character_comparison": True,
            "falsification": True,
            "minimum_difference_reconciliation": (
                True
            ),
            "character_specific_hardcoding": (
                False
            ),
            "automatic_canonization": False,
            "authority_effect": "none",
        }
