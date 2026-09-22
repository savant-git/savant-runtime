#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "inspect_modular_pipeline.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "inspect_modular_pipeline",
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


class ModularPipelineInspectionTests(
    unittest.TestCase
):

    def test_nine_expected_stage_keys(
        self,
    ) -> None:
        self.assertEqual(
            len(
                inspector.EXPECTED_STAGE_KEYS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    inspector.EXPECTED_STAGE_KEYS
                )
            ),
            9,
        )

    def test_nine_inspection_axes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                inspector.INSPECTION_AXES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    inspector.INSPECTION_AXES
                )
            ),
            9,
        )

    def make_stage(
        self,
        *,
        ordinal: int,
        key: str,
        script_exists: bool = True,
        output_exists_after: bool = True,
        output_json_valid: bool = True,
        return_code: int = 0,
        passed: bool = True,
        blocker: str | None = None,
    ) -> object:
        return inspector.InspectedStage(
            ordinal=ordinal,
            key=key,
            script=(
                "/root/savant-runtime/"
                f"{key}.py"
            ),
            operation=key,
            output=(
                "/root/savant-runtime/"
                f"{key}.json"
            ),
            script_exists=(
                script_exists
            ),
            output_exists_before=False,
            output_exists_after=(
                output_exists_after
            ),
            output_json_valid=(
                output_json_valid
            ),
            return_code=return_code,
            passed=passed,
            blocker=blocker,
            stdout="",
            stderr="",
        )

    def test_missing_script_is_first_blocker(
        self,
    ) -> None:
        stage = self.make_stage(
            ordinal=1,
            key="audit",
            script_exists=False,
            passed=False,
        )

        blocker = (
            inspector.derive_first_blocker(
                (
                    stage,
                )
            )
        )

        self.assertIn(
            "stage script is missing",
            blocker,
        )

    def test_missing_output_is_first_blocker(
        self,
    ) -> None:
        stage = self.make_stage(
            ordinal=1,
            key="audit",
            output_exists_after=False,
            passed=False,
        )

        blocker = (
            inspector.derive_first_blocker(
                (
                    stage,
                )
            )
        )

        self.assertIn(
            "required output is missing",
            blocker,
        )

    def test_invalid_json_is_first_blocker(
        self,
    ) -> None:
        stage = self.make_stage(
            ordinal=1,
            key="audit",
            output_json_valid=False,
            passed=False,
        )

        blocker = (
            inspector.derive_first_blocker(
                (
                    stage,
                )
            )
        )

        self.assertIn(
            "not valid JSON",
            blocker,
        )

    def test_stage_blocker_is_preserved(
        self,
    ) -> None:
        stage = self.make_stage(
            ordinal=1,
            key="audit",
            passed=False,
            blocker="specific failure",
        )

        blocker = (
            inspector.derive_first_blocker(
                (
                    stage,
                )
            )
        )

        self.assertEqual(
            blocker,
            "audit: specific failure",
        )

    def test_incomplete_pipeline_names_next_stage(
        self,
    ) -> None:
        stage = self.make_stage(
            ordinal=1,
            key="audit",
        )

        blocker = (
            inspector.derive_first_blocker(
                (
                    stage,
                )
            )
        )

        self.assertEqual(
            blocker,
            "plan: stage was not executed",
        )

    def test_digest_is_deterministic(
        self,
    ) -> None:
        self.assertEqual(
            inspector.sha256_bytes(
                b"same"
            ),
            inspector.sha256_bytes(
                b"same"
            ),
        )


if __name__ == "__main__":
    unittest.main()
