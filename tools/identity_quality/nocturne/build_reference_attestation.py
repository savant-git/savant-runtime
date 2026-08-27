#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("/root/savant-runtime")

NOCTURNE_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "opus"
    / "prodigals"
    / "nocturne"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "nocturne"
)

ATTESTATION_ROOT = (
    REPORT_ROOT
    / "attestations"
)

PROFILE = (
    ROOT
    / "tools"
    / "identity_quality"
    / "nocturne_reference_profile.json"
)

UPGRADE_PLAN = (
    REPORT_ROOT
    / "upgrade_plan.json"
)

QUALITY_REPORT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "identity_quality_report.json"
)

QUALITY_SUMMARY = (
    ROOT
    / "reports"
    / "identity_quality"
    / "identity_quality_summary.json"
)

COMPONENTS = {
    "veil": {
        "controller": ROOT / "bin" / "veilctl",
        "definition": (
            NOCTURNE_ROOT
            / "quirks"
            / "veil"
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "quirks"
            / "veil"
            / "runtime"
            / "veil_runtime.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "quirks"
            / "veil"
            / "tests"
            / "test_veil_runtime.py"
        ),
    },
    "lantern": {
        "controller": ROOT / "bin" / "lanternctl",
        "definition": (
            NOCTURNE_ROOT
            / "quirks"
            / "lantern"
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "quirks"
            / "lantern"
            / "runtime"
            / "lantern_runtime.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "quirks"
            / "lantern"
            / "tests"
            / "test_lantern_runtime.py"
        ),
    },
    "scribe": {
        "controller": ROOT / "bin" / "scribectl",
        "definition": (
            NOCTURNE_ROOT
            / "quirks"
            / "scribe"
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "quirks"
            / "scribe"
            / "runtime"
            / "scribe_runtime.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "quirks"
            / "scribe"
            / "tests"
            / "test_scribe_runtime.py"
        ),
    },
    "echo": {
        "controller": ROOT / "bin" / "echoctl",
        "definition": (
            NOCTURNE_ROOT
            / "quirks"
            / "echo"
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "quirks"
            / "echo"
            / "runtime"
            / "echo_runtime.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "quirks"
            / "echo"
            / "tests"
            / "test_echo_runtime.py"
        ),
    },
    "nocturne": {
        "controller": ROOT / "bin" / "nocturnectl",
        "definition": (
            NOCTURNE_ROOT
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "runtime"
            / "nocturne_runtime.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "tests"
            / "test_nocturne_runtime.py"
        ),
    },
    "opus_attachment": {
        "controller": ROOT / "bin" / "opus-nocturnectl",
        "definition": (
            NOCTURNE_ROOT
            / "definition.json"
        ),
        "runtime": (
            NOCTURNE_ROOT
            / "adapters"
            / "opus"
            / "opus_nocturne_adapter.py"
        ),
        "tests": (
            NOCTURNE_ROOT
            / "adapters"
            / "opus"
            / "tests"
            / "test_opus_nocturne_adapter.py"
        ),
    },
}

CONTRACT_FILES = (
    NOCTURNE_ROOT
    / "contracts"
    / "nocturne_contracts.py",
    NOCTURNE_ROOT
    / "contracts"
    / "lantern_contracts.py",
    NOCTURNE_ROOT
    / "contracts"
    / "scribe_contracts.py",
    NOCTURNE_ROOT
    / "contracts"
    / "echo_contracts.py",
    NOCTURNE_ROOT
    / "contracts"
    / "nocturne_fusion_contracts.py",
    NOCTURNE_ROOT
    / "contracts"
    / "opus_attachment_contracts.py",
)

VOLATILE_FIELDS = {
    "generated_at",
    "duration_seconds",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def sha256_path(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def deterministic_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run_command(
    command: list[str],
) -> dict[str, Any]:
    started = utc_now()

    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )

    return {
        "command": command,
        "started_at": started,
        "finished_at": utc_now(),
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": hashlib.sha256(
            completed.stdout.encode("utf-8")
        ).hexdigest(),
        "stderr_sha256": hashlib.sha256(
            completed.stderr.encode("utf-8")
        ).hexdigest(),
    }


def inspect_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": path.relative_to(ROOT).as_posix()
        if path.is_absolute() and ROOT in path.parents
        else str(path),
        "exists": path.is_file(),
    }

    if path.is_file():
        stat = path.stat()

        record.update(
            {
                "size": stat.st_size,
                "mode": oct(
                    stat.st_mode & 0o777
                ),
                "sha256": sha256_path(path),
            }
        )

    return record


