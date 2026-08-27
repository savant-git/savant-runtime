#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path("/root/savant-runtime")

IDENTITY_ROOT = (
    ROOT
    / "hierarchies"
    / "identity"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
)

NOCTURNE_PROFILE = (
    ROOT
    / "tools"
    / "identity_quality"
    / "nocturne_reference_profile.json"
)

IDENTITY_SCHEMA = (
    ROOT
    / "tools"
    / "identity_quality"
    / "identity_quality.schema.json"
)

REFERENCE_SUBJECTS = {
    "prodigal.nocturne",
    "quirk.nocturne.veil",
    "quirk.nocturne.lantern",
    "quirk.nocturne.scribe",
    "quirk.nocturne.echo",
}

KINSHIP_TERM = "kin" + "ship"

REQUIRED_FIELDS = (
    "id",
    "kind",
    "version",
    "status",
    "identity",
    "purpose",
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
)

REQUIRED_RUNTIME_FIELDS = (
    "implementation",
    "entrypoints",
    "hooks",
    "deterministic",
    "side_effects",
)

REQUIRED_AUTHORITY_FIELDS = (
    "owner",
    "class",
    "precedence",
    "source",
)

REQUIRED_LINEAGE_FIELDS = (
    "parents",
    "sources",
    "supersedes",
    "superseded_by",
)

REQUIRED_PROVENANCE_FIELDS = (
    "created_from",
    "captured_by",
    "source_hashes",
)

REQUIRED_DEPENDENCY_FIELDS = (
    "required",
    "optional",
    "runtime",
    "external",
)

REQUIRED_VALIDATION_FIELDS = (
    "unit_tests",
    "integration_tests",
    "property_tests",
    "security_tests",
    "acceptance",
)

REQUIRED_OBSERVABILITY_FIELDS = (
    "metrics",
    "events",
    "health",
    "audit",
)

REQUIRED_SECURITY_FIELDS = (
    "boundary",
    "permissions",
    "data_classification",
    "network_policy",
    "sandbox",
)

KIND_PRIORITY = {
    "quirk": 0,
    "prodigal": 1,
    "exile": 2,
}

IMPLEMENTATION_SCORE = {
    "complete": 0,
    "partial": 20,
    "prototype": 35,
    "absent": 50,
    "unknown": 45,
}

SEVERITY_WEIGHT = {
    "critical": 100,
    "high": 40,
    "medium": 15,
    "low": 5,
}

TEXT_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".md",
    ".txt",
    ".toml",
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


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


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


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
    )


def looks_like_identity_definition(
    path: Path,
) -> bool:
    if not path.is_file():
        return False

    if path.name == "definition.json":
        return True

    if path.name not in {
        "identity.json",
        "authority.json",
    }:
        return False

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return False

    if not isinstance(
        value,
        dict,
    ):
        return False

    identifier = value.get(
        "id"
    )

    kind = value.get(
        "kind"
    )

    return (
        isinstance(
            identifier,
            str,
        )
        and bool(
            identifier.strip()
        )
        and (
            kind in {
                "exile",
                "prodigal",
                "quirk",
            }
            or any(
                key in value
                for key in (
                    "identity",
                    "authority",
                    "lineage",
                    "composition",
                    "runtime",
                )
            )
        )
    )


def definition_paths() -> list[Path]:
    candidates: set[Path] = set()

    for name in (
        "definition.json",
        "identity.json",
        "authority.json",
    ):
        for path in IDENTITY_ROOT.rglob(
            name
        ):
            if looks_like_identity_definition(
                path
            ):
                candidates.add(
                    path.resolve()
                )

    return sorted(
        candidates,
        key=lambda path: (
            path.as_posix()
        ),
    )


def infer_kind(
    document: dict[str, Any],
    path: Path,
) -> str:
    declared = str(
        document.get(
            "kind",
            "",
        )
    ).strip().lower()

    if declared in {
        "exile",
        "prodigal",
        "quirk",
    }:
        return declared

    lowered_parts = {
        part.lower()
        for part in path.parts
    }

    if "quirks" in lowered_parts:
        return "quirk"

    if "prodigals" in lowered_parts:
        return "prodigal"

    return "exile"


