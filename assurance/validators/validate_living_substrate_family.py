#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


ROOT = Path("/root/savant-runtime")


SUBSTRATES = (
    "scyon",
    "splyce",
    "scrybe",
    "pryme",
    "cypher",
    "thryce",
    "spyral",
    "lythe",
    "dryve",
)


@dataclass(
    frozen=True,
    slots=True,
)
class CommandSpec:
    substrate: str
    command: tuple[str, ...]
    output_kind: str
    required_truths: tuple[
        tuple[str, Any],
        ...,
    ] = ()


class FamilyValidationError(
    RuntimeError
):
    pass


def nested_get(
    value: Any,
    path: str,
) -> Any:
    current = value

    for component in path.split("."):
        if not isinstance(
            current,
            dict,
        ):
            return None

        current = current.get(
            component
        )

    return current


def run(
    command: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=180,
    )


def parse_json_output(
    output: str,
) -> Any:
    stripped = output.strip()

    if not stripped:
        raise FamilyValidationError(
            "command returned no output"
        )

    try:
        return json.loads(
            stripped
        )
    except json.JSONDecodeError:
        pass

    starts = [
        index
        for index, character
        in enumerate(stripped)
        if character in "[{"
    ]

    for index in reversed(starts):
        candidate = stripped[
            index:
        ]

        try:
            return json.loads(
                candidate
            )
        except json.JSONDecodeError:
            continue

    raise FamilyValidationError(
        "JSON output could not be parsed"
    )


def executable(
    path: Path,
) -> bool:
    return (
        path.is_file()
        and os.access(
            path,
            os.X_OK,
        )
    )


def validate_command(
    specification: CommandSpec,
) -> dict[str, Any]:
    process = run(
        specification.command
    )

    result: dict[str, Any] = {
        "command": list(
            specification.command
        ),
        "returncode":
            process.returncode,
        "passed":
            process.returncode == 0,
        "checks": {},
    }

    if (
        process.returncode != 0
    ):
        result["output"] = (
            process.stdout[-6000:]
        )

        return result

    if (
        specification.output_kind
        == "returncode"
    ):
        return result

    try:
        payload = parse_json_output(
            process.stdout
        )
    except FamilyValidationError as exc:
        result["passed"] = False
        result["error"] = str(exc)
        result["output"] = (
            process.stdout[-6000:]
        )

        return result

    result["payload"] = payload

    for path, expected in (
        specification
        .required_truths
    ):
        observed = nested_get(
            payload,
            path,
        )

        passed = (
            observed == expected
        )

        result[
            "checks"
        ][path] = {
            "expected":
                expected,
            "observed":
                observed,
            "passed":
                passed,
        }

        if not passed:
            result["passed"] = False

    return result


def source_contains(
    path: Path,
    value: str,
) -> bool:
    if not path.is_file():
        return False

    return (
        value
        in path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )


