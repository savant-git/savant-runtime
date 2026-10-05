#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "prepare_modular_decisions.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "prepare_modular_decisions",
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


decisions = load_module()


class ModularDecisionPreparationTests(
    unittest.TestCase
):

    def test_three_decision_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                decisions.DECISION_STATES
            ),
            3,
        )

        self.assertEqual(
            len(
                set(
                    decisions.DECISION_STATES
                )
            ),
            3,
        )

    def test_nine_review_gates(
        self,
    ) -> None:
        self.assertEqual(
            len(
                decisions.REVIEW_GATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    decisions.REVIEW_GATES
                )
            ),
            9,
        )

    def test_four_proposable_dispositions(
        self,
    ) -> None:
        self.assertEqual(
            set(
                decisions.PROPOSABLE_DISPOSITIONS
            ),
            {
                "approve",
                "supersede",
                "instance",
                "project",
            },
        )

    def test_investigate_is_not_proposable(
        self,
    ) -> None:
        classification = {
            "disposition": "investigate"
        }

        self.assertFalse(
            decisions
            .classification_is_proposable(
                classification
            )
        )

    def test_supersede_is_proposable(
        self,
    ) -> None:
        classification = {
            "disposition": "supersede"
        }

        self.assertTrue(
            decisions
            .classification_is_proposable(
                classification
            )
        )

    def test_proposal_never_authorizes_mutation(
        self,
    ) -> None:
        classification = {
            "id": "classification:test",
            "candidate_id": "candidate:test",
            "candidate_ordinal": 1,
            "phase": "moods",
            "source_path": "/example",
            "source_finding_key": (
                "canonical_mood_mismatch"
            ),
            "disposition": "supersede",
            "proposed_action": "supersede",
            "authority_required": "decision",
            "rationale": "active mismatch",
            "preservation_requirements": [],
            "validation_requirements": [],
            "blockers": [
                "accepted mutation decision is not attached"
            ],
        }

        proposal = (
            decisions.prepare_proposal(
                classification
            )
        )

        self.assertEqual(
            proposal.state,
            "proposed",
        )

        self.assertFalse(
            proposal.mutation_authorized
        )

        self.assertNotIn(
            "accepted mutation decision is not attached",
            proposal.blockers,
        )

    def test_nine_acceptance_conditions(
        self,
    ) -> None:
        conditions = (
            decisions
            .acceptance_conditions(
                {}
            )
        )

        self.assertEqual(
            len(conditions),
            9,
        )

        self.assertEqual(
            len(set(conditions)),
            9,
        )

    def test_nine_rejection_conditions(
        self,
    ) -> None:
        conditions = (
            decisions
            .rejection_conditions(
                {}
            )
        )

        self.assertEqual(
            len(conditions),
            9,
        )

        self.assertEqual(
            len(set(conditions)),
            9,
        )

    def test_nine_rollback_requirements(
        self,
    ) -> None:
        requirements = (
            decisions
            .rollback_requirements(
                {}
            )
        )

        self.assertEqual(
            len(requirements),
            9,
        )

        self.assertEqual(
            len(set(requirements)),
            9,
        )


if __name__ == "__main__":
    unittest.main()
