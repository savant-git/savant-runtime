import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY / "canon-system"


class CanonCtlIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "canon-system"
        shutil.copytree(SOURCE, self.root, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
        self.command = [sys.executable, str(self.root / "runtime/canonctl.py")]
        self.environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def tearDown(self):
        self.temporary.cleanup()

    def run_ctl(self, *arguments, check=True):
        return subprocess.run(
            [*self.command, *arguments],
            cwd=self.root,
            env=self.environment,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_validate_project_and_database_are_reproducible(self):
        self.assertIn("valid: 31 records", self.run_ctl("validate").stdout)
        self.run_ctl("project")
        first_manifest = (self.root / "projections/index/manifest.json").read_bytes()
        self.run_ctl("project")
        self.assertEqual(
            first_manifest,
            (self.root / "projections/index/manifest.json").read_bytes(),
        )

        self.run_ctl("build-db")
        database = self.root / "runtime/canon.sqlite3"
        with sqlite3.connect(database) as connection:
            self.assertEqual(connection.execute("pragma integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("select count(*) from records").fetchone()[0], 31)

    def test_invalid_supersession_does_not_mutate_authority(self):
        authority_before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.joinpath("authority").rglob("*.yaml")
        }
        candidate = Path(self.temporary.name) / "invalid.yaml"
        candidate.write_text("id: invalid\n", encoding="utf-8")
        result = self.run_ctl(
            "supersede", "exile:carbon", str(candidate), check=False
        )
        self.assertNotEqual(result.returncode, 0)
        authority_after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.joinpath("authority").rglob("*.yaml")
        }
        self.assertEqual(authority_before, authority_after)

    def test_invalid_authority_does_not_replace_database(self):
        database = self.root / "runtime/canon.sqlite3"
        original = database.read_bytes()
        broken = self.root / "authority/broken.yaml"
        broken.write_text("not: a-valid-record\n", encoding="utf-8")
        result = self.run_ctl("build-db", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original, database.read_bytes())

    def test_manifest_paths_are_repository_relative(self):
        self.run_ctl("project")
        manifest = json.loads(
            (self.root / "projections/index/manifest.json").read_text(encoding="utf-8")
        )
        for item in manifest:
            self.assertFalse(Path(item["authority_path"]).is_absolute())
            self.assertFalse(Path(item["projection_path"]).is_absolute())


if __name__ == "__main__":
    unittest.main()
