#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

IDENTITY_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
)

PROFILE_PATH = (
    ROOT
    / "tools"
    / "identity_quality"
    / "nocturne_reference_profile.json"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "nocturne"
)

NOCTURNE_IDS = {
    "prodigal.nocturne",
    "quirk.nocturne.veil",
    "quirk.nocturne.lantern",
    "quirk.nocturne.scribe",
    "quirk.nocturne.echo",
}

SEARCH_ALIASES = {
    "prodigal.nocturne": {
        "nocturne",
    },
    "quirk.nocturne.veil": {
        "veil",
    },
    "quirk.nocturne.lantern": {
        "lantern",
    },
    "quirk.nocturne.scribe": {
        "scribe",
    },
    "quirk.nocturne.echo": {
        "echo",
    },
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
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


def find_definitions() -> dict[str, Path]:
    found: dict[str, Path] = {}

    for path in sorted(
        IDENTITY_ROOT.rglob(
            "definition.json"
        )
    ):
        try:
            value = load_json(path)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ):
            continue

        identifier = value.get("id")

        if isinstance(identifier, str):
            found[identifier] = path

    return found


def discover_runtime_evidence(
    identifier: str,
) -> list[str]:
    aliases = SEARCH_ALIASES.get(
        identifier,
        {
            identifier.rsplit(".", 1)[-1],
        },
    )

    candidates: list[str] = []

    search_roots = [
        ROOT / "ontology",
        ROOT / "runtime",
        ROOT / "tools",
        ROOT / "bin",
        ROOT / "canon-system",
    ]

    for search_root in search_roots:
        if not search_root.is_dir():
            continue

        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            lowered = path.name.lower()

            if any(
                alias.lower() in lowered
                for alias in aliases
            ):
                candidates.append(
                    path.relative_to(ROOT).as_posix()
                )

            if len(candidates) >= 250:
                break

        if len(candidates) >= 250:
            break

    return sorted(
        set(candidates)
    )


