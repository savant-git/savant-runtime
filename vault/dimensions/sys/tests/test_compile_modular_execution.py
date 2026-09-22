#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "compile_modular_execution.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "compile_modular_execution",
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


compiler = load_module()


class ModularExecutionCompilationTests(
    unittest.TestCase
):

    def test_three_execution_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.EXECUTION_STATES
            ),
            3,
        )

        self.assertEqual(
            len(
                set(
                    compiler.EXECUTION_STATES
                )
            ),
            3,
        )

    def test_nine_execution_phases(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.EXECUTION_PHASES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.EXECUTION_PHASES
                )
            ),
            9,
        )

    def test_nine_required_preflights(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.REQUIRED_PREFLIGHTS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.REQUIRED_PREFLIGHTS
                )
            ),
            9,
        )

    def test_nine_completion_evidence_items(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.REQUIRED_EVIDENCE
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.REQUIRED_EVIDENCE
                )
            ),
            9,
        )

    def accepted_decision(
        self,
    ) -> dict[str, object]:
        return {
            "id": "accepted-decision:test",
            "proposal_id": "proposal:test",
            "candidate_id": "candidate:test",
            "candidate_ordinal": 1,
            "phase": "moods",
            "source_path": (
                "/root/savant-runtime/"
                "authority_graph/registries/"
                "modular_moods.json"
            ),
            "source_finding_key": (
                "canonical_mood_mismatch"
            ),
            "authorized_action": "supersede",
            "authority": "decision",
            "state": "accepted",
            "immutable": True,
            "mutation_authorized": True,
            "preservation_requirements": [],
            "validation_requirements": [],
            "rollback_requirements": [],
        }

    def test_compiled_unit_remains_blocked(
        self,
    ) -> None:
        unit = compiler.compile_decision(
            self.accepted_decision()
        )

        self.assertEqual(
            unit.state,
            "blocked",
        )

        self.assertFalse(
            unit.implementation_authorized
        )

        self.assertTrue(
            unit.mutation_authorized
        )

        self.assertIn(
            "current implementation has not been semantically reviewed",
            unit.blockers,
        )

    def test_execution_identity_is_stable(
        self,
    ) -> None:
        first = (
            compiler.execution_identity(
                "decision:test",
                "/root/savant-runtime/example",
                "supersede",
            )
        )

        second = (
            compiler.execution_identity(
                "decision:test",
                "/root/savant-runtime/example",
                "supersede",
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_unknown_phase_normalizes_to_verification(
        self,
    ) -> None:
        self.assertEqual(
            compiler.normalize_phase(
                "unknown"
            ),
            "verification",
        )


if __name__ == "__main__":
    unittest.main()