def inspect_definition(
    path: Path,
) -> dict[str, Any]:
    record = inspect_file(path)

    if not path.is_file():
        record["valid_json"] = False
        return record

    try:
        value = load_json(path)

    except Exception as exc:
        record["valid_json"] = False
        record["error"] = repr(exc)
        return record

    record["valid_json"] = True
    record["id"] = value.get("id")
    record["kind"] = value.get("kind")
    record["status"] = value.get("status")
    record["runtime"] = value.get("runtime")
    record["authority"] = value.get("authority")
    record["lineage"] = value.get("lineage")
    record["provenance"] = value.get("provenance")
    record["dependencies"] = value.get("dependencies")
    record["relationships"] = value.get("relationships")
    record["validation"] = value.get("validation")
    record["apertures"] = value.get("apertures")

    return record


def component_attestation(
    name: str,
    configuration: dict[str, Path],
) -> dict[str, Any]:
    controller = configuration["controller"]

    command_result = run_command(
        [
            str(controller),
            "verify",
        ]
    )

    definition = inspect_definition(
        configuration["definition"]
    )

    runtime = inspect_file(
        configuration["runtime"]
    )

    tests = inspect_file(
        configuration["tests"]
    )

    passed = all(
        (
            command_result["passed"],
            bool(definition.get("exists")),
            bool(definition.get("valid_json")),
            bool(runtime.get("exists")),
            bool(tests.get("exists")),
        )
    )

    result = {
        "name": name,
        "passed": passed,
        "controller": inspect_file(
            controller
        ),
        "verification": command_result,
        "definition": definition,
        "runtime": runtime,
        "tests": tests,
    }

    result["deterministic_digest"] = digest(
        deterministic_projection(result)
    )

    return result


def contract_attestation() -> dict[str, Any]:
    files = [
        inspect_file(path)
        for path in CONTRACT_FILES
    ]

    passed = all(
        record["exists"]
        for record in files
    )

    return {
        "passed": passed,
        "files": files,
        "deterministic_digest": digest(
            deterministic_projection(files)
        ),
    }


def quality_attestation() -> dict[str, Any]:
    audit = run_command(
        [
            str(
                ROOT
                / "bin"
                / "identityqualityctl"
            ),
            "audit",
        ]
    )

    validation = run_command(
        [
            str(
                ROOT
                / "bin"
                / "identityqualityctl"
            ),
            "validate",
        ]
    )

    plan = run_command(
        [
            str(
                ROOT
                / "bin"
                / "identity-quality-python"
            ),
            str(
                ROOT
                / "tools"
                / "identity_quality"
                / "build_nocturne_upgrade_plan.py"
            ),
        ]
    )

    return {
        "passed": all(
            (
                audit["passed"],
                validation["passed"],
                plan["passed"],
            )
        ),
        "audit": audit,
        "validation": validation,
        "upgrade_plan": plan,
        "report_files": {
            "quality_report": inspect_file(
                QUALITY_REPORT
            ),
            "quality_summary": inspect_file(
                QUALITY_SUMMARY
            ),
            "upgrade_plan": inspect_file(
                UPGRADE_PLAN
            ),
        },
    }


def repository_state(
    paths: Iterable[Path],
) -> dict[str, Any]:
    records = [
        inspect_file(path)
        for path in sorted(
            set(paths),
            key=str,
        )
    ]

    existing = [
        record
        for record in records
        if record["exists"]
    ]

    return {
        "file_count": len(records),
        "existing_count": len(existing),
        "missing_count": (
            len(records)
            - len(existing)
        ),
        "files": records,
        "digest": digest(
            deterministic_projection(records)
        ),
    }


def build_attestation() -> dict[str, Any]:
    components = {
        name: component_attestation(
            name,
            configuration,
        )
        for name, configuration
        in COMPONENTS.items()
    }

    contracts = contract_attestation()
    quality = quality_attestation()

    repository_paths: list[Path] = [
        PROFILE,
        UPGRADE_PLAN,
        QUALITY_REPORT,
        QUALITY_SUMMARY,
    ]

    for configuration in COMPONENTS.values():
        repository_paths.extend(
            configuration.values()
        )

    repository_paths.extend(
        CONTRACT_FILES
    )

    repository = repository_state(
        repository_paths
    )

    component_passed = all(
        record["passed"]
        for record in components.values()
    )

    passed = all(
        (
            component_passed,
            contracts["passed"],
            quality["passed"],
            repository["missing_count"] == 0,
        )
    )

    body: dict[str, Any] = {
        "schema": (
            "savant://attestations/"
            "nocturne-reference-quality/1.0.0"
        ),
        "operation": (
            "build_nocturne_reference_attestation"
        ),
        "generated_at": utc_now(),
        "root": str(ROOT),
        "subject": {
            "id": "prodigal.nocturne",
            "parent": "exile.opus",
            "quirks": [
                "quirk.nocturne.veil",
                "quirk.nocturne.lantern",
                "quirk.nocturne.scribe",
                "quirk.nocturne.echo",
            ],
        },
        "profile": inspect_file(
            PROFILE
        ),
        "components": components,
        "contracts": contracts,
        "quality": quality,
        "repository": repository,
        "statistics": {
            "component_count": len(
                components
            ),
            "component_passed_count": sum(
                record["passed"]
                for record in components.values()
            ),
            "component_failed_count": sum(
                not record["passed"]
                for record in components.values()
            ),
            "contract_file_count": len(
                CONTRACT_FILES
            ),
            "repository_file_count": (
                repository["file_count"]
            ),
            "repository_missing_count": (
                repository["missing_count"]
            ),
        },
        "passed": passed,
    }

    body["attestation_digest"] = digest(
        deterministic_projection(body)
    )

    return body


