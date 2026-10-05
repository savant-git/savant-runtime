#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "accept_modular_decisions.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "accept_modular_decisions",
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


acceptance = load_module()


class ModularDecisionAcceptanceTests(
    unittest.TestCase
):

    def test_four_eligible_dispositions(
        self,
    ) -> None:
        self.assertEqual(
            set(
                acceptance.ELIGIBLE_DISPOSITIONS
            ),
            {
                "approve",
                "supersede",
                "instance",
                "project",
            },
        )

    def test_nine_review_gates(
        self,
    ) -> None:
        self.assertEqual(
            len(
                acceptance.REQUIRED_REVIEW_GATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    acceptance.REQUIRED_REVIEW_GATES
                )
            ),
            9,
        )

    def test_nine_decision_effects(
        self,
    ) -> None:
        self.assertEqual(
            len(
                acceptance.DECISION_EFFECTS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    acceptance.DECISION_EFFECTS
                )
            ),
            9,
        )

    def valid_proposal(
        self,
    ) -> dict[str, object]:
        return {
            "id": "decision-proposal:test",
            "classification_id": (
                "classification:test"
            ),
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
            "state": "proposed",
            "mutation_authorized": False,
            "rationale": "active mismatch",
            "review_gates": list(
                acceptance.REQUIRED_REVIEW_GATES
            ),
            "preservation_requirements": [],
            "validation_requirements": [],
            "blockers": [],
            "acceptance_conditions": [
                f"acceptance-{index}"
                for index in range(1, 10)
            ],
            "rejection_conditions": [
                f"rejection-{index}"
                for index in range(1, 10)
            ],
            "rollback_requirements": [
                f"rollback-{index}"
                for index in range(1, 10)
            ],
        }

    def test_valid_proposal_is_accepted(
        self,
    ) -> None:
        decision = (
            acceptance.accept_proposal(
                self.valid_proposal(),
                packet_id=(
                    "decision-packet:test"
                ),
                accepted_at=(
                    "20260804T000000Z"
                ),
            )
        )

        self.assertEqual(
            decision.state,
            "accepted",
        )

        self.assertTrue(
            decision.immutable
        )

        self.assertTrue(
            decision.mutation_authorized
        )

    def test_blocked_proposal_rejected(
        self,
    ) -> None:
        proposal = self.valid_proposal()
        proposal["blockers"] = [
            "unresolved"
        ]

        with self.assertRaises(
            acceptance.AcceptanceError
        ):
            acceptance.validate_proposal(
                proposal
            )

    def test_nonproposal_state_rejected(
        self,
    ) -> None:
        proposal = self.valid_proposal()
        proposal["state"] = "accepted"

        with self.assertRaises(
            acceptance.AcceptanceError
        ):
            acceptance.validate_proposal(
                proposal
            )

    def test_premature_mutation_rejected(
        self,
    ) -> None:
        proposal = self.valid_proposal()
        proposal[
            "mutation_authorized"
        ] = True

        with self.assertRaises(
            acceptance.AcceptanceError
        ):
            acceptance.validate_proposal(
                proposal
            )

    def test_decision_identity_is_stable(
        self,
    ) -> None:
        first = (
            acceptance.decision_identity(
                "proposal:test",
                "packet:test",
            )
        )

        second = (
            acceptance.decision_identity(
                "proposal:test",
                "packet:test",
            )
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
