#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "bind_modular_execution.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "bind_modular_execution",
        MODULE_PATH,
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

    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


binder = load_module()


class ModularExecutionBindingTests(
    unittest.TestCase
):

    def test_three_binding_states(self) -> None:
        self.assertEqual(
            len(binder.BINDING_STATES),
            3,
        )

        self.assertEqual(
            len(set(binder.BINDING_STATES)),
            3,
        )

    def test_nine_readiness_gates(self) -> None:
        self.assertEqual(
            len(binder.READINESS_GATES),
            9,
        )

        self.assertEqual(
            len(set(binder.READINESS_GATES)),
            9,
        )

    def test_identity_is_deterministic(
        self,
    ) -> None:
        first = binder.binding_identity(
            "execution:test",
            "/root/savant-runtime/example",
            "abc",
        )

        second = binder.binding_identity(
            "execution:test",
            "/root/savant-runtime/example",
            "abc",
        )

        self.assertEqual(first, second)

    def test_path_outside_root_is_rejected(
        self,
    ) -> None:
        self.assertIsNone(
            binder.normalize_target_path(
                "/etc/passwd"
            )
        )

    def test_relative_path_uses_runtime_root(
        self,
    ) -> None:
        result = binder.normalize_target_path(
            "example.json"
        )

        self.assertEqual(
            result,
            Path(
                "/root/savant-runtime/example.json"
            ),
        )

    def test_baseline_path_is_deterministic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_root = Path(raw)

            target = Path(
                "/root/savant-runtime/example.py"
            )

            first = binder.baseline_path(
                run_root,
                "execution-unit:test",
                target,
            )

            second = binder.baseline_path(
                run_root,
                "execution-unit:test",
                target,
            )

            self.assertEqual(first, second)

    def test_canonical_json_is_deterministic(
        self,
    ) -> None:
        first = binder.canonical_json_bytes(
            {
                "b": 2,
                "a": 1,
            }
        )

        second = binder.canonical_json_bytes(
            {
                "a": 1,
                "b": 2,
            }
        )

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
