#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "source" / "savant_dry_run.py"
spec = importlib.util.spec_from_file_location("savant_dry_run", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class DryRunTests(unittest.TestCase):
    def test_safe_relative_rejects_escape(self):
        with self.assertRaises(mod.DryRunError):
            mod.safe_relative("../escape")

    def test_tree_digest_is_deterministic(self):
        a = mod.tree_digest([("b", "2"), ("a", "1")])
        b = mod.tree_digest([("a", "1"), ("b", "2")])
        self.assertEqual(a, b)

    def test_evaluate_fails_closed(self):
        gate = mod.GateResult("x", "fail", "critical", "broken")
        verdict, reasons = mod.evaluate([gate], {}, [{}])
        self.assertEqual(verdict, mod.UNSAFE)
        self.assertTrue(reasons)

    def test_evaluate_indeterminate_on_unknown(self):
        gate = mod.GateResult("x", "indeterminate", "high", "unknown")
        verdict, _ = mod.evaluate([gate], {}, [{}])
        self.assertEqual(verdict, mod.INDETERMINATE)

    def test_evaluate_safe_only_all_pass(self):
        gate = mod.GateResult("x", "pass", "high", "ok")
        verdict, _ = mod.evaluate([gate], {}, [{}])
        self.assertEqual(verdict, mod.SAFE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
