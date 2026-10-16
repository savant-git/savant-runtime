#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path("/root/savant-runtime")

VALIDATOR = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "validate_primary_architecture.py"
)

PROJECT_INSTRUCTIONS = (
    ROOT
    / "vault"
    / "dimensions"
    / "canon"
    / "PROJECT_INSTRUCTIONS.md"
)

PRIMARY_LAW = (
    ROOT
    / "ontology"
    / "obelisks"
    / "segue"
    / "authority_graph"
    / "canon"
    / "PRIMARY_ARCHITECTURAL_LAW.md"
)


def load_validator():
    specification = importlib.util.spec_from_file_location(
        "validate_primary_architecture",
        VALIDATOR,
    )

    if specification is None:
        raise RuntimeError(
            "unable to create validator module specification"
        )

    if specification.loader is None:
        raise RuntimeError(
            "validator module specification lacks loader"
        )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


validator = load_validator()


class PrimaryArchitectureTests(unittest.TestCase):

    def test_authoritative_files_exist(self) -> None:
        self.assertTrue(
            PROJECT_INSTRUCTIONS.is_file()
        )
        self.assertTrue(
            PRIMARY_LAW.is_file()
        )

    def test_exactly_nine_moods(self) -> None:
        self.assertEqual(
            len(validator.CANONICAL_MOODS),
            9,
        )
        self.assertEqual(
            len(
                set(
                    validator.CANONICAL_MOODS
                )
            ),
            9,
        )

    def test_exactly_nine_footprints(self) -> None:
        self.assertEqual(
            len(validator.FOOTPRINTS),
            9,
        )
        self.assertEqual(
            len(
                set(
                    validator.FOOTPRINTS
                )
            ),
            9,
        )

    def test_exactly_three_combination_mechanisms(
        self,
    ) -> None:
        self.assertEqual(
            len(
                validator.CONSTRUCTION_MECHANISMS
            ),
            3,
        )

    def test_project_instructions_define_all_moods(
        self,
    ) -> None:
        content = PROJECT_INSTRUCTIONS.read_text(
            encoding="utf-8"
        )

        checks = validator.check_moods(
            content
        )

        self.assertEqual(
            len(checks),
            9,
        )

        self.assertTrue(
            all(
                check.passed
                for check in checks
            )
        )

    def test_project_instructions_define_cardinality(
        self,
    ) -> None:
        content = PROJECT_INSTRUCTIONS.read_text(
            encoding="utf-8"
        )

        checks = (
            validator.check_cardinality_policy(
                content
            )
        )

        self.assertEqual(
            len(checks),
            3,
        )

        self.assertTrue(
            all(
                check.passed
                for check in checks
            )
        )

    def test_primary_law_defines_three_mechanisms(
        self,
    ) -> None:
        content = PRIMARY_LAW.read_text(
            encoding="utf-8"
        )

        checks = validator.check_mechanisms(
            content
        )

        self.assertEqual(
            len(checks),
            3,
        )

        self.assertTrue(
            all(
                check.passed
                for check in checks
            )
        )

    def test_integrated_validator_passes(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            process.returncode,
            0,
            msg=(
                process.stdout
                + "\n"
                + process.stderr
            ),
        )

        payload = json.loads(
            process.stdout
        )

        self.assertTrue(
            payload["passed"]
        )
        self.assertEqual(
            payload["canonical_mood_count"],
            9,
        )
        self.assertEqual(
            payload["footprint_count"],
            9,
        )
        self.assertEqual(
            payload[
                "combination_mechanism_count"
            ],
            3,
        )
        self.assertEqual(
            payload["failure_count"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
