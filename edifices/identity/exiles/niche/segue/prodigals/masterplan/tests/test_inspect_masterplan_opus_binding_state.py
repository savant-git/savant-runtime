#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "inspect_masterplan_opus_binding_state.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "inspect_masterplan_opus_binding_state",
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


inspector = load_module()


class MasterplanOpusBindingStateTests(
    unittest.TestCase
):

    def test_nine_stage_keys(
        self,
    ) -> None:
        self.assertEqual(
            len(
                inspector.STAGE_KEYS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    inspector.STAGE_KEYS
                )
            ),
            9,
        )

    def test_every_stage_has_pointer(
        self,
    ) -> None:
        self.assertEqual(
            set(
                inspector.STAGE_KEYS
            ),
            set(
                inspector.STAGE_POINTERS
            ),
        )

    def test_every_stage_has_reference_contract(
        self,
    ) -> None:
        self.assertEqual(
            set(
                inspector.STAGE_KEYS
            ),
            set(
                inspector.REQUIRED_REFERENCES
            ),
        )

    def test_every_stage_has_state_contract(
        self,
    ) -> None:
        self.assertEqual(
            set(
                inspector.STAGE_KEYS
            ),
            set(
                inspector.TERMINAL_READY_STATES
            ),
        )

        self.assertEqual(
            set(
                inspector.STAGE_KEYS
            ),
            set(
                inspector.STATE_FIELDS
            ),
        )

    def test_semantic_digest_is_stable(
        self,
    ) -> None:
        first = inspector.semantic_digest(
            {
                "b": 2,
                "a": 1,
            }
        )

        second = inspector.semantic_digest(
            {
                "a": 1,
                "b": 2,
            }
        )

        self.assertEqual(
            first,
            second,
        )

    def test_confined_path_rejects_escape(
        self,
    ) -> None:
        with self.assertRaises(
            inspector.InspectionError
        ):
            inspector.confined_path(
                "/etc/passwd",
                "test",
            )

    def test_validate_empty_reference_contract(
        self,
    ) -> None:
        valid, count, blocker = (
            inspector.validate_references(
                "agent_context",
                {},
            )
        )

        self.assertTrue(
            valid
        )

        self.assertEqual(
            count,
            0,
        )

        self.assertIsNone(
            blocker
        )

    def test_missing_latest_is_blocked(
        self,
    ) -> None:
        original = inspector.STAGE_POINTERS[
            "agent_context"
        ]

        with tempfile.TemporaryDirectory() as raw:
            missing = (
                Path(
                    raw
                )
                / "missing.json"
            )

            inspector.STAGE_POINTERS[
                "agent_context"
            ] = missing

            try:
                stage = inspector.inspect_stage(
                    1,
                    "agent_context",
                )
            finally:
                inspector.STAGE_POINTERS[
                    "agent_context"
                ] = original

        self.assertFalse(
            stage.passed
        )

        self.assertIn(
            "latest pointer missing",
            stage.blocker,
        )

    def test_ready_state_contract(
        self,
    ) -> None:
        self.assertIn(
            "planned",
            inspector.TERMINAL_READY_STATES[
                "opus_plan"
            ],
        )

        self.assertIn(
            "ready",
            inspector.TERMINAL_READY_STATES[
                "opus_workspace"
            ],
        )


if __name__ == "__main__":
    unittest.main()