def identity_id(
    document: dict[str, Any],
    path: Path,
) -> str:
    identifier = document.get("id")

    if (
        isinstance(identifier, str)
        and identifier.strip()
    ):
        return identifier.strip()

    kind = infer_kind(
        document,
        path,
    )

    name = path.parent.name.lower()

    if kind == "quirk":
        prodigal = (
            path.parents[2].name.lower()
            if len(path.parents) >= 3
            else "unknown"
        )

        return (
            f"quirk.{prodigal}.{name}"
        )

    return f"{kind}.{name}"


def is_nonempty(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, dict):
        return bool(value)

    if isinstance(value, list):
        return bool(value)

    return True


def nested_missing(
    document: dict[str, Any],
    field: str,
    required: Iterable[str],
) -> list[str]:
    value = document.get(field)

    if not isinstance(value, dict):
        return [
            f"{field}.{child}"
            for child in required
        ]

    return [
        f"{field}.{child}"
        for child in required
        if child not in value
    ]


def runtime_state(
    document: dict[str, Any],
) -> str:
    runtime = document.get("runtime")

    if not isinstance(runtime, dict):
        return "absent"

    value = str(
        runtime.get(
            "implementation",
            "unknown",
        )
    ).strip().lower()

    if value not in IMPLEMENTATION_SCORE:
        return "unknown"

    return value


def runtime_entrypoints(
    document: dict[str, Any],
) -> tuple[str, ...]:
    runtime = document.get("runtime")

    if not isinstance(runtime, dict):
        return ()

    entrypoints = runtime.get(
        "entrypoints"
    )

    if not isinstance(entrypoints, list):
        return ()

    return tuple(
        sorted(
            value
            for value in entrypoints
            if isinstance(value, str)
            and value.strip()
        )
    )


def declared_tests(
    document: dict[str, Any],
) -> tuple[str, ...]:
    validation = document.get(
        "validation"
    )

    if not isinstance(validation, dict):
        return ()

    values: list[str] = []

    for field in (
        "unit_tests",
        "integration_tests",
    ):
        candidates = validation.get(
            field
        )

        if not isinstance(candidates, list):
            continue

        for candidate in candidates:
            if (
                isinstance(candidate, str)
                and candidate.strip()
            ):
                values.append(
                    candidate.strip()
                )

    return tuple(
        sorted(set(values))
    )


def path_exists(
    declared: str,
    definition: Path,
) -> bool:
    candidate = Path(declared)

    if candidate.is_absolute():
        return candidate.is_file()

    root_candidate = (
        ROOT
        / candidate
    )

    local_candidate = (
        definition.parent
        / candidate
    )

    return (
        root_candidate.is_file()
        or local_candidate.is_file()
    )


def scan_forbidden_terms(
    directory: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if not directory.is_dir():
        return findings

    pattern = re.compile(
        rf"\b{re.escape(KINSHIP_TERM)}\b",
        re.IGNORECASE,
    )

    for path in sorted(
        directory.rglob("*")
    ):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in TEXT_SUFFIXES
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
            )

        except (
            OSError,
            UnicodeDecodeError,
        ):
            continue

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            if pattern.search(line):
                findings.append(
                    {
                        "path": (
                            path.relative_to(
                                ROOT
                            ).as_posix()
                        ),
                        "line": line_number,
                        "value": KINSHIP_TERM,
                    }
                )

    return findings


