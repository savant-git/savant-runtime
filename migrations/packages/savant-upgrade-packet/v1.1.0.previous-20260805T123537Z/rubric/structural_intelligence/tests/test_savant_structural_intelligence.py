#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "source" / "savant_structural_intelligence.py"
spec = importlib.util.spec_from_file_location("ssi", MODULE_PATH)
assert spec and spec.loader
ssi = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ssi
spec.loader.exec_module(ssi)


class StructuralIntelligenceTests(unittest.TestCase):
    def test_stable_json(self) -> None:
        self.assertEqual(ssi.stable_json({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_owner_classification(self) -> None:
        result = ssi.classify_owner("tools/niche/masterplan/provider_router.py", "OpenAI provider model routing synthesis")
        self.assertEqual(result["owner"], "niche")
        self.assertTrue(any("ownership conflict" in reason for reason in result["reasons"]))

    def test_artifact_classification(self) -> None:
        entry = ssi.DumpEntry("x/tests/test_a.py", "source", "python", "id", "hash", "hash", "0o644", "")
        self.assertEqual(ssi.classify_artifact(entry), "test")

    def test_enhancement_count(self) -> None:
        self.assertGreaterEqual(len(ssi.enhancement_catalog()), 30)

    def test_dump_parser_minimal(self) -> None:
        manifest = {"counts": {"included_files": 1}, "files": [], "snapshot_hash": "abc"}
        text = (
            "=" * 76 + "\nsdump enterprise v3\n" + "=" * 76 + "\n\nmanifest\n" + "-" * 76 + "\n" +
            json.dumps(manifest) + "\n\n" + "=" * 76 + "\nunique authoritative contents\n" + "=" * 76 + "\n\n" +
            "=" * 76 + "\ncontent instance\n" + "=" * 76 + "\n" +
            "path: a.py\ncategory: source\nlanguage: python\nsource_size: 4\n" +
            "source_sha256: " + ssi.hashlib.sha256(b"x=1\n").hexdigest() + "\n" +
            "rendered_sha256: z\ncontent_id: sha256:z\nencoding: utf-8\nredactions: 0\n" +
            "-" * 76 + "\ncontent\n" + "-" * 76 + "\nx=1\n\n" +
            "=" * 76 + "\nend content instance\n" + "=" * 76 + "\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dump.txt"; p.write_text(text)
            parsed_manifest, entries = ssi.parse_dump(p)
            self.assertEqual(parsed_manifest["snapshot_hash"], "abc")
            self.assertEqual(entries[0].path, "a.py")


if __name__ == "__main__":
    unittest.main()
