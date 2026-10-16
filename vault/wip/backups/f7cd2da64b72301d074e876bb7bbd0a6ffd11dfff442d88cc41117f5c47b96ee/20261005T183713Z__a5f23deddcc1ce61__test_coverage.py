import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sdump_enterprise.audit import _coverage
from sdump_enterprise.model import (
    FileRecord,
    Projection,
    ScanStats,
    SkipRecord,
)


class CoverageIntelligenceTests(unittest.TestCase):

    def _record(
        self,
        path: str,
        *,
        included: bool,
        reason=None,
    ) -> FileRecord:
        return FileRecord(
            path=path,
            target_id="test",
            category="source",
            language="text",
            size=10,
            mode="0o644",
            mtime_ns=1,
            source_sha256="abc" if included else "",
            rendered_sha256="def" if included else None,
            content_id="sha256:def" if included else None,
            duplicate_of=None,
            encoding="utf-8" if included else None,
            redactions=0,
            authoritative=True,
            included=included,
            reason=reason,
        )

    def _evidence(self):
        return {
            "git": [{"root": "/test"}],
            "dependencies": {
                "files": [{"path": "pyproject.toml"}]
            },
            "runtime": {
                "processes": {"available": True},
                "listeners": {"available": True},
            },
            "tools": {
                "python": {"available": True},
            },
        }

    def test_projection_population_is_separate_from_skip_ledger(self):
        stats = ScanStats()
        stats.files_seen = 10
        stats.included_files = 8
        stats.failures = 0

        records = [
            self._record(f"file-{i}.txt", included=True)
            for i in range(8)
        ]

        records.extend([
            self._record(
                "binary.bin",
                included=False,
                reason="binary_content",
            ),
            self._record(
                "volatile.json",
                included=False,
                reason="volatile_runtime_unstable",
            ),
        ])

        skipped = [
            SkipRecord(
                "ignored.tmp",
                "excluded_extension",
                10,
            ),
            SkipRecord(
                "binary.bin",
                "binary_content",
                10,
            ),
            SkipRecord(
                "volatile.json",
                "volatile_runtime_unstable",
                10,
            ),
        ]

        projection = Projection(
            records=records,
            skipped=skipped,
            failures=[],
            symlinks=[],
            stats=stats,
            snapshot_hash="test",
        )

        coverage = _coverage(
            projection,
            self._evidence(),
        )

        self.assertEqual(
            coverage["schema"],
            "savant.sdump.coverage.v3",
        )

        self.assertEqual(
            coverage["projection"]["candidate_records"],
            10,
        )

        self.assertEqual(
            coverage["projection"]["included_records"],
            8,
        )

        self.assertEqual(
            coverage["projection"]["excluded_records"],
            2,
        )

        self.assertEqual(
            coverage["projection"]["capture_score"],
            0.8,
        )

        self.assertEqual(
            coverage["policy"]["skip_events"],
            3,
        )

        self.assertTrue(
            coverage["accounting"][
                "projection_invariant_valid"
            ]
        )

        self.assertEqual(
            coverage["accounting"]["warnings"],
            [],
        )

    def test_unknown_skip_reason_is_exposed(self):
        stats = ScanStats()
        stats.files_seen = 1
        stats.included_files = 1
        stats.failures = 0

        projection = Projection(
            records=[
                self._record(
                    "source.py",
                    included=True,
                )
            ],
            skipped=[
                SkipRecord(
                    "mystery",
                    "future_unknown_reason",
                    1,
                )
            ],
            failures=[],
            symlinks=[],
            stats=stats,
            snapshot_hash="test",
        )

        coverage = _coverage(
            projection,
            self._evidence(),
        )

        self.assertEqual(
            coverage["policy"]["unknown_skip_events"],
            1,
        )

        self.assertTrue(
            coverage["accounting"]["warnings"]
        )

    def test_failure_accounting_is_not_hidden(self):
        stats = ScanStats()
        stats.files_seen = 10
        stats.included_files = 8
        stats.failures = 1

        records = [
            self._record(
                f"source-{i}.py",
                included=True,
            )
            for i in range(8)
        ]

        projection = Projection(
            records=records,
            skipped=[],
            failures=[
                SkipRecord(
                    "broken.py",
                    "read_error:OSError",
                    10,
                )
            ],
            symlinks=[],
            stats=stats,
            snapshot_hash="test",
        )

        coverage = _coverage(
            projection,
            self._evidence(),
        )

        self.assertEqual(
            coverage["failures"]["count"],
            1,
        )

        self.assertEqual(
            coverage["discovery"]["hard_failures"],
            1,
        )

        self.assertEqual(
            coverage["discovery"]["integrity_score"],
            0.9,
        )

    def test_capabilities_are_independent_of_projection(self):
        stats = ScanStats()
        stats.files_seen = 1
        stats.included_files = 1
        stats.failures = 0

        projection = Projection(
            records=[
                self._record(
                    "source.py",
                    included=True,
                )
            ],
            skipped=[],
            failures=[],
            symlinks=[],
            stats=stats,
            snapshot_hash="test",
        )

        evidence = self._evidence()
        evidence["git"] = []

        coverage = _coverage(
            projection,
            evidence,
        )

        self.assertEqual(
            coverage["projection"]["capture_score"],
            1.0,
        )

        self.assertEqual(
            coverage["capabilities"][
                "dimensions"
            ]["git_provenance"],
            0.0,
        )

        self.assertLess(
            coverage["capabilities"]["score"],
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
