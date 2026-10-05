#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ai_contract import (
    AIContract,
    AIContractError,
    contract_from_mapping,
)


class AIContractTests(
    unittest.TestCase
):

    def test_native_contract(
        self,
    ) -> None:
        contract = AIContract.native()

        self.assertFalse(
            contract.eligible
        )

        self.assertTrue(
            contract.native_fallback
        )

    def test_eligible_contract(
        self,
    ) -> None:
        contract = (
            AIContract.eligible_contract(
                (
                    "generate",
                    "analyze",
                ),
                required=(
                    "analyze",
                ),
            )
        )

        self.assertTrue(
            contract.eligible
        )

        self.assertEqual(
            contract.capabilities,
            (
                "analyze",
                "generate",
            ),
        )

    def test_ai_cannot_grant_authority(
        self,
    ) -> None:
        with self.assertRaises(
            AIContractError
        ):
            AIContract(
                eligible=True,
                authority_effect="grant",
            )

    def test_ai_cannot_grant_mutation(
        self,
    ) -> None:
        with self.assertRaises(
            AIContractError
        ):
            AIContract(
                eligible=True,
                mutation_effect="write",
            )

    def test_opus_ready_is_backward_compatible(
        self,
    ) -> None:
        contract = contract_from_mapping(
            None,
            opus_ready=True,
        )

        self.assertTrue(
            contract.eligible
        )

        self.assertEqual(
            contract.capabilities,
            (),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
