#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


SCRIPT_PATH = Path(
    "/root/savant-runtime/vault/dimensions/sys/"
    "run_modular_diagnostics.sh"
)

SYS_ROOT = Path(
    "/root/savant-runtime/vault/dimensions/sys"
)

REPORT_ROOT = (
    SYS_ROOT
    / "reports"
)


class ModularDiagnosticsTests(
    unittest.TestCase
):

    def test_script_exists(
        self,
    ) -> None:
        self.assertTrue(
            SCRIPT_PATH.is_file()
        )

    def test_script_is_absolute(
        self,
    ) -> None:
        self.assertTrue(
            SCRIPT_PATH.is_absolute()
        )

    def test_shell_syntax(
        self,
    ) -> None:
        result = subprocess.run(
            [
                "/usr/bin/bash",
                "-n",
                str(SCRIPT_PATH),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )

    def test_script_has_shebang(
        self,
    ) -> None:
        first_line = (
            SCRIPT_PATH
            .read_text(
                encoding="utf-8"
            )
            .splitlines()[0]
        )

        self.assertEqual(
            first_line,
            "#!/usr/bin/env bash",
        )

    def test_script_forbids_unbound_variables(
        self,
    ) -> None:
        content = SCRIPT_PATH.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "set -u",
            content,
        )

    def test_script_enables_pipefail(
        self,
    ) -> None:
        content = SCRIPT_PATH.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "set -o pipefail",
            content,
        )

    def test_script_does_not_apply(
        self,
    ) -> None:
        content = SCRIPT_PATH.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "--apply",
            content,
        )

        self.assertNotIn(
            '"apply"',
            content,
        )

    def test_script_uses_absolute_root(
        self,
    ) -> None:
        content = SCRIPT_PATH.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'ROOT="/root/savant-runtime"',
            content,
        )

    def test_expected_report_root(
        self,
    ) -> None:
        expected = (
            Path(
                "/root/savant-runtime"
            )
            / "vault"
            / "dimensions"
            / "sys"
            / "reports"
        )

        self.assertEqual(
            REPORT_ROOT,
            expected,
        )


if __name__ == "__main__":
    unittest.main()
