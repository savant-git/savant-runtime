#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "classify_modular_migration.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "classify_modular_migration",
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


classifier = load_module()


class ModularMigrationClassificationTests(
    unittest.TestCase
):

    def test_nine_dispositions(self) -> None:
        self.assertEqual(
            len(
                classifier.DISPOSITIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    classifier.DISPOSITIONS
                )
            ),
            9,
        )

    def test_nine_evidence_states(self) -> None:
        self.assertEqual(
            len(
                classifier.EVIDENCE_STATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    classifier.EVIDENCE_STATES
                )
            ),
            9,
        )

    def test_nine_review_axes(self) -> None:
        self.assertEqual(
            len(
                classifier.REVIEW_AXES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    classifier.REVIEW_AXES
                )
            ),
            9,
        )

    def test_blocked_candidate_is_blocked(
        self,
    ) -> None:
        candidate = {
            "action_class": "refuse",
            "status": "blocked",
            "severity": "error",
            "source_finding_key": (
                "missing_required_authority"
            ),
        }

        self.assertEqual(
            classifier.candidate_disposition(
                candidate
            ),
            "block",
        )

    def test_duplicate_candidate_investigated(
        self,
    ) -> None:
        candidate = {
            "action_class": "classify",
            "status": "planned",
            "severity": "notice",
            "source_finding_key": (
                "duplicate_content_candidate"
            ),
        }

        self.assertEqual(
            classifier.candidate_disposition(
                candidate
            ),
            "investigate",
        )

    def test_supersession_requires_decision(
        self,
    ) -> None:
        candidate = {
            "id": "candidate:test",
            "ordinal": 1,
            "phase": "moods",
            "source_path": "/example",
            "source_finding_key": (
                "canonical_mood_mismatch"
            ),
            "action_class": "supersede",
            "status": "planned",
            "severity": "error",
            "mutation_allowed": True,
            "authority_required": "decision",
            "rationale": "active mismatch",
            "preservation_requirements": [],
            "validation_requirements": [],
        }

        classification = (
            classifier.classify_candidate(
                candidate
            )
        )

        self.assertEqual(
            classification.disposition,
            "supersede",
        )

        self.assertFalse(
            classification.mutation_authorized
        )

        self.assertIn(
            "accepted mutation decision is not attached",
            classification.blockers,
        )

    def test_identity_is_deterministic(
        self,
    ) -> None:
        first = (
            classifier
            .classification_identity(
                "candidate:test",
                "investigate",
                "partial",
            )
        )

        second = (
            classifier
            .classification_identity(
                "candidate:test",
                "investigate",
                "partial",
            )
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
