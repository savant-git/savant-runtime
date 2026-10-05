from __future__ import annotations

import argparse
import json

from .registry import ConstitutionalRegistry, PROJECTION_TARGETS
from .readiness import migration_readiness_report
from .validation import ConstitutionalValidator


def main() -> int:
    parser = argparse.ArgumentParser(description="Project Savant constitutional authority")
    parser.add_argument("target", choices=(*PROJECTION_TARGETS, "faculty-system-matrix", "readiness", "validate"))
    args = parser.parse_args()
    registry = ConstitutionalRegistry.load()
    if args.target == "faculty-system-matrix":
        result = registry.faculty_system_matrix()
    elif args.target == "readiness":
        result = migration_readiness_report(registry)
    elif args.target == "validate":
        result = ConstitutionalValidator(registry).validate()
    else:
        result = registry.project(args.target)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