def assess_definition(
    path: Path,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    try:
        document = load_json(path)

    except Exception as exc:
        return {
            "id": (
                f"invalid:{path.parent.name}"
            ),
            "kind": "unknown",
            "path": (
                path.relative_to(
                    ROOT
                ).as_posix()
            ),
            "passed": False,
            "score": 10000,
            "issues": [
                {
                    "severity": "critical",
                    "code": (
                        "definition.invalid_json"
                    ),
                    "field": None,
                    "message": str(exc),
                }
            ],
            "definition_sha256": (
                sha256_path(path)
            ),
        }

    identifier = identity_id(
        document,
        path,
    )

    kind = infer_kind(
        document,
        path,
    )

    for field in REQUIRED_FIELDS:
        if field not in document:
            issues.append(
                {
                    "severity": "high",
                    "code": (
                        "definition.field_missing"
                    ),
                    "field": field,
                    "message": (
                        f"Required field is missing: {field}"
                    ),
                }
            )

        elif not is_nonempty(
            document[field]
        ):
            issues.append(
                {
                    "severity": "medium",
                    "code": (
                        "definition.field_empty"
                    ),
                    "field": field,
                    "message": (
                        f"Required field is empty: {field}"
                    ),
                }
            )

    nested_requirements = {
        "authority": (
            REQUIRED_AUTHORITY_FIELDS
        ),
        "runtime": (
            REQUIRED_RUNTIME_FIELDS
        ),
        "lineage": (
            REQUIRED_LINEAGE_FIELDS
        ),
        "provenance": (
            REQUIRED_PROVENANCE_FIELDS
        ),
        "dependencies": (
            REQUIRED_DEPENDENCY_FIELDS
        ),
        "validation": (
            REQUIRED_VALIDATION_FIELDS
        ),
        "observability": (
            REQUIRED_OBSERVABILITY_FIELDS
        ),
        "security": (
            REQUIRED_SECURITY_FIELDS
        ),
    }

    for field, required in (
        nested_requirements.items()
    ):
        for missing in nested_missing(
            document,
            field,
            required,
        ):
            issues.append(
                {
                    "severity": "medium",
                    "code": (
                        "definition.nested_field_missing"
                    ),
                    "field": missing,
                    "message": (
                        f"Required nested field "
                        f"is missing: {missing}"
                    ),
                }
            )

    state = runtime_state(
        document
    )

    if state != "complete":
        issues.append(
            {
                "severity": (
                    "high"
                    if state
                    in {
                        "absent",
                        "unknown",
                    }
                    else "medium"
                ),
                "code": (
                    "runtime.incomplete"
                ),
                "field": (
                    "runtime.implementation"
                ),
                "message": (
                    f"Runtime implementation "
                    f"is {state}."
                ),
            }
        )

    entrypoints = runtime_entrypoints(
        document
    )

    if not entrypoints:
        issues.append(
            {
                "severity": "high",
                "code": (
                    "runtime.entrypoint_missing"
                ),
                "field": (
                    "runtime.entrypoints"
                ),
                "message": (
                    "No runtime entrypoint is declared."
                ),
            }
        )

    missing_entrypoints = [
        entrypoint
        for entrypoint in entrypoints
        if not path_exists(
            entrypoint,
            path,
        )
    ]

    for entrypoint in missing_entrypoints:
        issues.append(
            {
                "severity": "high",
                "code": (
                    "runtime.entrypoint_missing_file"
                ),
                "field": (
                    "runtime.entrypoints"
                ),
                "message": (
                    f"Declared entrypoint does "
                    f"not exist: {entrypoint}"
                ),
            }
        )

    tests = declared_tests(
        document
    )

    if not tests:
        issues.append(
            {
                "severity": "high",
                "code": (
                    "validation.tests_missing"
                ),
                "field": (
                    "validation.unit_tests"
                ),
                "message": (
                    "No executable unit or "
                    "integration tests are declared."
                ),
            }
        )

    missing_tests = [
        test
        for test in tests
        if not path_exists(
            test,
            path,
        )
    ]

    for test in missing_tests:
        issues.append(
            {
                "severity": "high",
                "code": (
                    "validation.test_missing_file"
                ),
                "field": "validation",
                "message": (
                    f"Declared test does "
                    f"not exist: {test}"
                ),
            }
        )

    forbidden = scan_forbidden_terms(
        path.parent
    )

    for finding in forbidden:
        issues.append(
            {
                "severity": "high",
                "code": (
                    "terminology.forbidden"
                ),
                "field": None,
                "message": (
                    "Forbidden terminology "
                    "exists in identity subtree."
                ),
                "evidence": finding,
            }
        )

    relationships = document.get(
        "relationships"
    )

    if (
        not isinstance(
            relationships,
            list,
        )
        or not relationships
    ):
        issues.append(
            {
                "severity": "medium",
                "code": (
                    "relationships.missing"
                ),
                "field": "relationships",
                "message": (
                    "Identity exposes no "
                    "declared relationships."
                ),
            }
        )

    apertures = document.get(
        "apertures"
    )

    if (
        not isinstance(
            apertures,
            list,
        )
        or not apertures
    ):
        issues.append(
            {
                "severity": "medium",
                "code": (
                    "apertures.missing"
                ),
                "field": "apertures",
                "message": (
                    "Identity exposes no "
                    "future attachment apertures."
                ),
            }
        )

    lineage = document.get(
        "lineage"
    )

    if isinstance(
        lineage,
        dict,
    ):
        parents = lineage.get(
            "parents"
        )

        if (
            kind in {
                "prodigal",
                "quirk",
            }
            and (
                not isinstance(
                    parents,
                    list,
                )
                or not parents
            )
        ):
            issues.append(
                {
                    "severity": "high",
                    "code": (
                        "lineage.parent_missing"
                    ),
                    "field": (
                        "lineage.parents"
                    ),
                    "message": (
                        f"{kind} has no "
                        f"declared parent."
                    ),
                }
            )

    score = IMPLEMENTATION_SCORE[
        state
    ]

    for issue in issues:
        score += SEVERITY_WEIGHT[
            issue["severity"]
        ]

    if (
        identifier in REFERENCE_SUBJECTS
        and not issues
    ):
        score -= 1000

    return {
        "id": identifier,
        "kind": kind,
        "path": (
            path.relative_to(
                ROOT
            ).as_posix()
        ),
        "definition_sha256": (
            sha256_path(path)
        ),
        "runtime_state": state,
        "runtime_entrypoints": (
            list(entrypoints)
        ),
        "declared_tests": list(
            tests
        ),
        "missing_entrypoints": (
            missing_entrypoints
        ),
        "missing_tests": (
            missing_tests
        ),
        "forbidden_term_count": (
            len(forbidden)
        ),
        "issue_count": len(
            issues
        ),
        "score": score,
        "passed": not issues,
        "reference_subject": (
            identifier
            in REFERENCE_SUBJECTS
        ),
        "issues": issues,
    }


def parent_identifier(
    record: dict[str, Any],
) -> str | None:
    path = (
        ROOT
        / record["path"]
    )

    try:
        document = load_json(
            path
        )

    except Exception:
        return None

    lineage = document.get(
        "lineage"
    )

    if isinstance(lineage, dict):
        parents = lineage.get(
            "parents"
        )

        if (
            isinstance(parents, list)
            and parents
            and isinstance(
                parents[0],
                str,
            )
        ):
            return parents[0]

    relationships = document.get(
        "relationships"
    )

    if isinstance(
        relationships,
        list,
    ):
        for relationship in relationships:
            if not isinstance(
                relationship,
                dict,
            ):
                continue

            if relationship.get(
                "type"
            ) in {
                "composition",
                "belongs_to",
                "child_of",
                "attached_to",
            }:
                target = relationship.get(
                    "target"
                )

                if isinstance(
                    target,
                    str,
                ):
                    return target

    return None


def task_for_issue(
    identifier: str,
    issue: dict[str, Any],
    priority: int,
) -> dict[str, Any]:
    code = issue["code"]

    field = issue.get(
        "field"
    )

    action_map = {
        "definition.invalid_json": (
            "Repair the authoritative definition "
            "without discarding recoverable fields."
        ),
        "definition.field_missing": (
            f"Add authoritative field `{field}`."
        ),
        "definition.field_empty": (
            f"Populate authoritative field `{field}`."
        ),
        "definition.nested_field_missing": (
            f"Add nested field `{field}`."
        ),
        "runtime.incomplete": (
            "Implement bounded deterministic runtime "
            "behavior through explicit contracts."
        ),
        "runtime.entrypoint_missing": (
            "Create one canonical executable controller "
            "and one importable runtime entrypoint."
        ),
        "runtime.entrypoint_missing_file": (
            "Restore or replace the missing declared "
            "runtime entrypoint without breaking lineage."
        ),
        "validation.tests_missing": (
            "Add unit, property, integration, security, "
            "recovery, and determinism tests."
        ),
        "validation.test_missing_file": (
            "Restore or replace the missing declared "
            "test and preserve its validation intent."
        ),
        "terminology.forbidden": (
            "Replace forbidden terminology with `kindred` "
            "across authoritative and projected files."
        ),
        "relationships.missing": (
            "Declare typed graph-addressable relationships."
        ),
        "apertures.missing": (
            "Add governed future attachment apertures."
        ),
        "lineage.parent_missing": (
            "Declare authoritative parent lineage."
        ),
    }

    action = action_map.get(
        code,
        issue["message"],
    )

    return {
        "priority": priority,
        "id": (
            f"{identifier}."
            f"{code.replace('.', '_')}"
        ),
        "severity": issue[
            "severity"
        ],
        "code": code,
        "field": field,
        "action": action,
        "acceptance": [
            (
                "Authority, lineage, provenance, "
                "dependencies, and relationships remain exposed."
            ),
            (
                "Existing authoritative primitives "
                "are preserved unless explicitly migrated."
            ),
            (
                "Generated views remain disposable "
                "deterministic projections."
            ),
            (
                "Runtime capability is not fabricated "
                "from absent implementation evidence."
            ),
            (
                "The identity remains recursively "
                "composable and future-attachable."
            ),
        ],
    }


def build_queue(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in records
        if not record.get(
            "passed",
            False,
        )
    ]

    ordered = sorted(
        candidates,
        key=lambda record: (
            (
                1
                if record.get(
                    "reference_subject",
                    False,
                )
                else 0
            ),
            -record["score"],
            KIND_PRIORITY.get(
                record["kind"],
                99,
            ),
            record["id"],
        ),
    )

    queue: list[
        dict[str, Any]
    ] = []

    for queue_index, record in enumerate(
        ordered,
        start=1,
    ):
        tasks = [
            task_for_issue(
                record["id"],
                issue,
                priority,
            )
            for priority, issue in enumerate(
                sorted(
                    record["issues"],
                    key=lambda issue: (
                        -SEVERITY_WEIGHT[
                            issue["severity"]
                        ],
                        issue["code"],
                        str(
                            issue.get(
                                "field"
                            )
                        ),
                    ),
                ),
                start=1,
            )
        ]

        queue.append(
            {
                "queue_position": (
                    queue_index
                ),
                "id": record["id"],
                "kind": record["kind"],
                "path": record["path"],
                "parent": (
                    parent_identifier(
                        record
                    )
                ),
                "score": record["score"],
                "runtime_state": (
                    record["runtime_state"]
                ),
                "issue_count": (
                    record["issue_count"]
                ),
                "reference_subject": (
                    record.get(
                        "reference_subject",
                        False,
                    )
                ),
                "tasks": tasks,
            }
        )

    return queue


def build_statistics(
    records: list[dict[str, Any]],
    queue: list[dict[str, Any]],
) -> dict[str, Any]:
    kind_counts = Counter(
        record["kind"]
        for record in records
    )

    runtime_counts = Counter(
        record.get(
            "runtime_state",
            "unknown",
        )
        for record in records
    )

    issue_counts = Counter()

    for record in records:
        for issue in record.get(
            "issues",
            []
        ):
            issue_counts[
                issue["code"]
            ] += 1

    return {
        "definition_count": len(
            records
        ),
        "passed_count": sum(
            record.get(
                "passed",
                False,
            )
            for record in records
        ),
        "failed_count": sum(
            not record.get(
                "passed",
                False,
            )
            for record in records
        ),
        "reference_count": sum(
            record.get(
                "reference_subject",
                False,
            )
            for record in records
        ),
        "queue_count": len(
            queue
        ),
        "kind_counts": dict(
            sorted(
                kind_counts.items()
            )
        ),
        "runtime_counts": dict(
            sorted(
                runtime_counts.items()
            )
        ),
        "issue_counts": dict(
            sorted(
                issue_counts.items()
            )
        ),
        "total_issue_count": sum(
            record.get(
                "issue_count",
                0,
            )
            for record in records
        ),
    }


def markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Identity Quality Promotion Queue",
        "",
        (
            f"- Generated: "
            f"`{result['generated_at']}`"
        ),
        (
            f"- Digest: "
            f"`{result['digest']}`"
        ),
        (
            f"- Definitions: "
            f"**{result['statistics']['definition_count']}**"
        ),
        (
            f"- Passed: "
            f"**{result['statistics']['passed_count']}**"
        ),
        (
            f"- Failed: "
            f"**{result['statistics']['failed_count']}**"
        ),
        (
            f"- Promotion candidates: "
            f"**{result['statistics']['queue_count']}**"
        ),
        "",
        "## Priority Queue",
        "",
    ]

    for item in result["queue"]:
        lines.extend(
            [
                (
                    f"### {item['queue_position']}. "
                    f"{item['id']}"
                ),
                "",
                f"- Kind: `{item['kind']}`",
                f"- Parent: `{item['parent']}`",
                f"- Path: `{item['path']}`",
                f"- Score: **{item['score']}**",
                (
                    f"- Runtime: "
                    f"`{item['runtime_state']}`"
                ),
                (
                    f"- Reference subject: "
                    f"`{item['reference_subject']}`"
                ),
                (
                    f"- Issues: "
                    f"**{item['issue_count']}**"
                ),
                "",
                "#### Tasks",
                "",
            ]
        )

        for task in item["tasks"]:
            lines.append(
                (
                    f"{task['priority']}. "
                    f"`{task['code']}` — "
                    f"{task['action']}"
                )
            )

        lines.append("")

    return "\n".join(
        lines
    )


