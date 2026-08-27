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
from runtime.opus_ai_adapter import (
    OpusAIAdapter,
)


CONFIG = (
    ROOT
    / "config"
    / "ai_capabilities.yaml"
)


class OpusAIAdapterTests(unittest.TestCase):

    def adapter(
        self,
        environ=None,
    ) -> OpusAIAdapter:
        return OpusAIAdapter(
            AICapabilityRegistry(
                CONFIG,
                environ=environ or {},
            )
        )

    def test_native_without_keys(
        self,
    ) -> None:
        adapter = self.adapter({})

        self.assertEqual(
            adapter.mode(),
            "native",
        )

        self.assertFalse(
            adapter.has_capability(
                "generate"
            )
        )

    def test_key_activates_provider(
        self,
    ) -> None:
        adapter = self.adapter(
            {
                "OPENAI_API_KEY":
                    "test-only",
            }
        )

        self.assertTrue(
            adapter.has_provider(
                "openai"
            )
        )

        self.assertTrue(
            adapter.has_capability(
                "generate"
            )
        )

    def test_capability_selection(
        self,
    ) -> None:
        adapter = self.adapter(
            {
                "OPENAI_API_KEY":
                    "test-only",
                "ANTHROPIC_API_KEY":
                    "test-only",
            }
        )

        result = adapter.select(
            "generate",
            preferred_providers=(
                "anthropic",
                "openai",
            ),
        )

        self.assertEqual(
            result.selected,
            "anthropic",
        )

        self.assertEqual(
            result.mode,
            "orchestrated",
        )

    def test_missing_capability_falls_native(
        self,
    ) -> None:
        adapter = self.adapter(
            {
                "OPENAI_API_KEY":
                    "test-only",
            }
        )

        result = adapter.select(
            "nonexistent-capability"
        )

        self.assertIsNone(
            result.selected
        )

        self.assertEqual(
            result.mode,
            "native",
        )

        self.assertTrue(
            result.native_fallback
        )

    def test_element_contract_resolves(
        self,
    ) -> None:
        adapter = self.adapter(
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
                    "analyze",
                ],
                "required_capabilities": [
                    "generate",
                ],
            }
        }

        resolved = adapter.resolve_element(
            record
        )

        self.assertTrue(
            resolved["eligible"]
        )

        self.assertTrue(
            resolved["ai_active"]
        )

        self.assertEqual(
            resolved[
                "missing_required_capabilities"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
