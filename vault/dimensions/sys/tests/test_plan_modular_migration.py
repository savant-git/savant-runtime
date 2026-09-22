#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "plan_modular_migration.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "plan_modular_migration",
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


planner = load_module()


class ModularMigrationPlannerTests(
    unittest.TestCase
):

    def test_nine_phases(self) -> None:
        self.assertEqual(
            len(
                planner.MIGRATION_PHASES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.MIGRATION_PHASES
                )
            ),
            9,
        )

    def test_nine_action_classes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.ACTION_CLASSES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.ACTION_CLASSES
                )
            ),
            9,
        )

    def test_missing_authority_refuses(
        self,
    ) -> None:
        finding = {
            "key": (
                "missing_required_authority"
            ),
            "severity": "error",
            "path": "/example",
        }

        self.assertEqual(
            planner.action_for_finding(
                finding
            ),
            "refuse",
        )

    def test_mood_mismatch_supersedes(
        self,
    ) -> None:
        finding = {
            "key": (
                "canonical_mood_mismatch"
            ),
            "severity": "error",
            "path": "/example",
        }

        self.assertEqual(
            planner.action_for_finding(
                finding
            ),
            "supersede",
        )

    def test_duplicate_requires_classification(
        self,
    ) -> None:
        finding = {
            "key": (
                "duplicate_content_candidate"
            ),
            "severity": "notice",
            "path": "/example",
        }

        self.assertEqual(
            planner.action_for_finding(
                finding
            ),
            "classify",
        )

    def test_candidate_identity_is_stable(
        self,
    ) -> None:
        first = planner.candidate_identity(
            phase="moods",
            source_finding_key="test",
            source_path="/example",
            action_class="supersede",
        )

        second = planner.candidate_identity(
            phase="moods",
            source_finding_key="test",
            source_path="/example",
            action_class="supersede",
        )

        self.assertEqual(
            first,
            second,
        )

    def test_all_phases_have_nine_validators(
        self,
    ) -> None:
        for phase in (
            planner.MIGRATION_PHASES
        ):
            validators = (
                planner
                .validation_for_phase(
                    phase
                )
            )

            self.assertEqual(
                len(validators),
                9,
            )

            self.assertEqual(
                len(set(validators)),
                9,
            )

    def test_all_phases_have_nine_preservations(
        self,
    ) -> None:
        for phase in (
            planner.MIGRATION_PHASES
        ):
            preservation = (
                planner
                .preservation_for_phase(
                    phase
                )
            )

            self.assertEqual(
                len(preservation),
                9,
            )

            self.assertEqual(
                len(set(preservation)),
                9,
            )

    def test_all_phases_have_seven_rollback_items(
        self,
    ) -> None:
        for phase in (
            planner.MIGRATION_PHASES
        ):
            rollback = (
                planner
                .rollback_for_phase(
                    phase
                )
            )

            self.assertEqual(
                len(rollback),
                7,
            )


if __name__ == "__main__":
    unittest.main()
