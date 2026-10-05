from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from sdump_enterprise.profiles import load_profile
from sdump_enterprise.render import write_bundle
from sdump_enterprise.scan import build_projection, discover, normalized_targets
from sdump_enterprise.util import sha256_file


class SdumpCoreTests(unittest.TestCase):
    def test_compact_exclusion_deduplication_and_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "duplicate.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "config.txt").write_text("OPENAI_API_KEY=secret-value\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=should-not-appear\n", encoding="utf-8")
            (root / "exports").mkdir()
            (root / "exports" / "copy.py").write_text("print('generated')\n", encoding="utf-8")
            output_root = root / "source"
            output_root.mkdir()

            profile = replace(load_profile("compact"), max_total_content_bytes=1024 * 1024)
            candidates, skipped, failures, symlinks, stats = discover(
                targets=normalized_targets([str(root)]),
                profile=profile,
                absolute_excluded_roots=(output_root,),
                include_hidden=False,
                include_secrets=False,
                extra_patterns=(),
                respect_gitignore=False,
            )
            store = Path(directory) / "store"
            projection = build_projection(
                candidates,
                skipped,
                failures,
                symlinks,
                stats,
                profile,
                store,
                workers=2,
                include_secrets=False,
            )
            self.assertEqual(projection.stats.included_files, 3)
            self.assertEqual(projection.stats.unique_contents, 2)
            self.assertEqual(projection.stats.duplicate_files, 1)
            self.assertGreaterEqual(projection.stats.redactions, 1)
            skipped_paths = {item.path for item in projection.skipped}
            self.assertIn(".env", skipped_paths)
            self.assertTrue(any(path == "exports" or path.startswith("exports/") for path in skipped_paths))

            manifest = {
                "schema": "test",
                "snapshot_hash": projection.snapshot_hash,
                "files": [record.to_dict() for record in projection.records],
            }
            output = Path(directory) / "dump.txt"
            write_bundle(output, manifest, projection)
            text = output.read_text(encoding="utf-8")
            self.assertIn("[REDACTED]", text)
            self.assertNotIn("secret-value", text)
            self.assertEqual(text.count("print('ok')"), 1)
            self.assertEqual(len(sha256_file(output)), 64)

    def test_profile_is_valid(self) -> None:
        profile = load_profile("compact")
        self.assertEqual(profile.id, "compact")
        self.assertGreater(profile.max_total_content_bytes, profile.max_file_bytes)


if __name__ == "__main__":
    unittest.main()
