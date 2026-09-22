#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ai_capabilities import AICapabilityRegistry


CONFIG = ROOT / "config" / "ai_capabilities.yaml"


class AICapabilityTests(unittest.TestCase):

    def test_zero_keys_is_native_and_valid(self) -> None:
        registry = AICapabilityRegistry(
            CONFIG,
            environ={},
        )

        self.assertEqual(registry.mode(), "native")
        self.assertEqual(registry.usable_providers(), ())
        self.assertEqual(registry.capabilities(), ())

    def test_one_key_activates_augmented_mode(self) -> None:
        registry = AICapabilityRegistry(
            CONFIG,
            environ={
                "OPENAI_API_KEY": "test-only",
            },
        )

        self.assertEqual(registry.mode(), "augmented")
        self.assertEqual(
            registry.usable_providers(),
            ("openai",),
        )
        self.assertIn(
            "generate",
            registry.capabilities(),
        )

    def test_multiple_keys_activate_orchestration(self) -> None:
        registry = AICapabilityRegistry(
            CONFIG,
            environ={
                "OPENAI_API_KEY": "test-only",
                "ANTHROPIC_API_KEY": "test-only",
            },
        )

        self.assertEqual(
            registry.mode(),
            "orchestrated",
        )

        self.assertEqual(
            registry.usable_providers(),
            (
                "anthropic",
                "openai",
            ),
        )

    def test_secrets_are_never_projected(self) -> None:
        secret = "DO-NOT-LEAK-THIS"

        registry = AICapabilityRegistry(
            CONFIG,
            environ={
                "OPENAI_API_KEY": secret,
            },
        )

        projection = str(
            registry.projection()
        )

        self.assertNotIn(
            secret,
            projection,
        )

    def test_opus_ready_element_has_native_fallback(self) -> None:
        registry = AICapabilityRegistry(
            CONFIG,
            environ={},
        )

        contract = registry.element_contract(
            opus_ready=True,
            capabilities=(
                "analyze",
                "generate",
            ),
        )

        self.assertTrue(
            contract["eligible"]
        )

        self.assertEqual(
            contract["native_fallback"],
            "required",
        )

        self.assertEqual(
            contract["authority_effect"],
            "none",
        )

        self.assertEqual(
            contract["mutation_effect"],
            "none",
        )

        self.assertEqual(
            contract["available_capabilities"],
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
