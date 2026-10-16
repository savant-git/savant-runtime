#!/usr/bin/env python3
"""
Focused tests for the Savant dimensional scaffold system.

Tests operate only in temporary directories and do not mutate the live tree.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/scaffold.py"
)
MODULE_NAME = "savant_dimension_scaffold"

SPEC = importlib.util.spec_from_file_location(
    MODULE_NAME,
    MODULE_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        f"Unable to construct import specification for {MODULE_PATH}"
    )

scaffold = importlib.util.module_from_spec(SPEC)

# dataclasses resolves annotations through sys.modules while the module is
# executing. Dynamic modules must therefore be registered before exec_module.
sys.modules[MODULE_NAME] = scaffold

try:
    SPEC.loader.exec_module(scaffold)
except Exception:
    sys.modules.pop(MODULE_NAME, None)
    raise


class DimensionScaffoldTests(unittest.TestCase):
    def test_registry_has_exactly_nine_unique_dimensions(self) -> None:
        value = scaffold.registry()
        dimensions = value["dimensions"]

        self.assertEqual(len(dimensions), 9)
        self.assertEqual(
            len(
                {
                    dimension["key"]
                    for dimension in dimensions
                }
            ),
            9,
        )
        self.assertEqual(
            len(
                {
                    dimension["name"]
                    for dimension in dimensions
                }
            ),
            9,
        )
        self.assertEqual(
            dimensions[0]["key"],
            "canon",
        )

    def test_sys_is_not_registered_as_dimension(self) -> None:
        value = scaffold.registry()
        keys = {
            dimension["key"]
            for dimension in value["dimensions"]
        }

        self.assertNotIn("sys", keys)

    def test_generated_dimension_count_is_eight(self) -> None:
        value = scaffold.registry()

        self.assertEqual(
            len(
                scaffold.generated_dimensions(value)
            ),
            8,
        )

    def test_record_is_non_authoritative(self) -> None:
        dimension = {
            "key": "signal",
            "name": "Signal",
            "ordinal": 7,
        }
        canon_object = scaffold.CanonObject(
            relative_path="foundation/example.md",
            absolute_path=(
                "/root/savant-runtime/vault/"
                "dimensions/canon/foundation/example.md"
            ),
            sha256="a" * 64,
            size=10,
            modified_ns=1,
        )

        record = scaffold.make_record(
            dimension,
            canon_object,
            "2026-08-04T00:00:00+00:00",
        )

        self.assertEqual(
            record["state"]["authority"],
            "none",
        )
        self.assertFalse(
            record["validation"][
                "authority_manufactured"
            ]
        )
        self.assertEqual(
            record["canon"]["sha256"],
            "a" * 64,
        )

    def test_basic_schema_validation_accepts_generated_record(
        self,
    ) -> None:
        dimension = {
            "key": "context",
            "name": "Context",
            "ordinal": 2,
        }
        canon_object = scaffold.CanonObject(
            relative_path="example.md",
            absolute_path=(
                "/root/savant-runtime/vault/"
                "dimensions/canon/example.md"
            ),
            sha256="b" * 64,
            size=1,
            modified_ns=1,
        )

        record = scaffold.make_record(
            dimension,
            canon_object,
            "2026-08-04T00:00:00+00:00",
        )

        self.assertEqual(
            scaffold.basic_schema_validate(record),
            [],
        )

    def test_identical_tree_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"

            first.mkdir()
            second.mkdir()

            (first / "a.txt").write_text(
                "same",
                encoding="utf-8",
            )
            (second / "a.txt").write_text(
                "same",
                encoding="utf-8",
            )

            self.assertTrue(
                scaffold.identical_trees(
                    first,
                    second,
                )
            )

            (second / "a.txt").write_text(
                "different",
                encoding="utf-8",
            )

            self.assertFalse(
                scaffold.identical_trees(
                    first,
                    second,
                )
            )

    def test_generated_record_detection_rejects_manual_data(
        self,
    ) -> None:
        self.assertFalse(
            scaffold.generated_record(
                {
                    "schema": "manual",
                    "lineage": {
                        "generator": "human",
                    },
                }
            )
        )

    def test_generated_record_detection_accepts_scaffold_record(
        self,
    ) -> None:
        dimension = {
            "key": "proof",
            "name": "Proof",
            "ordinal": 4,
        }
        canon_object = scaffold.CanonObject(
            relative_path="example.json",
            absolute_path=(
                "/root/savant-runtime/vault/"
                "dimensions/canon/example.json"
            ),
            sha256="c" * 64,
            size=2,
            modified_ns=2,
        )

        record = scaffold.make_record(
            dimension,
            canon_object,
            "2026-08-04T00:00:00+00:00",
        )

        self.assertTrue(
            scaffold.generated_record(record)
        )

    def test_record_path_preserves_complete_canon_filename(
        self,
    ) -> None:
        canon_object = scaffold.CanonObject(
            relative_path=(
                "foundation/example.schema.json"
            ),
            absolute_path=(
                "/root/savant-runtime/vault/"
                "dimensions/canon/foundation/"
                "example.schema.json"
            ),
            sha256="d" * 64,
            size=3,
            modified_ns=3,
        )

        path = scaffold.record_path(
            "context",
            canon_object,
        )

        self.assertEqual(
            path,
            Path(
                "/root/savant-runtime/vault/"
                "dimensions/context/foundation/"
                "example.schema.json.dimension.json"
            ),
        )

    def test_kinship_pattern_is_case_insensitive(self) -> None:
        self.assertIsNotNone(
            scaffold.KINSHIP_PATTERN.search(
                "Kinship"
            )
        )
        self.assertIsNotNone(
            scaffold.KINSHIP_PATTERN.search(
                "kinship"
            )
        )
        self.assertIsNone(
            scaffold.KINSHIP_PATTERN.search(
                "kindred"
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