def field_complete(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return bool(value)

    if isinstance(value, dict):
        return bool(value)

    return True


def assess_definition(
    identifier: str,
    path: Path,
    profile: dict[str, Any],
) -> dict[str, Any]:
    value = load_json(path)

    required_fields = [
        "authority",
        "composition",
        "contracts",
        "capabilities",
        "dependencies",
        "relationships",
        "lineage",
        "provenance",
        "runtime",
        "security",
        "observability",
        "validation",
        "lifecycle",
        "apertures",
    ]

    fields = {
        field: field_complete(
            value.get(field)
        )
        for field in required_fields
    }

    runtime = value.get("runtime")

    if isinstance(runtime, dict):
        implementation = runtime.get(
            "implementation",
            "unknown",
        )
        entrypoints = runtime.get(
            "entrypoints",
            [],
        )
    else:
        implementation = "unknown"
        entrypoints = []

    missing = [
        field
        for field, complete in fields.items()
        if not complete
    ]

    runtime_evidence = (
        discover_runtime_evidence(
            identifier
        )
    )

    quirk_contracts = profile.get(
        "quirk_contracts",
        {},
    )

    reference_contract = (
        quirk_contracts.get(identifier)
        if isinstance(
            quirk_contracts,
            dict,
        )
        else None
    )

    tasks: list[dict[str, Any]] = []

    priority = 1

    for field in missing:
        tasks.append(
            {
                "priority": priority,
                "id": (
                    f"{identifier}.complete.{field}"
                ),
                "action": (
                    f"Complete authoritative "
                    f"{field} definition."
                ),
                "status": "required",
            }
        )
        priority += 1

    if implementation not in {
        "complete",
    }:
        tasks.append(
            {
                "priority": priority,
                "id": (
                    f"{identifier}.runtime"
                ),
                "action": (
                    "Implement bounded runtime behavior "
                    "through declared contracts without "
                    "fabricating unavailable capabilities."
                ),
                "status": "required",
            }
        )
        priority += 1

    if not entrypoints:
        tasks.append(
            {
                "priority": priority,
                "id": (
                    f"{identifier}.entrypoint"
                ),
                "action": (
                    "Create one canonical standalone "
                    "developer-facing entrypoint."
                ),
                "status": "required",
            }
        )
        priority += 1

    tasks.extend(
        [
            {
                "priority": priority,
                "id": (
                    f"{identifier}.unit_tests"
                ),
                "action": (
                    "Add unit and contract tests for "
                    "independent bounded behavior."
                ),
                "status": "required",
            },
            {
                "priority": priority + 1,
                "id": (
                    f"{identifier}.property_tests"
                ),
                "action": (
                    "Add property tests for determinism, "
                    "lineage, provenance, and access bounds."
                ),
                "status": "required",
            },
            {
                "priority": priority + 2,
                "id": (
                    f"{identifier}.security_tests"
                ),
                "action": (
                    "Add denial-by-default security tests."
                ),
                "status": "required",
            },
            {
                "priority": priority + 3,
                "id": (
                    f"{identifier}.observability"
                ),
                "action": (
                    "Emit structured execution, success, "
                    "failure, duration, dependency, and "
                    "provenance observations."
                ),
                "status": "required",
            },
        ]
    )

    return {
        "id": identifier,
        "path": path.relative_to(
            ROOT
        ).as_posix(),
        "definition_sha256": hashlib.sha256(
            path.read_bytes()
        ).hexdigest(),
        "fields": fields,
        "missing_fields": missing,
        "runtime_implementation": implementation,
        "declared_entrypoints": entrypoints,
        "runtime_evidence": runtime_evidence,
        "reference_contract": reference_contract,
        "tasks": tasks,
    }


def markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Nocturne Reference Upgrade Plan",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- Digest: `{result['digest']}`",
        f"- Definitions found: **{result['statistics']['found']}**",
        f"- Definitions missing: **{result['statistics']['missing']}**",
        f"- Required tasks: **{result['statistics']['task_count']}**",
        "",
        "## Execution order",
        "",
        "1. Veil",
        "2. Lantern",
        "3. Scribe",
        "4. Echo",
        "5. Nocturne composition runtime",
        "6. Opus attachment",
        "7. End-to-end validation",
        "8. Reference-quality attestation",
        "",
    ]

    for record in result["records"]:
        lines.extend(
            [
                f"## {record['id']}",
                "",
                f"- Definition: `{record['path']}`",
                f"- Runtime state: `{record['runtime_implementation']}`",
                f"- Missing fields: `{', '.join(record['missing_fields']) or 'none'}`",
                f"- Runtime evidence files: **{len(record['runtime_evidence'])}**",
                "",
                "### Tasks",
                "",
            ]
        )

        for task in record["tasks"]:
            lines.append(
                f"{task['priority']}. "
                f"`{task['id']}` — "
                f"{task['action']}"
            )

        lines.append("")

    if result["missing"]:
        lines.extend(
            [
                "## Missing definitions",
                "",
            ]
        )

        for identifier in result["missing"]:
            lines.append(
                f"- `{identifier}`"
            )

        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not PROFILE_PATH.is_file():
        print(
            f"ERROR: profile missing: {PROFILE_PATH}",
            file=sys.stderr,
        )
        return 2

    profile = load_json(
        PROFILE_PATH
    )

    definitions = find_definitions()

    records: list[dict[str, Any]] = []
    missing: list[str] = []

    execution_order = [
        "quirk.nocturne.veil",
        "quirk.nocturne.lantern",
        "quirk.nocturne.scribe",
        "quirk.nocturne.echo",
        "prodigal.nocturne",
    ]

    for identifier in execution_order:
        path = definitions.get(identifier)

        if path is None:
            missing.append(identifier)
            continue

        records.append(
            assess_definition(
                identifier,
                path,
                profile,
            )
        )

    result: dict[str, Any] = {
        "generated_at": utc_now(),
        "profile": str(
            PROFILE_PATH.relative_to(ROOT)
        ),
        "profile_sha256": hashlib.sha256(
            PROFILE_PATH.read_bytes()
        ).hexdigest(),
        "records": records,
        "missing": missing,
        "statistics": {
            "expected": len(execution_order),
            "found": len(records),
            "missing": len(missing),
            "task_count": sum(
                len(record["tasks"])
                for record in records
            ),
        },
    }

    result["digest"] = digest(
        result
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_json(
        REPORT_ROOT
        / "upgrade_plan.json",
        result,
    )

    (
        REPORT_ROOT
        / "upgrade_plan.md"
    ).write_text(
        markdown(result),
        encoding="utf-8",
    )

    write_json(
        REPORT_ROOT
        / "manifest.json",
        {
            "generated_at": result[
                "generated_at"
            ],
            "plan_digest": result[
                "digest"
            ],
            "files": {
                "upgrade_plan.json": hashlib.sha256(
                    (
                        REPORT_ROOT
                        / "upgrade_plan.json"
                    ).read_bytes()
                ).hexdigest(),
                "upgrade_plan.md": hashlib.sha256(
                    (
                        REPORT_ROOT
                        / "upgrade_plan.md"
                    ).read_bytes()
                ).hexdigest(),
            },
        },
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_nocturne_upgrade_plan"
                ),
                "passed": not missing,
                "digest": result["digest"],
                "statistics": result[
                    "statistics"
                ],
                "reports": {
                    "json": str(
                        REPORT_ROOT
                        / "upgrade_plan.json"
                    ),
                    "markdown": str(
                        REPORT_ROOT
                        / "upgrade_plan.md"
                    ),
                    "manifest": str(
                        REPORT_ROOT
                        / "manifest.json"
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
