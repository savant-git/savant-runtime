#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import itertools
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "compile_modular_replacement.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "compile_modular_replacement",
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


class ModularReplacementCompilationTests(
    unittest.TestCase
):

    def test_nine_canonical_moods(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.CANONICAL_MOODS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.CANONICAL_MOODS
                )
            ),
            9,
        )

    def test_thirty_six_mood_pairs(
        self,
    ) -> None:
        pairs = tuple(
            itertools.combinations(
                compiler.CANONICAL_MOODS,
                2,
            )
        )

        self.assertEqual(
            len(pairs),
            36,
        )

    def test_three_transformations(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.TRANSFORMATION_KEYS
            ),
            3,
        )

    def test_three_replacement_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.REPLACEMENT_STATES
            ),
            3,
        )

    def test_nine_validation_axes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.VALIDATION_AXES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.VALIDATION_AXES
                )
            ),
            9,
        )

    def test_historical_moods_map(
        self,
    ) -> None:
        self.assertEqual(
            compiler.map_mood_key(
                "Instantiation"
            ),
            "anima",
        )

        self.assertEqual(
            compiler.map_mood_key(
                "Composition"
            ),
            "weld",
        )

        self.assertEqual(
            compiler.map_mood_key(
                "Segue"
            ),
            "fulcrum",
        )

    def test_mood_registry_has_nine_moods(
        self,
    ) -> None:
        migrated = (
            compiler.migrate_mood_registry(
                {
                    "moods": [],
                    "fusions": [],
                }
            )
        )

        self.assertEqual(
            len(
                migrated["moods"]
            ),
            9,
        )

        self.assertEqual(
            len(
                migrated["fusions"]
            ),
            36,
        )

    def test_slot_registry_is_additive(
        self,
    ) -> None:
        migrated = (
            compiler.migrate_slot_registry(
                {}
            )
        )

        self.assertIs(
            migrated["semantics"][
                "additive"
            ],
            True,
        )

        self.assertIs(
            migrated["semantics"][
                "fusion"
            ],
            False,
        )

        self.assertEqual(
            migrated["capacity"][
                "maximum_non_atomic"
            ],
            4,
        )

    def test_identity_is_stable(
        self,
    ) -> None:
        first = (
            compiler.replacement_identity(
                "review:test",
                "/root/savant-runtime/example",
                "canonical_moods",
            )
        )

        second = (
            compiler.replacement_identity(
                "review:test",
                "/root/savant-runtime/example",
                "canonical_moods",
            )
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
