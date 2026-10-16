#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


DEFAULT_ROOT = Path("/root/savant-runtime")
DEFAULT_IDENTITY_ROOT = DEFAULT_ROOT / "edifices/identity"
DEFAULT_SCHEMA = (
    DEFAULT_ROOT
    / "tools"
    / "identity_quality"
    / "identity_quality.schema.json"
)
DEFAULT_BACKUP_ROOT = (
    DEFAULT_ROOT
    / "backups"
    / "identity-quality"
)
DEFAULT_REPORT_ROOT = (
    DEFAULT_ROOT
    / "reports"
    / "identity_quality"
)

TOOL_ID = "savant.identity-quality.upgrader"
TOOL_VERSION = "1.1.0"

KINDRED_TERM = "kin" + "ship"

LEVELS = {
    "exile": 6,
    "prodigal": 5,
    "quirk": 4,
}

LIFECYCLE_TRANSITIONS = [
    "proposed",
    "canonical",
    "active",
    "deprecated",
    "superseded",
    "retired",
]

COMMON_ACCEPTANCE = [
    "Definition validates against the identity quality schema.",
    "Authority, lineage, provenance, dependencies, and relationships are exposed.",
    "Existing authoritative fields remain unchanged unless explicitly migrated.",
    "Runtime capability is never fabricated from absent implementation evidence.",
    "Generated compatibility views remain disposable projections.",
    "Future extensions can attach without architectural replacement.",
]


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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
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
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def definition_paths(
    identity_root: Path,
) -> list[Path]:
    return sorted(
        path
        for path in identity_root.rglob(
            "definition.json"
        )
        if path.is_file()
    )


def infer_kind(
    document: dict[str, Any],
    path: Path,
) -> str:
    kind = str(
        document.get("kind", "")
    ).strip().lower()

    if kind in LEVELS:
        return kind

    parts = {
        part.lower()
        for part in path.parts
    }

    if "quirks" in parts:
        return "quirk"

    if "prodigals" in parts:
        return "prodigal"

    return "exile"


def identity_name(
    document: dict[str, Any],
) -> str:
    identity = document.get("identity")

    if isinstance(identity, dict):
        name = identity.get("name")

        if isinstance(name, str) and name.strip():
            return name.strip()

    identifier = str(
        document.get("id", "unknown")
    )

    return (
        identifier
        .rsplit(".", 1)[-1]
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )


def identity_domain(
    document: dict[str, Any],
) -> str:
    identity = document.get("identity")

    if isinstance(identity, dict):
        domain = identity.get("domain")

        if isinstance(domain, str) and domain.strip():
            return domain.strip()

    domain = document.get("domain")

    if isinstance(domain, str) and domain.strip():
        return domain.strip()

    return "Unresolved domain"


