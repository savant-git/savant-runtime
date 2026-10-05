#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "review_modular_binding.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "review_modular_binding",
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


reviewer = load_module()


class ModularBindingReviewTests(
    unittest.TestCase
):

    def test_nine_supported_actions(
        self,
    ) -> None:
        self.assertEqual(
            len(
                reviewer.SUPPORTED_ACTIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    reviewer.SUPPORTED_ACTIONS
                )
            ),
            9,
        )

    def test_three_review_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                reviewer.REVIEW_STATES
            ),
            3,
        )

        self.assertEqual(
            len(
                set(
                    reviewer.REVIEW_STATES
                )
            ),
            3,
        )

    def test_nine_semantic_axes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                reviewer.SEMANTIC_AXES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    reviewer.SEMANTIC_AXES
                )
            ),
            9,
        )

    def test_nine_ready_gates(
        self,
    ) -> None:
        self.assertEqual(
            len(
                reviewer.REQUIRED_READY_GATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    reviewer.REQUIRED_READY_GATES
                )
            ),
            9,
        )

    def test_known_rule_resolves(
        self,
    ) -> None:
        rule = reviewer.semantic_rule_for(
            "canonical_mood_mismatch"
        )

        self.assertIsInstance(
            rule,
            str,
        )

        self.assertTrue(
            rule
        )

    def test_unknown_rule_does_not_resolve(
        self,
    ) -> None:
        self.assertIsNone(
            reviewer.semantic_rule_for(
                "unknown-finding"
            )
        )

    def test_review_identity_is_stable(
        self,
    ) -> None:
        first = reviewer.review_identity(
            "bound:test",
            "/root/savant-runtime/example",
            "canonical_mood_mismatch",
        )

        second = reviewer.review_identity(
            "bound:test",
            "/root/savant-runtime/example",
            "canonical_mood_mismatch",
        )

        self.assertEqual(
            first,
            second,
        )

    def test_string_paths_are_sorted_unique(
        self,
    ) -> None:
        result = reviewer.string_paths(
            [
                {"path": "/b"},
                {"path": "/a"},
                {"path": "/a"},
            ]
        )

        self.assertEqual(
            result,
            (
                "/a",
                "/b",
            ),
        )


if __name__ == "__main__":
    unittest.main()
