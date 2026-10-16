#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "apply_modular_replacement.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "apply_modular_replacement",
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


application = load_module()


class ModularReplacementApplicationTests(
    unittest.TestCase
):

    def test_three_application_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                application.APPLICATION_STATES
            ),
            3,
        )

        self.assertEqual(
            len(
                set(
                    application.APPLICATION_STATES
                )
            ),
            3,
        )

    def test_three_validation_kinds(
        self,
    ) -> None:
        self.assertEqual(
            len(
                application.VALIDATION_KINDS
            ),
            3,
        )

    def test_json_validation(
        self,
    ) -> None:
        application.validate_json_bytes(
            Path("/root/savant-runtime/test.json"),
            b'{"valid": true}\n',
        )

    def test_invalid_json_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            application.ApplicationError
        ):
            application.validate_json_bytes(
                Path(
                    "/root/savant-runtime/test.json"
                ),
                b"{invalid}",
            )

    def test_python_validation(
        self,
    ) -> None:
        application.validate_python_bytes(
            Path("/root/savant-runtime/test.py"),
            b"x = 1\n",
        )

    def test_invalid_python_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            application.ApplicationError
        ):
            application.validate_python_bytes(
                Path(
                    "/root/savant-runtime/test.py"
                ),
                b"def broken(:\n",
            )

    def test_atomic_write_replaces_complete_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "example.json"

            path.write_text(
                '{"old": true}\n',
                encoding="utf-8",
            )

            application.atomic_write_bytes(
                path,
                b'{"new": true}\n',
                0o644,
            )

            self.assertEqual(
                json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                ),
                {
                    "new": True,
                },
            )

    def test_paths_outside_runtime_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            application.ApplicationError
        ):
            application.confined_path(
                "/etc/passwd",
                "test path",
            )

    def test_validation_kind(
        self,
    ) -> None:
        self.assertEqual(
            application.validation_kind(
                Path("example.json")
            ),
            "json",
        )

        self.assertEqual(
            application.validation_kind(
                Path("example.py")
            ),
            "python",
        )

        self.assertEqual(
            application.validation_kind(
                Path("example.sh")
            ),
            "shell",
        )

        self.assertIsNone(
            application.validation_kind(
                Path("example.md")
            )
        )


if __name__ == "__main__":
    unittest.main()