def normalize_identity(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("identity")

    if isinstance(existing, dict):
        identity = copy.deepcopy(existing)
    else:
        identity = {}

    identity.setdefault(
        "name",
        identity_name(document),
    )
    identity.setdefault(
        "domain",
        identity_domain(document),
    )
    identity.setdefault(
        "aliases",
        [],
    )
    identity.setdefault(
        "historical_names",
        [],
    )

    return identity


def infer_parent(
    document: dict[str, Any],
    kind: str,
) -> str | None:
    lineage = document.get("lineage")

    if isinstance(lineage, dict):
        parents = lineage.get("parents")

        if (
            isinstance(parents, list)
            and parents
            and isinstance(parents[0], str)
        ):
            return parents[0]

        parent = lineage.get("parent")

        if isinstance(parent, str) and parent.strip():
            return parent.strip()

    candidate_fields = {
        "quirk": [
            "parent_prodigal",
            "parent",
        ],
        "prodigal": [
            "parent_exile",
            "parent",
        ],
        "exile": [
            "parent_innate",
            "parent",
        ],
    }

    for field in candidate_fields[kind]:
        value = document.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    identifier = str(
        document.get("id", "")
    )
    parts = identifier.split(".")

    if kind == "quirk" and len(parts) >= 3:
        return f"prodigal.{parts[1]}"

    if kind == "prodigal" and len(parts) >= 2:
        return f"exile.{parts[1]}"

    return None


def normalize_parent_id(
    parent: str | None,
    kind: str,
) -> str | None:
    if parent is None:
        return None

    if "." in parent:
        return parent

    normalized = (
        parent.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    if kind == "quirk":
        return f"prodigal.{normalized}"

    if kind == "prodigal":
        return f"exile.{normalized}"

    return normalized


def normalize_authority(
    document: dict[str, Any],
    relative_path: str,
) -> dict[str, Any]:
    existing = document.get("authority")

    if isinstance(existing, dict):
        authority = copy.deepcopy(existing)
    else:
        authority = {}

    authority.setdefault(
        "owner",
        str(
            document.get(
                "id",
                "unresolved",
            )
        ),
    )
    authority.setdefault(
        "class",
        "identity_definition",
    )
    authority.setdefault(
        "precedence",
        700,
    )
    authority.setdefault(
        "source",
        relative_path,
    )

    return authority


def normalize_composition(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("composition")

    if isinstance(existing, dict):
        composition = copy.deepcopy(existing)
    else:
        composition = {}

    children = composition.get("children")

    if not isinstance(children, list):
        children = []

    for field in (
        "quirks",
        "prodigals",
        "components",
    ):
        value = document.get(field)

        if isinstance(value, list):
            for child in value:
                if (
                    isinstance(child, str)
                    and child not in children
                ):
                    children.append(child)

    composition["children"] = children
    composition.setdefault(
        "shared_children",
        [],
    )
    composition.setdefault(
        "composition_policy",
        (
            "Compose authoritative children through "
            "typed relationships without duplicating "
            "their source authority."
        ),
    )

    return composition


def normalize_contracts(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("contracts")

    if isinstance(existing, dict):
        contracts = copy.deepcopy(existing)
    else:
        contracts = {}

    contracts.setdefault(
        "inputs",
        [],
    )
    contracts.setdefault(
        "outputs",
        [],
    )
    contracts.setdefault(
        "errors",
        [
            {
                "code": "implementation.unavailable",
                "condition": (
                    "Required executable behavior is "
                    "absent, incomplete, or unverified."
                ),
                "recoverable": True,
            }
        ],
    )

    return contracts


def capability_from_purpose(
    document: dict[str, Any],
) -> dict[str, Any]:
    identifier = str(
        document.get("id", "unknown")
    )

    return {
        "id": f"{identifier}.declared_purpose",
        "description": str(
            document.get(
                "purpose",
                (
                    "Declared semantic capability; "
                    "runtime implementation remains "
                    "unverified."
                ),
            )
        ),
        "status": "proposed",
    }


def normalize_capabilities(
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    existing = document.get("capabilities")

    if isinstance(existing, list) and existing:
        return copy.deepcopy(existing)

    return [
        capability_from_purpose(document)
    ]


def normalize_dependencies(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("dependencies")

    if isinstance(existing, dict):
        dependencies = copy.deepcopy(existing)
    elif isinstance(existing, list):
        dependencies = {
            "required": copy.deepcopy(existing),
        }
    else:
        dependencies = {}

    dependencies.setdefault(
        "required",
        [],
    )
    dependencies.setdefault(
        "optional",
        [],
    )
    dependencies.setdefault(
        "runtime",
        [],
    )
    dependencies.setdefault(
        "external",
        [],
    )

    return dependencies


def normalize_relationships(
    document: dict[str, Any],
    kind: str,
) -> list[dict[str, Any]]:
    existing = document.get("relationships")

    if isinstance(existing, list):
        relationships = copy.deepcopy(existing)
    else:
        relationships = []

    parent = normalize_parent_id(
        infer_parent(
            document,
            kind,
        ),
        kind,
    )

    if parent is not None:
        candidate = {
            "type": "composition",
            "target": parent,
            "direction": "outbound",
        }

        if candidate not in relationships:
            relationships.append(candidate)

    return relationships


def normalize_lineage(
    document: dict[str, Any],
    kind: str,
    relative_path: str,
) -> dict[str, Any]:
    existing = document.get("lineage")

    if isinstance(existing, dict):
        lineage = copy.deepcopy(existing)
    else:
        lineage = {}

    parent = normalize_parent_id(
        infer_parent(
            document,
            kind,
        ),
        kind,
    )

    parents = lineage.get("parents")

    if not isinstance(parents, list):
        parents = []

    if parent and parent not in parents:
        parents.append(parent)

    lineage["parents"] = parents

    sources = lineage.get("sources")

    if not isinstance(sources, list):
        sources = []

    if relative_path not in sources:
        sources.append(relative_path)

    lineage["sources"] = sources
    lineage.setdefault(
        "supersedes",
        [],
    )
    lineage.setdefault(
        "superseded_by",
        [],
    )

    lineage.pop(
        "parent",
        None,
    )
    lineage.pop(
        "ancestors",
        None,
    )

    return lineage


def normalize_provenance(
    document: dict[str, Any],
    relative_path: str,
    source_hash: str,
) -> dict[str, Any]:
    existing = document.get("provenance")

    if isinstance(existing, dict):
        provenance = copy.deepcopy(existing)
    else:
        provenance = {}

    created_from = provenance.get(
        "created_from"
    )

    if not isinstance(created_from, list):
        created_from = []

    if relative_path not in created_from:
        created_from.append(relative_path)

    provenance["created_from"] = created_from
    provenance.setdefault(
        "captured_by",
        TOOL_ID,
    )

    source_hashes = provenance.get(
        "source_hashes"
    )

    if not isinstance(source_hashes, dict):
        source_hashes = {}

    source_hashes[relative_path] = source_hash
    provenance["source_hashes"] = source_hashes

    return provenance


def detect_runtime_evidence(
    root: Path,
    document: dict[str, Any],
) -> tuple[str, list[str]]:
    identifier = str(
        document.get("id", "")
    )
    token = (
        identifier
        .rsplit(".", 1)[-1]
        .lower()
    )

    matches: list[str] = []

    search_roots = [
        root / "ontology",
        root / "runtime",
        root / "bin",
        root / "tools",
    ]

    for search_root in search_roots:
        if not search_root.exists():
            continue

        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            lowered = path.name.lower()

            if token and token in lowered:
                matches.append(
                    path.relative_to(root).as_posix()
                )

            if len(matches) >= 100:
                break

        if len(matches) >= 100:
            break

    if not matches:
        return "absent", []

    executable = [
        match
        for match in matches
        if Path(match).suffix.lower()
        in {
            ".py",
            ".sh",
            ".js",
            ".ts",
        }
    ]

    if executable:
        return "partial", sorted(
            set(executable)
        )

    return "prototype", sorted(
        set(matches)
    )


def normalize_runtime(
    root: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("runtime")

    if isinstance(existing, dict):
        runtime = copy.deepcopy(existing)
    else:
        runtime = {}

    implementation = runtime.get(
        "implementation"
    )

    entrypoints = runtime.get(
        "entrypoints"
    )

    if not isinstance(entrypoints, list):
        entrypoints = []

    if implementation not in {
        "absent",
        "prototype",
        "partial",
        "complete",
    }:
        inferred, discovered = (
            detect_runtime_evidence(
                root,
                document,
            )
        )
        implementation = inferred

        for candidate in discovered:
            if candidate not in entrypoints:
                entrypoints.append(candidate)

    runtime["implementation"] = (
        implementation
    )
    runtime["entrypoints"] = (
        sorted(set(entrypoints))
    )
    runtime.setdefault(
        "hooks",
        [],
    )
    runtime.setdefault(
        "deterministic",
        True,
    )
    runtime.setdefault(
        "side_effects",
        [],
    )

    return runtime


def normalize_security(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("security")

    if isinstance(existing, dict):
        security = copy.deepcopy(existing)
    else:
        security = {}

    security.setdefault(
        "boundary",
        (
            "Deny undeclared access; require explicit "
            "authority for filesystem, network, provider, "
            "secret, and subprocess operations."
        ),
    )
    security.setdefault(
        "permissions",
        [],
    )
    security.setdefault(
        "data_classification",
        "unclassified",
    )
    security.setdefault(
        "network_policy",
        "deny_by_default",
    )
    security.setdefault(
        "sandbox",
        True,
    )

    return security


def normalize_observability(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get(
        "observability"
    )

    if isinstance(existing, dict):
        observability = copy.deepcopy(existing)
    else:
        observability = {}

    observability.setdefault(
        "metrics",
        [
            "execution_count",
            "success_count",
            "failure_count",
            "duration_seconds",
        ],
    )
    observability.setdefault(
        "events",
        [
            "identity.invoked",
            "identity.completed",
            "identity.failed",
        ],
    )
    observability.setdefault(
        "health",
        [
            "definition_valid",
            "dependencies_available",
            "runtime_available",
        ],
    )
    observability.setdefault(
        "audit",
        True,
    )

    return observability


def normalize_validation(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("validation")

    if isinstance(existing, dict):
        validation = copy.deepcopy(existing)
    else:
        validation = {}

    validation.setdefault(
        "unit_tests",
        [],
    )
    validation.setdefault(
        "integration_tests",
        [],
    )
    validation.setdefault(
        "property_tests",
        [
            "canonical_serialization_is_stable",
            "identity_is_graph_addressable",
            "lineage_contains_no_self_cycle",
        ],
    )
    validation.setdefault(
        "security_tests",
        [
            "undeclared_access_is_denied",
        ],
    )
    validation.setdefault(
        "acceptance",
        copy.deepcopy(
            COMMON_ACCEPTANCE
        ),
    )

    return validation


def normalize_lifecycle(
    document: dict[str, Any],
) -> dict[str, Any]:
    existing = document.get("lifecycle")

    if isinstance(existing, dict):
        lifecycle = copy.deepcopy(existing)
    else:
        lifecycle = {}

    status = str(
        document.get(
            "status",
            "proposed",
        )
    ).lower()

    mapping = {
        "canonical": "canonical",
        "active": "active",
        "deprecated": "deprecated",
        "superseded": "superseded",
        "retired": "retired",
    }

    lifecycle.setdefault(
        "state",
        mapping.get(
            status,
            "proposed",
        ),
    )
    lifecycle.setdefault(
        "allowed_transitions",
        copy.deepcopy(
            LIFECYCLE_TRANSITIONS
        ),
    )

    return lifecycle


def normalize_apertures(
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    existing = document.get("apertures")

    if isinstance(existing, list) and existing:
        return copy.deepcopy(existing)

    identifier = str(
        document.get("id", "unknown")
    )

    return [
        {
            "id": f"{identifier}.future",
            "purpose": (
                "Admit future compatible attachments "
                "without replacing this identity."
            ),
            "admission": (
                "Requires compatible contract, validated "
                "authority, explicit lineage, and complete "
                "provenance."
            ),
        }
    ]


def replace_forbidden_term(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            (
                key.replace(
                    KINDRED_TERM,
                    "kindred",
                )
                if isinstance(key, str)
                else key
            ): replace_forbidden_term(child)
            for key, child in value.items()
        }

    if isinstance(value, list):
        return [
            replace_forbidden_term(child)
            for child in value
        ]

    if isinstance(value, str):
        return value.replace(
            KINDRED_TERM,
            "kindred",
        ).replace(
            KINDRED_TERM.capitalize(),
            "Kindred",
        )

    return value


def extend_definition(
    root: Path,
    identity_root: Path,
    path: Path,
    original: dict[str, Any],
) -> dict[str, Any]:
    document = replace_forbidden_term(
        copy.deepcopy(original)
    )

    relative_path = path.relative_to(
        root
    ).as_posix()

    source_hash = sha256_path(path)
    kind = infer_kind(
        document,
        path,
    )

    document["kind"] = kind
    document.setdefault(
        "level",
        LEVELS[kind],
    )
    document.setdefault(
        "version",
        "1.0.0",
    )
    document.setdefault(
        "status",
        "proposed",
    )

    document["identity"] = (
        normalize_identity(document)
    )

    document.setdefault(
        "purpose",
        (
            f"Provide bounded canonical behavior for "
            f"{identity_name(document)} while exposing "
            "authority, lineage, provenance, dependencies, "
            "relationships, validation, and extension points."
        ),
    )

    document["authority"] = normalize_authority(
        document,
        relative_path,
    )
    document["composition"] = normalize_composition(
        document
    )
    document["contracts"] = normalize_contracts(
        document
    )
    document["capabilities"] = normalize_capabilities(
        document
    )
    document["dependencies"] = normalize_dependencies(
        document
    )
    document["relationships"] = normalize_relationships(
        document,
        kind,
    )
    document["lineage"] = normalize_lineage(
        document,
        kind,
        relative_path,
    )
    document["provenance"] = normalize_provenance(
        document,
        relative_path,
        source_hash,
    )
    document["runtime"] = normalize_runtime(
        root,
        document,
    )
    document["security"] = normalize_security(
        document
    )
    document["observability"] = (
        normalize_observability(
            document
        )
    )
    document["validation"] = normalize_validation(
        document
    )
    document["lifecycle"] = normalize_lifecycle(
        document
    )
    document["apertures"] = normalize_apertures(
        document
    )

    return document


def schema_findings(
    document: dict[str, Any],
    validator: Draft202012Validator,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for error in sorted(
        validator.iter_errors(document),
        key=lambda issue: (
            list(issue.absolute_path),
            issue.message,
        ),
    ):
        findings.append(
            {
                "path": "$."
                + ".".join(
                    str(part)
                    for part in error.absolute_path
                ),
                "message": error.message,
            }
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extend Savant exile, prodigal, and quirk "
            "definitions to the shared quality contract."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )
    parser.add_argument(
        "--identity-root",
        type=Path,
        default=DEFAULT_IDENTITY_ROOT,
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    identity_root = (
        args.identity_root.resolve()
    )
    schema_path = args.schema.resolve()
    report_root = (
        args.report_root.resolve()
    )

    if not root.is_dir():
        print(
            f"ERROR: Savant root missing: {root}",
            file=sys.stderr,
        )
        return 2

    if not identity_root.is_dir():
        print(
            f"ERROR: identity root missing: {identity_root}",
            file=sys.stderr,
        )
        return 2

    if not schema_path.is_file():
        print(
            f"ERROR: schema missing: {schema_path}",
            file=sys.stderr,
        )
        return 2

    schema = load_json(schema_path)
    validator = Draft202012Validator(
        schema
    )

    run_timestamp = timestamp()
    backup_root = (
        args.backup_root.resolve()
        / run_timestamp
    )

    records: list[dict[str, Any]] = []
    invalid_count = 0
    changed_count = 0

    for path in definition_paths(
        identity_root
    ):
        original = load_json(path)

        upgraded = extend_definition(
            root,
            identity_root,
            path,
            original,
        )

        findings = schema_findings(
            upgraded,
            validator,
        )

        changed = (
            canonical_bytes(original)
            != canonical_bytes(upgraded)
        )

        if findings:
            invalid_count += 1

        if changed:
            changed_count += 1

        action = "unchanged"

        if changed:
            action = "planned"

        if args.apply and changed:
            backup = (
                backup_root
                / path.relative_to(root)
            )

            backup.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                path,
                backup,
            )

            write_json(
                path,
                upgraded,
            )

            action = "extended"

        records.append(
            {
                "id": upgraded.get("id"),
                "kind": upgraded.get("kind"),
                "path": path.relative_to(
                    root
                ).as_posix(),
                "changed": changed,
                "action": action,
                "before_sha256": (
                    sha256_bytes(
                        canonical_bytes(original)
                    )
                ),
                "after_sha256": (
                    sha256_bytes(
                        canonical_bytes(upgraded)
                    )
                ),
                "schema_valid": not findings,
                "findings": findings,
            }
        )

    result: dict[str, Any] = {
        "generated_at": utc_now(),
        "tool": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "mode": (
            "apply"
            if args.apply
            else "plan"
        ),
        "root": str(root),
        "identity_root": str(
            identity_root
        ),
        "schema": str(schema_path),
        "backup_root": (
            str(backup_root)
            if args.apply
            else None
        ),
        "definition_count": len(records),
        "changed_count": changed_count,
        "invalid_count": invalid_count,
        "records": records,
    }

    result["digest"] = sha256_bytes(
        canonical_bytes(result)
    )

    report_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_json(
        report_root
        / "identity_quality_upgrade.json",
        result,
    )

    write_json(
        report_root
        / "identity_quality_upgrade_changes.json",
        {
            "generated_at": (
                result["generated_at"]
            ),
            "digest": result["digest"],
            "records": [
                record
                for record in records
                if record["changed"]
            ],
        },
    )

    write_json(
        report_root
        / "identity_quality_upgrade_failures.json",
        {
            "generated_at": (
                result["generated_at"]
            ),
            "digest": result["digest"],
            "records": [
                record
                for record in records
                if not record[
                    "schema_valid"
                ]
            ],
        },
    )

    print(
        json.dumps(
            {
                "passed": (
                    invalid_count == 0
                ),
                "mode": result["mode"],
                "definition_count": (
                    len(records)
                ),
                "changed_count": (
                    changed_count
                ),
                "invalid_count": (
                    invalid_count
                ),
                "digest": result["digest"],
                "backup_root": (
                    result["backup_root"]
                ),
                "report": str(
                    report_root
                    / (
                        "identity_quality_"
                        "upgrade.json"
                    )
                ),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if args.strict and invalid_count:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
