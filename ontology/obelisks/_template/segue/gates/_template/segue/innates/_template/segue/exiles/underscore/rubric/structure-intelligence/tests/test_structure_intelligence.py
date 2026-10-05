#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


SOURCE = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "underscore/rubric/structure-intelligence/source/"
    "compile_structure_intelligence.py"
)


def load_subject() -> ModuleType:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"source unavailable: {SOURCE}")

    specification = importlib.util.spec_from_file_location(
        "savant_structure_intelligence",
        SOURCE,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError(f"unable to load source: {SOURCE}")

    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


class StructureIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.subject = load_subject()

    def test_canonical_ninefold_sets(self) -> None:
        self.assertEqual(len(self.subject.IDENTITY_LEVELS), 9)
        self.assertEqual(len(self.subject.CONTENT_LEVELS), 9)
        self.assertEqual(len(self.subject.MOODS), 9)
        self.assertEqual(len(self.subject.KINDRED_TREES), 9)
        self.assertEqual(len(self.subject.KINDRED_COORDINATES), 9)
        self.assertEqual(len(self.subject.RUBRIC_FACILITIES), 9)
        self.assertEqual(len(self.subject.CABAL_LAWS), 9)

    def test_owner_inference(self) -> None:
        owner, confidence = self.subject.infer_owner(
            "ontology/obelisks/example/segue/gates/example/"
            "segue/innates/example/segue/exiles/opus/"
            "rubric/router/source/route.py"
        )

        self.assertEqual(owner, "opus")
        self.assertGreaterEqual(confidence, 0.90)

    def test_read_only_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            source = (
                root
                / "ontology/obelisks/example/segue/gates/example/"
                "segue/innates/example/segue/exiles/opus/"
                "rubric/router/source"
            )

            source.mkdir(parents=True)

            file_path = source / "route.py"

            file_path.write_text(
                "from pathlib import Path\n"
                "VALUE = 'aria kindred dependency'\n",
                encoding="utf-8",
            )

            before = file_path.read_bytes()

            analysis = self.subject.compile_analysis(
                root=root,
                maximum_files=100,
                maximum_text_bytes=100_000,
            )

            after = file_path.read_bytes()

            self.assertEqual(before, after)
            self.assertFalse(analysis.summary["mutation_performed"])
            self.assertFalse(analysis.summary["migration_authorized"])
            self.assertEqual(analysis.summary["file_count"], 1)
            self.assertEqual(analysis.files[0].semantic_owner, "opus")
            self.assertIn("aria", analysis.files[0].moods)
            self.assertIn("kindred", analysis.files[0].kindred_terms)

    def test_unknown_source_owner_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "miscellaneous"
            source.mkdir(parents=True)

            file_path = source / "orphan.py"
            file_path.write_text("VALUE = 1\n", encoding="utf-8")

            analysis = self.subject.compile_analysis(
                root=root,
                maximum_files=100,
                maximum_text_bytes=100_000,
            )

            self.assertEqual(
                analysis.summary["unresolved_source_owner_count"],
                1,
            )

            self.assertTrue(
                any(
                    conflict["kind"] == "unresolved-source-owner"
                    and conflict["path"] == "miscellaneous/orphan.py"
                    for conflict in analysis.ownership_conflicts
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
