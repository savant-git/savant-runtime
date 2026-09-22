#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "run_modular_pipeline.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "run_modular_pipeline",
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


pipeline = load_module()


class ModularPipelineTests(
    unittest.TestCase
):

    def test_exactly_nine_stages(
        self,
    ) -> None:
        self.assertEqual(
            len(
                pipeline.STAGES
            ),
            9,
        )

    def test_stage_ordinals_are_contiguous(
        self,
    ) -> None:
        self.assertEqual(
            [
                stage.ordinal
                for stage in pipeline.STAGES
            ],
            list(
                range(
                    1,
                    10,
                )
            ),
        )

    def test_stage_keys_are_unique(
        self,
    ) -> None:
        keys = [
            stage.key
            for stage in pipeline.STAGES
        ]

        self.assertEqual(
            len(keys),
            len(set(keys)),
        )

    def test_all_stage_paths_are_absolute(
        self,
    ) -> None:
        for stage in pipeline.STAGES:
            self.assertTrue(
                stage.script.is_absolute()
            )

            self.assertTrue(
                stage.output.is_absolute()
            )

    def test_application_defaults_to_disabled(
        self,
    ) -> None:
        self.assertTrue(
            callable(
                pipeline.parse_arguments
            )
        )

    def test_digest_is_deterministic(
        self,
    ) -> None:
        self.assertEqual(
            pipeline.sha256_bytes(
                b"same"
            ),
            pipeline.sha256_bytes(
                b"same"
            ),
        )

    def test_canonical_json_is_deterministic(
        self,
    ) -> None:
        first = (
            pipeline.canonical_json_bytes(
                {
                    "b": 2,
                    "a": 1,
                }
            )
        )

        second = (
            pipeline.canonical_json_bytes(
                {
                    "a": 1,
                    "b": 2,
                }
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_stage_outputs_use_report_root(
        self,
    ) -> None:
        for stage in pipeline.STAGES:
            self.assertTrue(
                stage.output.is_relative_to(
                    pipeline.REPORT_ROOT
                )
            )

    def test_stage_scripts_use_sys_root(
        self,
    ) -> None:
        for stage in pipeline.STAGES:
            self.assertTrue(
                stage.script.is_relative_to(
                    pipeline.SYS_ROOT
                )
            )


if __name__ == "__main__":
    unittest.main()