def task_markdown(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Savant Identity Promotion Tasks",
        "",
        (
            f"- Generated: "
            f"`{result['generated_at']}`"
        ),
        (
            f"- Queue digest: "
            f"`{result['digest']}`"
        ),
        "",
        "## Governing Method",
        "",
        (
            "Nocturne is the current reference implementation. "
            "Every promoted identity must reach equivalent "
            "structural, contractual, deterministic, security, "
            "observability, validation, lineage, provenance, "
            "relationship, and attachment quality without "
            "blindly copying Nocturne-specific behavior."
        ),
        "",
        "## Promotion Order",
        "",
    ]

    for item in result["queue"]:
        lines.extend(
            [
                (
                    f"### {item['queue_position']}. "
                    f"`{item['id']}`"
                ),
                "",
                (
                    f"Definition: "
                    f"`{item['path']}`"
                ),
                "",
            ]
        )

        for task in item["tasks"]:
            lines.extend(
                [
                    (
                        f"- [ ] "
                        f"**{task['code']}** — "
                        f"{task['action']}"
                    ),
                ]
            )

        lines.extend(
            [
                (
                    "- [ ] Create or extend versioned contracts."
                ),
                (
                    "- [ ] Create bounded independently useful runtime behavior."
                ),
                (
                    "- [ ] Create canonical controller."
                ),
                (
                    "- [ ] Add deterministic example request and result."
                ),
                (
                    "- [ ] Add unit, property, security, integration, and recovery tests."
                ),
                (
                    "- [ ] Attach runtime evidence to authoritative definition."
                ),
                (
                    "- [ ] Add parent attachment without authority transfer."
                ),
                (
                    "- [ ] Add reference-quality verification controller."
                ),
                (
                    "- [ ] Produce deterministic attestation."
                ),
                "",
            ]
        )

    return "\n".join(
        lines
    )


