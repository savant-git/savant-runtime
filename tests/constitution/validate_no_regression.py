#!/usr/bin/env python3
"""Run legacy suites while enforcing the accepted pre-constitution baseline."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


EXPECTED_KINSHIP_ERRORS = {
    "test_functional_kinship.FunctionalKinshipTests.test_all_renderers",
    "test_functional_kinship.FunctionalKinshipTests.test_direct_parent_profiles",
    "test_functional_kinship.FunctionalKinshipTests.test_full_sibling_and_twin",
    "test_functional_kinship.FunctionalKinshipTests.test_projection_is_deterministic",
}


def test_ids(items: list[tuple[unittest.case.TestCase, str]]) -> set[str]:
    return {test.id() for test, _traceback in items}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", choices=("kinship", "lineage"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    suite_dir = root / "tests" / args.suite
    suite = unittest.defaultTestLoader.discover(str(suite_dir), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    failures = test_ids(result.failures)
    errors = test_ids(result.errors)
    unexpected_successes = {test.id() for test in result.unexpectedSuccesses}

    if args.suite == "lineage":
        return 0 if result.wasSuccessful() else 1

    if failures or unexpected_successes or errors != EXPECTED_KINSHIP_ERRORS:
        print("kinship regression baseline changed", file=sys.stderr)
        print(f"expected errors: {sorted(EXPECTED_KINSHIP_ERRORS)}", file=sys.stderr)
        print(f"actual errors:   {sorted(errors)}", file=sys.stderr)
        print(f"failures:        {sorted(failures)}", file=sys.stderr)
        return 1

    print("kinship baseline preserved: 2 passing, 4 known recursion errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
