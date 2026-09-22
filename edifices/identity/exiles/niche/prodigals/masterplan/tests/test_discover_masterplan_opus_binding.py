#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "discover_masterplan_opus_binding.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "discover_masterplan_opus_binding",
            MODULE_PATH,
        )
    )

    if specification is None:
        raise RuntimeError(
            "unable to create module specification"
        )

    if specification.loader is None:
        raise RuntimeError(
            "module specification lacks loader"
        )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


discovery = load_module()


class MasterplanOpusBindingDiscoveryTests(
    unittest.TestCase
):

    def test_nine_artifact_classes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                discovery.ARTIFACT_CLASSES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    discovery.ARTIFACT_CLASSES
                )
            ),
            9,
        )

    def test_nine_binding_capabilities(
        self,
    ) -> None:
        self.assertEqual(
            len(
                discovery.BINDING_CAPABILITIES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    discovery.BINDING_CAPABILITIES
                )
            ),
            9,
        )

    def test_provider_classification(
        self,
    ) -> None:
        result = discovery.classify_artifact(
            Path(
                "/root/savant-runtime/"
                "opus/runtime/providers/openai.py"
            ),
            "",
        )

        self.assertEqual(
            result,
            "provider",
        )

    def test_protocol_classification(
        self,
    ) -> None:
        result = discovery.classify_artifact(
            Path(
                "/root/savant-runtime/"
                "opus/runtime/protocol/request.py"
            ),
            "",
        )

        self.assertEqual(
            result,
            "protocol",
        )

    def test_capability_detection(
        self,
    ) -> None:
        capabilities, evidence = (
            discovery.detect_capabilities(
                Path(
                    "/root/savant-runtime/"
                    "opus/runtime/router.py"
                ),
                (
                    "def select_provider():\n"
                    "    publish('selected')\n"
                    "    return provider.call()\n"
                ),
                (
                    "select_provider",
                ),
            )
        )

        self.assertIn(
            "provider_discovery",
            capabilities,
        )

        self.assertIn(
            "provider_routing",
            capabilities,
        )

        self.assertIn(
            "provider_execution",
            capabilities,
        )

        self.assertIn(
            "event_publication",
            capabilities,
        )

        self.assertTrue(
            evidence
        )

    def test_python_symbol_discovery(
        self,
    ) -> None:
        source = (
            "import json\n"
            "from pathlib import Path\n"
            "\n"
            "class Router:\n"
            "    pass\n"
            "\n"
            "def route():\n"
            "    return None\n"
        )

        with tempfile.TemporaryDirectory() as raw:
            path = (
                Path(
                    raw
                )
                / "router.py"
            )

            path.write_text(
                source,
                encoding="utf-8",
            )

            symbols, imports = (
                discovery.python_symbols(
                    path,
                    source,
                )
            )

        self.assertEqual(
            symbols,
            (
                "Router",
                "route",
            ),
        )

        self.assertEqual(
            imports,
            (
                "json",
                "pathlib",
            ),
        )

    def test_historical_candidate_not_selected(
        self,
    ) -> None:
        historical = discovery.CandidateRoot(
            path="/root/savant-runtime/legacy/opus",
            exists=True,
            file_count=100,
            authority_score=0,
            historical_score=100,
            implementation_score=100,
            ranking_score=-300,
            classification="historical",
            evidence=(),
        )

        current = discovery.CandidateRoot(
            path="/root/savant-runtime/current/opus",
            exists=True,
            file_count=10,
            authority_score=1,
            historical_score=0,
            implementation_score=20,
            ranking_score=23,
            classification="partial_candidate",
            evidence=(),
        )

        selected = discovery.select_candidate(
            (
                historical,
                current,
            )
        )

        self.assertEqual(
            selected,
            current,
        )

    def test_tied_candidates_require_authority(
        self,
    ) -> None:
        first = discovery.CandidateRoot(
            path="/root/savant-runtime/a/opus",
            exists=True,
            file_count=10,
            authority_score=1,
            historical_score=0,
            implementation_score=20,
            ranking_score=23,
            classification="partial_candidate",
            evidence=(),
        )

        second = discovery.CandidateRoot(
            path="/root/savant-runtime/b/opus",
            exists=True,
            file_count=10,
            authority_score=1,
            historical_score=0,
            implementation_score=20,
            ranking_score=23,
            classification="partial_candidate",
            evidence=(),
        )

        selected = discovery.select_candidate(
            (
                first,
                second,
            )
        )

        self.assertIsNone(
            selected
        )

    def test_semantic_digest_is_stable(
        self,
    ) -> None:
        first = discovery.semantic_digest(
            {
                "b": 2,
                "a": 1,
            }
        )

        second = discovery.semantic_digest(
            {
                "a": 1,
                "b": 2,
            }
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
