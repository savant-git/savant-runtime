#!/usr/bin/env python3
"""
Validate the latest dimensions report.

This is a standalone verification utility.
"""

from __future__ import annotations

import json
from pathlib import Path


REPORT = Path(
    "/root/savant-runtime/vault/dimensions/sys/reports/latest.json"
)


def main() -> int:
    report = json.loads(
        REPORT.read_text(encoding="utf-8")
    )

    print(f"operation: {report['operation']}")
    print(f"canon objects: {report['canon_object_count']}")
    print(f"failures: {report['failure_count']}")
    print(
        f"kinship occurrences: "
        f"{len(report.get('kinship_occurrences', []))}"
    )

    assert report["operation"] == "verify"
    assert report["canon_object_count"] == 100
    assert report["failure_count"] == 0

    print("PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
