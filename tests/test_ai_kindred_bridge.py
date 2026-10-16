#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ai_capabilities import (
    AICapabilityRegistry,
)
from runtime.ai_kindred_bridge import (
    AIKindredBridge,
)
from lexicon.kindred.discipline_engine import (
    DisciplineEngine,
)


AI_CONFIG = (
    ROOT
    / "config"
    / "ai_capabilities.yaml"
)


class AIKindredBridgeTests(
    unittest.TestCase
):

    def bridge(
        self,
        environ=None,
    ) -> AIKindredBridge:
        return AIKindredBridge(
            ai_registry=AICapabilityRegistry(
                AI_CONFIG,
                environ=environ or {},
            ),
            kindred=DisciplineEngine(),
        )

    def test_provider_capabilities_project_in_native_mode(
        self,
    ) -> None:
        bridge = self.bridge({})

        self.assertEqual(
            bridge.ai.mode(),
            "native",
        )

        self.assertGreater(
            len(
                bridge.provider_edges()
            ),
            0,
        )

    def test_explicit_element_contract_projects_edges(
        self,
    ) -> None:
        bridge = self.bridge({})

        record = {
            "ai": {
                "eligible": True,
                "capabilities": [
                    "analyze",
                    "generate",
                ],
            }
        }

        edges = bridge.element_edges(
            "exile:test",
            record,
        )

        self.assertEqual(
            len(edges),
            2,
        )

    def test_opus_ready_without_explicit_capabilities_is_compatible(
        self,
    ) -> None:
        bridge = self.bridge({})

        record = {
            "orchestration": {
                "opus_ready": True,
            }
        }

        edges = bridge.element_edges(
            "exile:test",
            record,
        )

        self.assertEqual(
            edges,
            [],
        )

        resolved = (
            bridge.eligibility.resolve(
                record
            )
        )

        self.assertTrue(
            resolved["eligible"]
        )

        self.assertTrue(
            resolved[
                "native_operational"
            ]
        )

    def test_key_activates_declared_capability(
        self,
    ) -> None:
        bridge = self.bridge(
            {
                "OPENAI_API_KEY":
                    "test-only",
            }
        )

        record = {
            "ai": {
                "eligible": True,
                "capabilities": [
                    "generate",
                ],
            }
        }

        resolved = (
            bridge.eligibility.resolve(
                record
            )
        )

        self.assertTrue(
            resolved["ai_active"]
        )

        self.assertIn(
            "generate",
            resolved[
                "usable_capabilities"
            ],
        )

    def test_capability_edges_are_kindred_capability_discipline(
        self,
    ) -> None:
        bridge = self.bridge({})

        edge = (
            bridge.provider_edges()[0]
        )

        normalized = (
            bridge.kindred.normalize_edge(
                edge
            )
        )

        self.assertEqual(
            normalized["discipline"],
            "discipline:capability",
        )

        self.assertEqual(
            normalized["steward"],
            "Opus",
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
