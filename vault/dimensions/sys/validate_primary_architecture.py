#!/usr/bin/env python3
"""
Validate Savant's primary instance-first, mood-governed,
minimal-footprint architectural law.

This validator is read-only. It does not mutate authority.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


ROOT: Final[Path] = Path("/root/savant-runtime")

PROJECT_INSTRUCTIONS: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "canon"
    / "PROJECT_INSTRUCTIONS.md"
)

PRIMARY_LAW: Final[Path] = (
    ROOT
    / "ontology"
    / "obelisks"
    / "segue"
    / "authority_graph"
    / "canon"
    / "PRIMARY_ARCHITECTURAL_LAW.md"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
    / "reports"
    / "primary-architecture"
)

CANONICAL_MOODS: Final[tuple[str, ...]] = (
    "Anima",
    "Weld",
    "Kiln",
    "Graft",
    "Aria",
    "Mantle",
    "Fulcrum",
    "Echelon",
    "Ascent",
)

FOOTPRINTS: Final[tuple[str, ...]] = (
    "authoritative footprint",
    "storage footprint",
    "code footprint",
    "dependency footprint",
    "runtime footprint",
    "migration footprint",
    "validation footprint",
    "cognitive footprint",
    "recovery footprint",
)

CONSTRUCTION_MECHANISMS: Final[tuple[str, ...]] = (
    "additive slot capability",
    "two-mood fusion",
    "Weld composition",
)

REQUIRED_PROJECT_STATEMENTS: Final[tuple[str, ...]] = (
    "This is Savant's highest architectural rule.",
    "Everything that can be expressed as an instance must be expressed as an instance.",
    "Store authority once.",
    "Instance it wherever needed.",
    "Generate everything else deterministically.",
    "Slots never fuse capabilities.",
    "Exactly two distinct moods may fuse into one canonical ability.",
    "A mood may not fuse with itself.",
    "A fusion may not contain three or more moods.",
    "Savant recognizes exactly three combination mechanisms.",
    "Every deliberate peer collection of named architectural elements must contain:",
)

REQUIRED_LAW_STATEMENTS: Final[tuple[str, ...]] = (
    "Savant must minimize authoritative substance while maximizing emergent capability.",
    "Atomic elements are the only directly substantiated material.",
    "Exactly three construction mechanisms exist:",
    "Slots add independent capabilities.",
    "Two distinct moods may fuse into one distinct ability.",
    "Welds construct higher structures while preserving constituent identity.",
)


class ValidationError(RuntimeError):
    """Raised when a constitutional architectural invariant fails."""


@dataclass(frozen=True, slots=True)
class Check:
    key: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "passed": self.passed,
            "detail": self.detail,
        }


def require_file(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(
            f"required authoritative file is missing: {path}"
        )

    return path.read_text(encoding="utf-8")


def check_statements(
    *,
    key_prefix: str,
    content: str,
    statements: tuple[str, ...],
) -> list[Check]:
    checks: list[Check] = []

    for index, statement in enumerate(statements, start=1):
        checks.append(
            Check(
                key=f"{key_prefix}.{index:02d}",
                passed=statement in content,
                detail=statement,
            )
        )

    return checks


def check_moods(content: str) -> list[Check]:
    checks: list[Check] = []

    for index, mood in enumerate(CANONICAL_MOODS, start=1):
        heading_pattern = re.compile(
            rf"^###\s+{re.escape(mood)}\s*$",
            flags=re.MULTILINE,
        )

        checks.append(
            Check(
                key=f"mood.{index:02d}.{mood.casefold()}",
                passed=bool(heading_pattern.search(content)),
                detail=f"canonical mood heading exists: {mood}",
            )
        )

    return checks


def check_footprints(content: str) -> list[Check]:
    checks: list[Check] = []

    for index, footprint in enumerate(FOOTPRINTS, start=1):
        checks.append(
            Check(
                key=f"footprint.{index:02d}",
                passed=footprint in content,
                detail=footprint,
            )
        )

    return checks


def check_mechanisms(content: str) -> list[Check]:
    checks: list[Check] = []

    for index, mechanism in enumerate(
        CONSTRUCTION_MECHANISMS,
        start=1,
    ):
        checks.append(
            Check(
                key=f"mechanism.{index:02d}",
                passed=mechanism.casefold() in content.casefold(),
                detail=mechanism,
            )
        )

    return checks


def check_cardinality_policy(content: str) -> list[Check]:
    return [
        Check(
            key="cardinality.three",
            passed=(
                "exactly three items when fewer than nine are justified"
                in content
            ),
            detail="sub-nine deliberate peer taxonomies reduce to three",
        ),
        Check(
            key="cardinality.nine",
            passed=(
                "otherwise a multiple of nine"
                in content
            ),
            detail="larger deliberate peer taxonomies use multiples of nine",
        ),
        Check(
            key="cardinality.no-filler",
            passed=(
                "Never add meaningless filler merely to satisfy cardinality."
                in content
            ),
            detail="cardinality cannot justify semantic filler",
        ),
    ]


def check_primary_law_structure(content: str) -> list[Check]:
    expected_headings = (
        "## Law",
        "## Canonical Moods",
        "## Construction Priority",
        "## Minimal Footprint",
        "## Construction Mechanisms",
        "## Acceptance",
        "## Consequence",
    )

    return [
        Check(
            key=f"law.heading.{index:02d}",
            passed=heading in content,
            detail=heading,
        )
        for index, heading in enumerate(
            expected_headings,
            start=1,
        )
    ]


def write_report(payload: dict[str, object]) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)

    report_path = REPORT_ROOT / "latest.json"

    temporary_path = REPORT_ROOT / ".latest.json.tmp"

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.chmod(0o644)
    temporary_path.replace(report_path)

    return report_path


def main() -> int:
    try:
        project_content = require_file(
            PROJECT_INSTRUCTIONS
        )
        law_content = require_file(
            PRIMARY_LAW
        )

        checks: list[Check] = []

        checks.extend(
            check_statements(
                key_prefix="project.statement",
                content=project_content,
                statements=REQUIRED_PROJECT_STATEMENTS,
            )
        )

        checks.extend(
            check_statements(
                key_prefix="law.statement",
                content=law_content,
                statements=REQUIRED_LAW_STATEMENTS,
            )
        )

        checks.extend(
            check_moods(project_content)
        )

        checks.extend(
            check_footprints(project_content)
        )

        checks.extend(
            check_mechanisms(law_content)
        )

        checks.extend(
            check_cardinality_policy(
                project_content
            )
        )

        checks.extend(
            check_primary_law_structure(
                law_content
            )
        )

        failures = [
            check
            for check in checks
            if not check.passed
        ]

        payload: dict[str, object] = {
            "operation": "validate_primary_architecture",
            "passed": not failures,
            "root": str(ROOT),
            "project_instructions": str(
                PROJECT_INSTRUCTIONS
            ),
            "primary_law": str(PRIMARY_LAW),
            "canonical_mood_count": len(
                CANONICAL_MOODS
            ),
            "canonical_moods": list(
                CANONICAL_MOODS
            ),
            "footprint_count": len(
                FOOTPRINTS
            ),
            "combination_mechanism_count": len(
                CONSTRUCTION_MECHANISMS
            ),
            "check_count": len(checks),
            "failure_count": len(failures),
            "checks": [
                check.as_dict()
                for check in checks
            ],
        }

        report_path = write_report(payload)

        payload["report"] = str(report_path)

        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )

        return 1 if failures else 0

    except ValidationError as error:
        payload = {
            "operation": "validate_primary_architecture",
            "passed": False,
            "failure_count": 1,
            "error": str(error),
        }

        report_path = write_report(payload)
        payload["report"] = str(report_path)

        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
