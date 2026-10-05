#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "summarize_modular_pipeline.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "summarize_modular_pipeline",
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


summary = load_module()


class ModularPipelineSummaryTests(
    unittest.TestCase
):

    def test_nine_pipeline_stages(
        self,
    ) -> None:
        self.assertEqual(
            len(
                summary.PIPELINE_STAGES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    summary.PIPELINE_STAGES
                )
            ),
            9,
        )

    def test_nine_stage_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                summary.STAGE_STATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    summary.STAGE_STATES
                )
            ),
            9,
        )

    def test_nine_summary_axes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                summary.REQUIRED_SUMMARY_AXES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    summary.REQUIRED_SUMMARY_AXES
                )
            ),
            9,
        )

    def test_missing_stage_is_missing(
        self,
    ) -> None:
        state = summary.derive_stage_state(
            latest_exists=False,
            latest_valid=False,
            manifest_valid=False,
            passed=None,
            ready_count=None,
            blocked_count=None,
            failure_count=None,
            replacement_stage=False,
        )

        self.assertEqual(
            state,
            "missing",
        )

    def test_failure_is_blocked(
        self,
    ) -> None:
        state = summary.derive_stage_state(
            latest_exists=True,
            latest_valid=True,
            manifest_valid=True,
            passed=False,
            ready_count=0,
            blocked_count=0,
            failure_count=1,
            replacement_stage=False,
        )

        self.assertEqual(
            state,
            "blocked",
        )

    def test_passed_stage_is_passed(
        self,
    ) -> None:
        state = summary.derive_stage_state(
            latest_exists=True,
            latest_valid=True,
            manifest_valid=True,
            passed=True,
            ready_count=0,
            blocked_count=0,
            failure_count=0,
            replacement_stage=False,
        )

        self.assertEqual(
            state,
            "passed",
        )

    def test_replacement_pass_is_complete(
        self,
    ) -> None:
        state = summary.derive_stage_state(
            latest_exists=True,
            latest_valid=True,
            manifest_valid=True,
            passed=True,
            ready_count=0,
            blocked_count=0,
            failure_count=0,
            replacement_stage=True,
        )

        self.assertEqual(
            state,
            "complete",
        )


if __name__ == "__main__":
    unittest.main()