def main() -> int:
    bins = {
        name:
            ROOT
            / "bin"
            / (
                "scyonctl"
                if name == "scyon"
                else name
            )
        for name
        in SUBSTRATES
    }

    runtime_roots = {
        name:
            ROOT
            / "runtime"
            / name
        for name
        in SUBSTRATES
        if name
        not in (
            "splyce",
        )
    }

    splyce_root = (
        ROOT
        / "ontology/obelisks/_template/"
          "segue/gates/_template/segue/"
          "innates/_template/segue/exiles/"
          "segue/exile_runtime/ui"
    )

    architecture = (
        ROOT
        / "canon/structure/"
          "SAVANT_LIVING_SUBSTRATE_ARCHITECTURE_v1.0.0.md"
    )

    presence: dict[
        str,
        Any,
    ] = {
        "family_count":
            len(SUBSTRATES),

        "family_count_valid":
            len(SUBSTRATES) == 9,

        "unique_names":
            len(
                set(
                    SUBSTRATES
                )
            )
            == 9,

        "architecture_present":
            architecture.is_file(),

        "splyce_root_present":
            splyce_root.is_dir(),

        "runtime_roots": {
            name:
                path.is_dir()
            for name, path
            in runtime_roots.items()
        },

        "executables": {
            name:
                executable(
                    path
                )
            for name, path
            in bins.items()
        },
    }

    command_specs = (
        CommandSpec(
            substrate="scyon",
            command=(
                str(
                    bins["scyon"]
                ),
                "verify",
            ),
            output_kind="returncode",
        ),

        CommandSpec(
            substrate="splyce",
            command=(
                str(
                    bins["splyce"]
                ),
                "verify",
            ),
            output_kind="returncode",
        ),

        CommandSpec(
            substrate="scrybe",
            command=(
                str(
                    bins["scrybe"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "invariants.independent_memory_store",
                    False,
                ),
            ),
        ),

        CommandSpec(
            substrate="pryme",
            command=(
                str(
                    bins["pryme"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "authority_manufacture_authorized",
                    False,
                ),
                (
                    "confidence_used_for_precedence",
                    False,
                ),
                (
                    "filesystem_used_for_precedence",
                    False,
                ),
            ),
        ),

        CommandSpec(
            substrate="cypher",
            command=(
                str(
                    bins["cypher"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "authoritative",
                    False,
                ),
                (
                    "mutation_authorized",
                    False,
                ),
            ),
        ),

        CommandSpec(
            substrate="thryce",
            command=(
                str(
                    bins["thryce"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "attestation_authorized",
                    False,
                ),
                (
                    "evidence_admission_authorized",
                    False,
                ),
            ),
        ),

        CommandSpec(
            substrate="spyral",
            command=(
                str(
                    bins["spyral"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "mutation_authorized",
                    False,
                ),
                (
                    "migration_execution_authorized",
                    False,
                ),
            ),
        ),

        CommandSpec(
            substrate="lythe",
            command=(
                str(
                    bins["lythe"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "projection_execution_authorized",
                    False,
                ),
                (
                    "projection_execution_owner",
                    "exile:filament",
                ),
            ),
        ),

        CommandSpec(
            substrate="dryve",
            command=(
                str(
                    bins["dryve"]
                ),
                "validate",
            ),
            output_kind="json",
            required_truths=(
                (
                    "valid",
                    True,
                ),
                (
                    "pipeline_stage_count",
                    18,
                ),
                (
                    "enhancement_count",
                    27,
                ),
                (
                    "task_authority_owned",
                    False,
                ),
                (
                    "ai_execution_owned",
                    False,
                ),
                (
                    "durable_commit_authorized",
                    False,
                ),
            ),
        ),
    )

    validations: dict[
        str,
        dict[str, Any],
    ] = {}

    for specification in (
        command_specs
    ):
        binary = bins[
            specification.substrate
        ]

        if not executable(
            binary
        ):
            validations[
                specification.substrate
            ] = {
                "passed":
                    False,
                "error":
                    "executable missing "
                    "or not executable",
                "path":
                    str(binary),
            }

            continue

        validations[
            specification.substrate
        ] = validate_command(
            specification
        )

    boundary_sources = {
        "scrybe": (
            ROOT
            / "runtime/scrybe/"
              "engine.py"
        ),

        "pryme": (
            ROOT
            / "runtime/pryme/"
              "engine.py"
        ),

        "thryce": (
            ROOT
            / "runtime/thryce/"
              "engine.py"
        ),

        "spyral": (
            ROOT
            / "runtime/spyral/"
              "engine.py"
        ),

        "lythe": (
            ROOT
            / "runtime/lythe/"
              "engine.py"
        ),

        "dryve": (
            ROOT
            / "runtime/dryve/"
              "engine.py"
        ),
    }

    boundaries = {
        "scrybe_no_independent_store":
            source_contains(
                boundary_sources[
                    "scrybe"
                ],
                "independent_memory_store",
            ),

        "pryme_no_authority_manufacture":
            source_contains(
                boundary_sources[
                    "pryme"
                ],
                "authority_manufacture_authorized",
            ),

        "thryce_notary_boundary":
            source_contains(
                boundary_sources[
                    "thryce"
                ],
                "attestation_authorized",
            )
            and source_contains(
                boundary_sources[
                    "thryce"
                ],
                "evidence_admission_authorized",
            ),

        "spyral_no_migration_execution":
            source_contains(
                boundary_sources[
                    "spyral"
                ],
                "migration_execution_authorized",
            ),

        "lythe_filament_boundary":
            source_contains(
                boundary_sources[
                    "lythe"
                ],
                "projection_execution_authorized",
            )
            and source_contains(
                boundary_sources[
                    "lythe"
                ],
                "exile:filament",
            ),

        "dryve_niche_opus_boundary":
            source_contains(
                boundary_sources[
                    "dryve"
                ],
                "task_authority_owned",
            )
            and source_contains(
                boundary_sources[
                    "dryve"
                ],
                "ai_execution_owned",
            ),
    }

    presence_valid = (
        presence[
            "family_count_valid"
        ]
        and presence[
            "unique_names"
        ]
        and presence[
            "architecture_present"
        ]
        and presence[
            "splyce_root_present"
        ]
        and all(
            presence[
                "runtime_roots"
            ].values()
        )
        and all(
            presence[
                "executables"
            ].values()
        )
    )

    validations_valid = all(
        result.get(
            "passed",
            False,
        )
        for result
        in validations.values()
    )

    boundaries_valid = all(
        boundaries.values()
    )

    report = {
        "schema": (
            "savant://assurance/"
            "living-substrate-family/1.0.0"
        ),

        "family": list(
            SUBSTRATES
        ),

        "family_count": 9,

        "presence":
            presence,

        "validations":
            validations,

        "boundaries":
            boundaries,

        "requirements": {
            "instanceable":
                True,

            "specialization_layer":
                True,

            "minimum_enhancements":
                20,

            "enterprise_grade_required":
                True,

            "new_identity_tier_created":
                False,

            "runtime_layer_is_ontology_child":
                False,
        },

        "valid": (
            presence_valid
            and validations_valid
            and boundaries_valid
        ),
    }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    if report["valid"]:
        print(
            "LIVING SUBSTRATE FAMILY: passed",
            file=sys.stderr,
        )

        return 0

    print(
        "LIVING SUBSTRATE FAMILY: failed",
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