def markdown(
    attestation: dict[str, Any],
) -> str:
    lines = [
        "# Nocturne Reference-Quality Attestation",
        "",
        f"- Generated: `{attestation['generated_at']}`",
        f"- Subject: `{attestation['subject']['id']}`",
        f"- Parent: `{attestation['subject']['parent']}`",
        f"- Passed: **{attestation['passed']}**",
        f"- Digest: `{attestation['attestation_digest']}`",
        "",
        "## Components",
        "",
    ]

    for name, record in attestation[
        "components"
    ].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Passed: **{record['passed']}**",
                (
                    "- Controller: "
                    f"`{record['controller']['path']}`"
                ),
                (
                    "- Definition: "
                    f"`{record['definition']['path']}`"
                ),
                (
                    "- Runtime: "
                    f"`{record['runtime']['path']}`"
                ),
                (
                    "- Tests: "
                    f"`{record['tests']['path']}`"
                ),
                (
                    "- Digest: "
                    f"`{record['deterministic_digest']}`"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Contracts",
            "",
            (
                "- Passed: "
                f"**{attestation['contracts']['passed']}**"
            ),
            (
                "- Digest: "
                f"`{attestation['contracts']['deterministic_digest']}`"
            ),
            "",
            "## Quality",
            "",
            (
                "- Passed: "
                f"**{attestation['quality']['passed']}**"
            ),
            (
                "- Audit: "
                f"**{attestation['quality']['audit']['passed']}**"
            ),
            (
                "- Validation: "
                f"**{attestation['quality']['validation']['passed']}**"
            ),
            (
                "- Upgrade plan: "
                f"**{attestation['quality']['upgrade_plan']['passed']}**"
            ),
            "",
            "## Repository State",
            "",
            (
                "- Files: "
                f"**{attestation['repository']['file_count']}**"
            ),
            (
                "- Missing: "
                f"**{attestation['repository']['missing_count']}**"
            ),
            (
                "- Digest: "
                f"`{attestation['repository']['digest']}`"
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic Nocturne "
            "reference-quality attestation."
        )
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=ATTESTATION_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    output_root = (
        arguments.output_root.resolve()
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    attestation = build_attestation()

    run_id = timestamp()

    json_path = (
        output_root
        / f"{run_id}__nocturne-reference-attestation.json"
    )

    markdown_path = (
        output_root
        / f"{run_id}__nocturne-reference-attestation.md"
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    write_json(
        json_path,
        attestation,
    )

    markdown_value = markdown(
        attestation
    )

    markdown_path.write_text(
        markdown_value,
        encoding="utf-8",
    )

    write_json(
        latest_json,
        attestation,
    )

    latest_markdown.write_text(
        markdown_value,
        encoding="utf-8",
    )

    manifest = {
        "generated_at": attestation[
            "generated_at"
        ],
        "passed": attestation[
            "passed"
        ],
        "attestation_digest": (
            attestation[
                "attestation_digest"
            ]
        ),
        "files": {
            json_path.name: (
                sha256_path(
                    json_path
                )
            ),
            markdown_path.name: (
                sha256_path(
                    markdown_path
                )
            ),
            latest_json.name: (
                sha256_path(
                    latest_json
                )
            ),
            latest_markdown.name: (
                sha256_path(
                    latest_markdown
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / f"{run_id}__manifest.json"
    )

    write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_nocturne_reference_attestation"
                ),
                "passed": attestation[
                    "passed"
                ],
                "attestation_digest": (
                    attestation[
                        "attestation_digest"
                    ]
                ),
                "json": str(
                    json_path
                ),
                "markdown": str(
                    markdown_path
                ),
                "manifest": str(
                    manifest_path
                ),
                "latest_json": str(
                    latest_json
                ),
                "latest_markdown": str(
                    latest_markdown
                ),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not attestation["passed"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