def build() -> dict[str, Any]:
    paths = definition_paths()

    records = [
        assess_definition(path)
        for path in paths
    ]

    queue = build_queue(
        records
    )

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-queue/1.1.0"
        ),
        "operation": (
            "build_identity_promotion_queue"
        ),
        "generated_at": utc_now(),
        "root": str(ROOT),
        "identity_root": str(
            IDENTITY_ROOT
        ),
        "reference_profile": {
            "path": (
                NOCTURNE_PROFILE
                .relative_to(
                    ROOT
                )
                .as_posix()
            ),
            "exists": (
                NOCTURNE_PROFILE
                .is_file()
            ),
            "sha256": (
                sha256_path(
                    NOCTURNE_PROFILE
                )
                if NOCTURNE_PROFILE
                .is_file()
                else None
            ),
        },
        "identity_schema": {
            "path": (
                IDENTITY_SCHEMA
                .relative_to(
                    ROOT
                )
                .as_posix()
            ),
            "exists": (
                IDENTITY_SCHEMA
                .is_file()
            ),
            "sha256": (
                sha256_path(
                    IDENTITY_SCHEMA
                )
                if IDENTITY_SCHEMA
                .is_file()
                else None
            ),
        },
        "statistics": build_statistics(
            records,
            queue,
        ),
        "records": records,
        "queue": queue,
    }

    result["digest"] = digest(
        {
            key: value
            for key, value in result.items()
            if key != "generated_at"
        }
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic priority queue "
            "for promoting all Savant exiles, "
            "prodigals, and quirks to the "
            "Nocturne reference-quality baseline."
        )
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPORT_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    if not IDENTITY_ROOT.is_dir():
        print(
            f"ERROR: identity root missing: "
            f"{IDENTITY_ROOT}",
            file=sys.stderr,
        )

        return 2

    result = build()

    output_root = (
        arguments.output_root
        .resolve()
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / (
            f"{run_id}__"
            "identity-promotion-queue.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "identity-promotion-queue.md"
        )
    )

    task_path = (
        output_root
        / (
            f"{run_id}__"
            "identity-promotion-tasks.md"
        )
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    latest_tasks = (
        output_root
        / "tasks.md"
    )

    write_json(
        json_path,
        result,
    )

    write_json(
        latest_json,
        result,
    )

    rendered = markdown(
        result
    )

    tasks = task_markdown(
        result
    )

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    write_text(
        task_path,
        tasks,
    )

    write_text(
        latest_tasks,
        tasks,
    )

    manifest = {
        "generated_at": (
            result["generated_at"]
        ),
        "queue_digest": (
            result["digest"]
        ),
        "statistics": (
            result["statistics"]
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
            task_path.name: (
                sha256_path(
                    task_path
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
            latest_tasks.name: (
                sha256_path(
                    latest_tasks
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / (
            f"{run_id}__manifest.json"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    passed = (
        result["statistics"][
            "definition_count"
        ] > 0
        and result[
            "reference_profile"
        ]["exists"]
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_identity_promotion_queue"
                ),
                "passed": passed,
                "digest": (
                    result["digest"]
                ),
                "statistics": (
                    result["statistics"]
                ),
                "next": (
                    result["queue"][0]
                    if result["queue"]
                    else None
                ),
                "reports": {
                    "json": str(
                        json_path
                    ),
                    "markdown": str(
                        markdown_path
                    ),
                    "tasks": str(
                        task_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "latest_tasks": str(
                        latest_tasks
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if arguments.strict and not passed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
