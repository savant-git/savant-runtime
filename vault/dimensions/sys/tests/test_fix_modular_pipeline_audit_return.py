#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "fix_modular_pipeline_audit_return.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "fix_modular_pipeline_audit_return",
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


migration = load_module()


class ModularPipelineAuditReturnTests(
    unittest.TestCase
):

    def test_old_contract_is_recognized(
        self,
    ) -> None:
        migration.validate_target(
            migration.OLD_BLOCK
        )

    def test_new_contract_is_already_applied(
        self,
    ) -> None:
        with self.assertRaises(
            migration.MigrationError
        ):
            migration.validate_target(
                migration.NEW_BLOCK
            )

    def test_ambiguous_contract_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            migration.MigrationError
        ):
            migration.validate_target(
                migration.OLD_BLOCK
                + migration.OLD_BLOCK
            )

    def test_replacement_changes_only_contract(
        self,
    ) -> None:
        before = (
            "prefix\n"
            + migration.OLD_BLOCK
            + "suffix\n"
        )

        after = before.replace(
            migration.OLD_BLOCK,
            migration.NEW_BLOCK,
            1,
        )

        migration.validate_replacement(
            before,
            after,
        )

    def test_unrelated_change_is_rejected(
        self,
    ) -> None:
        before = (
            "prefix\n"
            + migration.OLD_BLOCK
            + "suffix\n"
        )

        after = (
            before.replace(
                migration.OLD_BLOCK,
                migration.NEW_BLOCK,
                1,
            )
            + "unrelated\n"
        )

        with self.assertRaises(
            migration.MigrationError
        ):
            migration.validate_replacement(
                before,
                after,
            )

    def test_contract_accepts_three_codes(
        self,
    ) -> None:
        self.assertIn(
            "acceptable_return_codes=(0, 1, 2)",
            migration.NEW_BLOCK,
        )

    def test_contract_preserves_audit_stage(
        self,
    ) -> None:
        self.assertIn(
            'key="audit"',
            migration.NEW_BLOCK,
        )

        self.assertIn(
            'operation="audit"',
            migration.NEW_BLOCK,
        )

    def test_contract_preserves_output(
        self,
    ) -> None:
        self.assertIn(
            (
                'output=REPORT_ROOT / '
                '"modular-conformance" / '
                '"latest.json"'
            ),
            migration.NEW_BLOCK,
        )

    def test_digest_is_deterministic(
        self,
    ) -> None:
        self.assertEqual(
            migration.sha256_bytes(
                b"same"
            ),
            migration.sha256_bytes(
                b"same"
            ),
        )


if __name__ == "__main__":
    unittest.main()
