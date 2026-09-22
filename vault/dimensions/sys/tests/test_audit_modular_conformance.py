#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import itertools
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "audit_modular_conformance.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "audit_modular_conformance",
        MODULE_PATH,
    )

    if specification is None:
        raise RuntimeError(
            "unable to create audit module specification"
        )

    if specification.loader is None:
        raise RuntimeError(
            "audit module specification lacks loader"
        )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


audit = load_module()


class ModularConformanceAuditTests(unittest.TestCase):

    def test_nine_canonical_moods(self) -> None:
        self.assertEqual(
            len(audit.CANONICAL_MOODS),
            9,
        )

        self.assertEqual(
            len(set(audit.CANONICAL_MOODS)),
            9,
        )

    def test_thirty_six_mood_pairs(self) -> None:
        pairs = tuple(
            itertools.combinations(
                audit.CANONICAL_MOODS,
                2,
            )
        )

        self.assertEqual(
            len(pairs),
            36,
        )

    def test_fulcrum_replaces_segue_mood(self) -> None:
        self.assertIn(
            "fulcrum",
            audit.CANONICAL_MOODS,
        )

        self.assertNotIn(
            "segue",
            audit.CANONICAL_MOODS,
        )

    def test_digest_is_deterministic(self) -> None:
        self.assertEqual(
            audit.digest(b"same"),
            audit.digest(b"same"),
        )

    def test_required_authority_check_returns_list(
        self,
    ) -> None:
        findings = (
            audit.required_file_findings()
        )

        self.assertIsInstance(
            findings,
            list,
        )


if __name__ == "__main__":
    unittest.main()
