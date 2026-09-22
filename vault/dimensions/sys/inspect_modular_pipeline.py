#!/usr/bin/env python3
"""
Inspect the latest Savant modular-pipeline run and print the exact first blocker.

This tool is read-only with respect to implementation and authority.

It validates:

- latest pipeline pointer
- pipeline report
- pipeline manifest
- stage ordering
- stage output existence
- stage output JSON validity
- stage stdout and stderr
- first-blocker consistency

It never reruns stages, creates authority, or mutates implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final


ROOT: Final[Path] = Path("/root/savant-runtime")

SYS_ROOT: Final[Path] = (
    ROOT
    / "vault"
    / "dimensions"
    / "sys"
)

PIPELINE_ROOT: Final[Path] = (
    SYS_ROOT
    / "reports"
    / "modular-pipeline-run"
)

LATEST_PIPELINE: Final[Path] = (
    PIPELINE_ROOT
    / "latest.json"
)

EXPECTED_STAGE_KEYS: Final[tuple[str, ...]] = (
    "audit",
    "plan",
    "classification",
    "proposal",
    "acceptance",
    "execution",
    "binding",
    "review",
    "replacement",
)

INSPECTION_AXES: Final[tuple[str, ...]] = (
    "pointer",
    "manifest",
    "report",
    "ordering",
    "script",
    "return_code",
    "output",
    "diagnostic",
    "mutation",
)


class InspectionError(RuntimeError):
    """Raised when the pipeline run cannot be inspected reliably."""


@dataclass(frozen=True, slots=True)
class InspectedStage:
    ordinal: int
    key: str
    script: str
    operation: str
    output: str
    script_exists: bool
    output_exists_before: bool
    output_exists_after: bool
    output_json_valid: bool
    return_code: int | None
    passed: bool
    blocker: str | None
    stdout: str
    stderr: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InspectionError(
            f"required JSON file missing: {path}"
        )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise InspectionError(
            f"cannot load JSON {path}: {error}"
        ) from error

    if not isinstance(value, dict):
        raise InspectionError(
            f"JSON root must be an object: {path}"
        )

    return value


def require_path(
    document: dict[str, Any],
    key: str,
    source: Path,
) -> Path:
    value = document.get(key)

    if not isinstance(value, str):
        raise InspectionError(
            f"{source} lacks string path field {key!r}"
        )

    path = Path(value)

    if not path.is_absolute():
        raise InspectionError(
            f"{source} contains non-absolute {key!r}: {path}"
        )

    try:
        path.resolve(
            strict=False
        ).relative_to(
            ROOT.resolve()
        )
    except (
        OSError,
        ValueError,
    ) as error:
        raise InspectionError(
            f"{source} contains path outside runtime root: {path}"
        ) from error

    return path


def verify_manifest(
    manifest_path: Path,
) -> tuple[dict[str, Any], ...]:
    manifest = load_json(
        manifest_path
    )

    entries = manifest.get(
        "entries"
    )

    if not isinstance(
        entries,
        list,
    ):
        raise InspectionError(
            "pipeline manifest entries must be an array"
        )

    verified_entries: list[
        dict[str, Any]
    ] = []

    for ordinal, entry in enumerate(
        entries,
        start=1,
    ):
        if not isinstance(
            entry,
            dict,
        ):
            raise InspectionError(
                f"manifest entry {ordinal} must be an object"
            )

        raw_path = entry.get(
            "path"
        )

        expected_digest = entry.get(
            "sha256"
        )

        expected_size = entry.get(
            "size"
        )

        if not isinstance(
            raw_path,
            str,
        ):
            raise InspectionError(
                f"manifest entry {ordinal} lacks path"
            )

        if not isinstance(
            expected_digest,
            str,
        ):
            raise InspectionError(
                f"manifest entry {ordinal} lacks sha256"
            )

        if not isinstance(
            expected_size,
            int,
        ):
            raise InspectionError(
                f"manifest entry {ordinal} lacks size"
            )

        path = Path(raw_path)

        if not path.is_file():
            raise InspectionError(
                f"manifest file missing: {path}"
            )

        content = path.read_bytes()
        actual_digest = sha256_bytes(
            content
        )

        if actual_digest != expected_digest:
            raise InspectionError(
                f"manifest digest mismatch: {path}"
            )

        if len(content) != expected_size:
            raise InspectionError(
                f"manifest size mismatch: {path}"
            )

        verified_entries.append(
            {
                "path": str(path),
                "sha256": actual_digest,
                "size": len(content),
                "passed": True,
            }
        )

    return tuple(
        verified_entries
    )


def inspect_stage(
    raw_stage: dict[str, Any],
) -> InspectedStage:
    ordinal = raw_stage.get(
        "ordinal"
    )

    if not isinstance(
        ordinal,
        int,
    ):
        raise InspectionError(
            "pipeline stage lacks integer ordinal"
        )

    key = raw_stage.get(
        "key"
    )

    if not isinstance(
        key,
        str,
    ):
        raise InspectionError(
            f"pipeline stage {ordinal} lacks key"
        )

    script = raw_stage.get(
        "script"
    )

    operation = raw_stage.get(
        "operation"
    )

    output = raw_stage.get(
        "output"
    )

    if not isinstance(
        script,
        str,
    ):
        raise InspectionError(
            f"pipeline stage {ordinal} lacks script path"
        )

    if not isinstance(
        operation,
        str,
    ):
        raise InspectionError(
            f"pipeline stage {ordinal} lacks operation"
        )

    if not isinstance(
        output,
        str,
    ):
        raise InspectionError(
            f"pipeline stage {ordinal} lacks output path"
        )

    script_path = Path(
        script
    )

    output_path = Path(
        output
    )

    output_json_valid = False

    if output_path.is_file():
        try:
            load_json(
                output_path
            )
            output_json_valid = True
        except InspectionError:
            output_json_valid = False

    return InspectedStage(
        ordinal=ordinal,
        key=key,
        script=script,
        operation=operation,
        output=output,
        script_exists=(
            script_path.is_file()
        ),
        output_exists_before=(
            raw_stage.get(
                "output_exists_before"
            )
            is True
        ),
        output_exists_after=(
            output_path.is_file()
        ),
        output_json_valid=(
            output_json_valid
        ),
        return_code=(
            raw_stage.get(
                "return_code"
            )
            if isinstance(
                raw_stage.get(
                    "return_code"
                ),
                int,
            )
            else None
        ),
        passed=(
            raw_stage.get(
                "passed"
            )
            is True
        ),
        blocker=(
            str(
                raw_stage.get(
                    "blocker"
                )
            )
            if raw_stage.get(
                "blocker"
            )
            is not None
            else None
        ),
        stdout=str(
            raw_stage.get(
                "stdout",
                "",
            )
        ),
        stderr=str(
            raw_stage.get(
                "stderr",
                "",
            )
        ),
    )


def derive_first_blocker(
    stages: tuple[InspectedStage, ...],
) -> str | None:
    for stage in stages:
        if not stage.script_exists:
            return (
                f"{stage.key}: stage script is missing: "
                f"{stage.script}"
            )

        if (
            stage.return_code is not None
            and stage.return_code
            not in {
                0,
                2,
            }
        ):
            return (
                f"{stage.key}: stage returned "
                f"{stage.return_code}"
            )

        if not stage.output_exists_after:
            return (
                f"{stage.key}: required output is missing: "
                f"{stage.output}"
            )

        if not stage.output_json_valid:
            return (
                f"{stage.key}: required output is not valid JSON: "
                f"{stage.output}"
            )

        if not stage.passed:
            return (
                f"{stage.key}: "
                f"{stage.blocker or 'stage reports failure'}"
            )

    if len(stages) < len(
        EXPECTED_STAGE_KEYS
    ):
        next_key = EXPECTED_STAGE_KEYS[
            len(stages)
        ]

        return (
            f"{next_key}: stage was not executed"
        )

    return None


def inspect_pipeline() -> dict[str, Any]:
    latest = load_json(
        LATEST_PIPELINE
    )

    report_path = require_path(
        latest,
        "report",
        LATEST_PIPELINE,
    )

    manifest_path = require_path(
        latest,
        "manifest",
        LATEST_PIPELINE,
    )

    verified_manifest_entries = (
        verify_manifest(
            manifest_path
        )
    )

    report = load_json(
        report_path
    )

    raw_stages = report.get(
        "stages"
    )

    if not isinstance(
        raw_stages,
        list,
    ):
        raise InspectionError(
            "pipeline report stages must be an array"
        )

    stages = tuple(
        inspect_stage(
            raw_stage
        )
        for raw_stage in raw_stages
        if isinstance(
            raw_stage,
            dict,
        )
    )

    if len(stages) != len(
        raw_stages
    ):
        raise InspectionError(
            "pipeline report contains non-object stages"
        )

    expected_ordinals = list(
        range(
            1,
            len(stages) + 1,
        )
    )

    actual_ordinals = [
        stage.ordinal
        for stage in stages
    ]

    if actual_ordinals != expected_ordinals:
        raise InspectionError(
            "pipeline stage ordinals are not contiguous"
        )

    actual_keys = tuple(
        stage.key
        for stage in stages
    )

    expected_prefix = (
        EXPECTED_STAGE_KEYS[
            :len(stages)
        ]
    )

    if actual_keys != expected_prefix:
        raise InspectionError(
            "pipeline stage order differs from authority"
        )

    derived_first_blocker = (
        derive_first_blocker(
            stages
        )
    )

    recorded_first_blocker = (
        report.get(
            "first_blocker"
        )
    )

    if (
        recorded_first_blocker
        is not None
        and not isinstance(
            recorded_first_blocker,
            str,
        )
    ):
        raise InspectionError(
            "pipeline first_blocker must be null or a string"
        )

    blocker_consistent = (
        derived_first_blocker
        == recorded_first_blocker
    )

    pipeline_passed = (
        report.get(
            "passed"
        )
        is True
    )

    mutation_performed = (
        report.get(
            "implementation_mutation_performed"
        )
        is True
    )

    return {
        "operation": (
            "inspect_modular_pipeline"
        ),
        "passed": True,
        "pipeline_passed": (
            pipeline_passed
        ),
        "stage_count": len(
            EXPECTED_STAGE_KEYS
        ),
        "executed_stage_count": len(
            stages
        ),
        "recorded_first_blocker": (
            recorded_first_blocker
        ),
        "derived_first_blocker": (
            derived_first_blocker
        ),
        "blocker_consistent": (
            blocker_consistent
        ),
        "implementation_mutation_performed": (
            mutation_performed
        ),
        "inspection_axes": list(
            INSPECTION_AXES
        ),
        "manifest_entry_count": len(
            verified_manifest_entries
        ),
        "manifest_entries": list(
            verified_manifest_entries
        ),
        "stages": [
            asdict(stage)
            for stage in stages
        ],
    }


def print_human(
    result: dict[str, Any],
) -> None:
    print(
        "pipeline passed:",
        result["pipeline_passed"],
    )

    print(
        "executed stages:",
        result[
            "executed_stage_count"
        ],
        "/",
        result["stage_count"],
    )

    print(
        "first blocker:",
        result[
            "derived_first_blocker"
        ],
    )

    print(
        "blocker consistent:",
        result[
            "blocker_consistent"
        ],
    )

    print(
        "implementation mutation:",
        result[
            "implementation_mutation_performed"
        ],
    )

    for stage in result[
        "stages"
    ]:
        print()

        print(
            f"{stage['ordinal']}. "
            f"{stage['key']}"
        )

        print(
            "script:",
            stage["script"],
        )

        print(
            "script exists:",
            stage[
                "script_exists"
            ],
        )

        print(
            "operation:",
            stage[
                "operation"
            ],
        )

        print(
            "return code:",
            stage[
                "return_code"
            ],
        )

        print(
            "output:",
            stage[
                "output"
            ],
        )

        print(
            "output exists:",
            stage[
                "output_exists_after"
            ],
        )

        print(
            "output JSON valid:",
            stage[
                "output_json_valid"
            ],
        )

        print(
            "passed:",
            stage[
                "passed"
            ],
        )

        if stage[
            "blocker"
        ]:
            print(
                "blocker:",
                stage[
                    "blocker"
                ],
            )

        if stage[
            "stdout"
        ].strip():
            print(
                "stdout:"
            )

            print(
                stage[
                    "stdout"
                ].strip()
            )

        if stage[
            "stderr"
        ].strip():
            print(
                "stderr:"
            )

            print(
                stage[
                    "stderr"
                ].strip()
            )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the latest Savant "
            "modular-pipeline run."
        )
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print the complete inspection "
            "as JSON."
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        result = inspect_pipeline()

        if arguments.json:
            print(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print_human(
                result
            )

        return 0

    except InspectionError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        "inspect_modular_pipeline"
                    ),
                    "passed": False,
                    "error": str(
                        error
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
