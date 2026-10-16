#!/usr/bin/env python3
"""
Savant nine-dimensional archive migration, scaffold, refresh, and verification.

Canonical implementation:
    /root/savant-runtime/vault/dimensions/sys/scaffold.py

Canonical data root:
    /root/savant-runtime/vault/dimensions

This implementation:

- keeps all nine dimensions structurally equal
- treats sys as the subsystem implementation boundary
- migrates legacy top-level canon and context trees safely
- refuses ambiguous or non-identical competing trees
- backs up every moved, refreshed, or removed path
- creates one JSON dimensional record for every supported canon object
- preserves manually authored dimensional records
- binds generated records to exact canon SHA-256 digests
- verifies schema, coverage, paths, digests, and lexical migration
- never manufactures authority
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Iterable, Sequence


SAVANT_ROOT: Final[Path] = Path("/root/savant-runtime")
VAULT_ROOT: Final[Path] = SAVANT_ROOT / "vault"
DIMENSIONS_ROOT: Final[Path] = VAULT_ROOT / "dimensions"
SYS_ROOT: Final[Path] = DIMENSIONS_ROOT / "sys"
REGISTRY_PATH: Final[Path] = SYS_ROOT / "dimension_registry.json"
SCHEMA_PATH: Final[Path] = SYS_ROOT / "schemas" / "dimensional-record.schema.json"

CANON_ROOT: Final[Path] = DIMENSIONS_ROOT / "canon"
REPORT_ROOT: Final[Path] = SYS_ROOT / "reports"
BACKUP_ROOT: Final[Path] = VAULT_ROOT / "backups" / "dimensions"

LEGACY_DIMENSIONS_ROOT: Final[Path] = SAVANT_ROOT / "dimensions"

SUPPORTED_SUFFIXES: Final[set[str]] = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}

EXCLUDED_NAMES: Final[set[str]] = {
    ".DS_Store",
    "DIMENSION.md",
    "DIMENSIONS.md",
    "DIMENSION.json",
    "DIMENSIONS.json",
}

EXCLUDED_SUFFIXES: Final[set[str]] = {
    ".bak",
    ".orig",
    ".rej",
    ".save",
    ".swp",
    ".tmp",
}

KINSHIP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"kinship",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class CanonObject:
    relative_path: str
    absolute_path: str
    sha256: str
    size: int
    modified_ns: int


@dataclass(frozen=True)
class Action:
    kind: str
    source: str | None
    destination: str | None
    dimension: str | None
    canon_relative_path: str | None
    reason: str


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp_slug() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_json_write(path: Path, value: Any) -> None:
    atomic_write(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def ensure_directory(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise RuntimeError(f"Expected directory: {path}")

    path.mkdir(parents=True, exist_ok=True)


def registry() -> dict[str, Any]:
    value = load_json(REGISTRY_PATH)

    dimensions = value.get("dimensions")

    if not isinstance(dimensions, list) or len(dimensions) != 9:
        raise RuntimeError("Dimension registry must define exactly nine dimensions.")

    names = [item["name"] for item in dimensions]
    keys = [item["key"] for item in dimensions]

    if len(set(names)) != 9 or len(set(keys)) != 9:
        raise RuntimeError("Dimension names and keys must be globally unique.")

    if keys[0] != "canon":
        raise RuntimeError("Canon must remain the first registered dimension.")

    return value


def generated_dimensions(registry_value: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dimension
        for dimension in registry_value["dimensions"]
        if dimension["generated"] is True
    ]


def inventory(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}

    if not root.exists():
        return result

    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"Cannot inventory non-directory tree: {root}")

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()

        if path.is_symlink():
            result[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_file():
            result[relative] = f"sha256:{sha256_path(path)}"

    return result


def identical_trees(first: Path, second: Path) -> bool:
    return inventory(first) == inventory(second)


def backup_path(path: Path, stamp: str) -> Path:
    if not path.exists() and not path.is_symlink():
        raise RuntimeError(f"Cannot back up missing path: {path}")

    relative = path.relative_to(SAVANT_ROOT)
    destination = BACKUP_ROOT / stamp / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    if path.is_symlink():
        destination.symlink_to(os.readlink(path))
    elif path.is_dir():
        shutil.copytree(path, destination, symlinks=True)
    else:
        shutil.copy2(path, destination)

    return destination


def move_path(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"Migration destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.replace(source, destination)
    except OSError:
        shutil.move(str(source), str(destination))


def record_path(dimension_key: str, canon_object: CanonObject) -> Path:
    relative = Path(canon_object.relative_path)
    return DIMENSIONS_ROOT / dimension_key / relative.with_name(
        relative.name + ".dimension.json"
    )


def discover_canon(root: Path = CANON_ROOT) -> list[CanonObject]:
    if not root.is_dir():
        raise RuntimeError(f"Canon dimension is missing: {root}")

    objects: list[CanonObject] = []

    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue

        if path.name in EXCLUDED_NAMES:
            continue

        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue

        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        relative = path.relative_to(root)
        stat = path.stat()

        objects.append(
            CanonObject(
                relative_path=relative.as_posix(),
                absolute_path=str(path),
                sha256=sha256_path(path),
                size=stat.st_size,
                modified_ns=stat.st_mtime_ns,
            )
        )

    if not objects:
        raise RuntimeError(f"No supported canon objects found beneath {root}")

    return objects


def find_pre_migration_canon() -> Path | None:
    candidates = [
        CANON_ROOT,
        SAVANT_ROOT / "canon",
        LEGACY_DIMENSIONS_ROOT / "canon",
    ]
    existing = [
        candidate
        for candidate in candidates
        if candidate.is_dir() and not candidate.is_symlink()
    ]

    if not existing:
        return None

    if len(existing) == 1:
        return existing[0]

    first = existing[0]

    if all(identical_trees(first, candidate) for candidate in existing[1:]):
        return first

    raise RuntimeError(
        "Multiple non-identical canon trees exist: "
        + ", ".join(str(candidate) for candidate in existing)
    )


def migration_plan(registry_value: dict[str, Any]) -> list[Action]:
    actions: list[Action] = []

    if LEGACY_DIMENSIONS_ROOT.exists():
        if DIMENSIONS_ROOT.exists():
            if not identical_trees(LEGACY_DIMENSIONS_ROOT, DIMENSIONS_ROOT):
                raise RuntimeError(
                    "Legacy and vault dimension roots both exist with different contents."
                )

            actions.append(
                Action(
                    kind="remove-identical-legacy-tree",
                    source=str(LEGACY_DIMENSIONS_ROOT),
                    destination=str(DIMENSIONS_ROOT),
                    dimension=None,
                    canon_relative_path=None,
                    reason="Legacy dimensions tree duplicates the vault dimensions tree.",
                )
            )
        else:
            actions.append(
                Action(
                    kind="move-tree",
                    source=str(LEGACY_DIMENSIONS_ROOT),
                    destination=str(DIMENSIONS_ROOT),
                    dimension=None,
                    canon_relative_path=None,
                    reason="Migrate the former dimension root into Vault.",
                )
            )

    for dimension in registry_value["dimensions"]:
        key = dimension["key"]
        legacy = SAVANT_ROOT / key
        canonical = DIMENSIONS_ROOT / key

        if not legacy.exists() and not legacy.is_symlink():
            continue

        if legacy.is_symlink():
            raise RuntimeError(
                f"Top-level dimension symlink requires manual resolution: {legacy}"
            )

        if canonical.exists():
            if not identical_trees(legacy, canonical):
                raise RuntimeError(
                    f"Competing non-identical {key} trees exist: {legacy} and {canonical}"
                )

            actions.append(
                Action(
                    kind="remove-identical-legacy-tree",
                    source=str(legacy),
                    destination=str(canonical),
                    dimension=key,
                    canon_relative_path=None,
                    reason="Top-level tree exactly duplicates the canonical dimension tree.",
                )
            )
        else:
            actions.append(
                Action(
                    kind="move-tree",
                    source=str(legacy),
                    destination=str(canonical),
                    dimension=key,
                    canon_relative_path=None,
                    reason="Move the top-level dimension into the vault edifice.",
                )
            )

    return actions


def apply_migration(actions: Sequence[Action], stamp: str) -> dict[str, int]:
    counts = {
        "moved": 0,
        "removed_identical": 0,
        "backed_up": 0,
    }

    ensure_directory(VAULT_ROOT)
    ensure_directory(DIMENSIONS_ROOT)
    ensure_directory(BACKUP_ROOT)

    for action in actions:
        if action.source is None or action.destination is None:
            raise RuntimeError(f"Migration action lacks paths: {action}")

        source = Path(action.source)
        destination = Path(action.destination)

        backup_path(source, stamp)
        counts["backed_up"] += 1

        if action.kind == "move-tree":
            move_path(source, destination)
            counts["moved"] += 1
        elif action.kind == "remove-identical-legacy-tree":
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()

            counts["removed_identical"] += 1
        else:
            raise RuntimeError(f"Unsupported migration action: {action.kind}")

    return counts


def make_record(
    dimension: dict[str, Any],
    canon_object: CanonObject,
    generated_at: str,
) -> dict[str, Any]:
    key = dimension["key"]

    return {
        "schema": "savant://vault/dimensions/record/1.3.0",
        "version": "1.3.0",
        "record_id": f"dimension:{key}:{canon_object.relative_path}",
        "dimension": {
            "key": key,
            "name": dimension["name"],
            "ordinal": dimension["ordinal"],
        },
        "canon": {
            "relative_path": canon_object.relative_path,
            "absolute_path": canon_object.absolute_path,
            "sha256": canon_object.sha256,
            "size": canon_object.size,
            "modified_ns": canon_object.modified_ns,
        },
        "state": {
            "dimensional": "unresolved",
            "admission": "unadmitted",
            "authority": "none",
            "generated_at": generated_at,
        },
        "claims": {
            "admitted": [],
            "candidate": [],
        },
        "unknowns": [
            f"The complete {key} state has not been established.",
            "Relevant source material has not been fully classified.",
            "No accepted decision has admitted dimensional claims for this object.",
        ],
        "contradictions": [],
        "lineage": {
            "source_digest": canon_object.sha256,
            "generator": "/root/savant-runtime/vault/dimensions/sys/scaffold.py",
            "supersedes": [],
            "superseded_by": [],
        },
        "provenance": {
            "method": "deterministic-dimensional-scaffold",
            "source": (
                "savant://vault/dimensions/canon/"
                + canon_object.relative_path
            ),
        },
        "validation": {
            "canon_exists": True,
            "digest_matches": True,
            "schema_valid": True,
            "authority_manufactured": False,
        },
    }


def generated_record(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("schema") == "savant://vault/dimensions/record/1.3.0"
        and value.get("lineage", {}).get("generator")
        == "/root/savant-runtime/vault/dimensions/sys/scaffold.py"
    )


def scaffold_plan(
    registry_value: dict[str, Any],
    canon_objects: Sequence[CanonObject],
    refresh: bool,
) -> list[Action]:
    actions: list[Action] = []

    for dimension in generated_dimensions(registry_value):
        key = dimension["key"]

        for canon_object in canon_objects:
            destination = record_path(key, canon_object)

            if not destination.exists():
                actions.append(
                    Action(
                        kind="create-record",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Required dimensional record is missing.",
                    )
                )
                continue

            if not destination.is_file():
                actions.append(
                    Action(
                        kind="conflict",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Dimensional destination exists but is not a file.",
                    )
                )
                continue

            try:
                existing = load_json(destination)
            except (UnicodeDecodeError, json.JSONDecodeError):
                actions.append(
                    Action(
                        kind="preserve-manual",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Existing dimensional file is not a generated JSON record.",
                    )
                )
                continue

            if not generated_record(existing):
                actions.append(
                    Action(
                        kind="preserve-manual",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Existing dimensional record is manually governed.",
                    )
                )
                continue

            bound_digest = existing.get("canon", {}).get("sha256")

            if bound_digest == canon_object.sha256:
                actions.append(
                    Action(
                        kind="unchanged",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Generated record matches the current canon digest.",
                    )
                )
            elif refresh:
                actions.append(
                    Action(
                        kind="refresh-record",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Generated record is bound to a stale canon digest.",
                    )
                )
            else:
                actions.append(
                    Action(
                        kind="stale",
                        source=canon_object.absolute_path,
                        destination=str(destination),
                        dimension=key,
                        canon_relative_path=canon_object.relative_path,
                        reason="Explicit --refresh is required.",
                    )
                )

    return actions


def apply_scaffold(
    actions: Sequence[Action],
    registry_value: dict[str, Any],
    canon_objects: Sequence[CanonObject],
    stamp: str,
) -> dict[str, int]:
    generated_at = utc_now()
    dimensions_by_key = {
        dimension["key"]: dimension
        for dimension in registry_value["dimensions"]
    }
    canon_by_relative = {
        canon_object.relative_path: canon_object
        for canon_object in canon_objects
    }

    counts = {
        "created": 0,
        "refreshed": 0,
        "unchanged": 0,
        "preserved_manual": 0,
        "stale": 0,
        "conflicts": 0,
        "backed_up": 0,
    }

    for action in actions:
        if action.kind in {"create-record", "refresh-record"}:
            if action.dimension is None or action.canon_relative_path is None:
                raise RuntimeError(f"Incomplete scaffold action: {action}")

            destination = Path(str(action.destination))
            canon_object = canon_by_relative[action.canon_relative_path]
            dimension = dimensions_by_key[action.dimension]

            if action.kind == "refresh-record":
                backup_path(destination, stamp)
                counts["backed_up"] += 1
                counts["refreshed"] += 1
            else:
                counts["created"] += 1

            atomic_json_write(
                destination,
                make_record(
                    dimension,
                    canon_object,
                    generated_at,
                ),
            )
        elif action.kind == "unchanged":
            counts["unchanged"] += 1
        elif action.kind == "preserve-manual":
            counts["preserved_manual"] += 1
        elif action.kind == "stale":
            counts["stale"] += 1
        elif action.kind == "conflict":
            counts["conflicts"] += 1
        else:
            raise RuntimeError(f"Unsupported scaffold action: {action.kind}")

    return counts


def basic_schema_validate(value: Any) -> list[str]:
    failures: list[str] = []

    if not isinstance(value, dict):
        return ["record is not an object"]

    required = {
        "schema",
        "version",
        "record_id",
        "dimension",
        "canon",
        "state",
        "claims",
        "unknowns",
        "contradictions",
        "lineage",
        "provenance",
        "validation",
    }

    missing = sorted(required - set(value))
    failures.extend(f"missing field: {field}" for field in missing)

    if value.get("schema") != "savant://vault/dimensions/record/1.3.0":
        failures.append("incorrect schema identifier")

    digest = value.get("canon", {}).get("sha256")

    if not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
        failures.append("invalid canon SHA-256")

    if value.get("validation", {}).get("authority_manufactured") is not False:
        failures.append("authority_manufactured must be false")

    return failures


def verify(
    registry_value: dict[str, Any],
    canon_objects: Sequence[CanonObject],
) -> list[str]:
    failures: list[str] = []

    if not DIMENSIONS_ROOT.is_dir():
        return [f"missing dimensions root: {DIMENSIONS_ROOT}"]

    if not SYS_ROOT.is_dir():
        failures.append(f"missing sys root: {SYS_ROOT}")

    for dimension in registry_value["dimensions"]:
        path = DIMENSIONS_ROOT / dimension["key"]

        if not path.is_dir():
            failures.append(f"missing dimension directory: {path}")

    for forbidden in registry_value["forbidden_top_level_dimension_paths"]:
        path = Path(forbidden)

        if path.exists() or path.is_symlink():
            failures.append(f"forbidden legacy path remains: {path}")

    for dimension in generated_dimensions(registry_value):
        key = dimension["key"]

        for canon_object in canon_objects:
            destination = record_path(key, canon_object)

            if not destination.is_file():
                failures.append(f"missing record: {destination}")
                continue

            try:
                value = load_json(destination)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                failures.append(f"invalid JSON record {destination}: {error}")
                continue

            if not generated_record(value):
                continue

            for failure in basic_schema_validate(value):
                failures.append(f"{destination}: {failure}")

            actual_digest = value.get("canon", {}).get("sha256")

            if actual_digest != canon_object.sha256:
                failures.append(
                    f"stale digest {destination}: "
                    f"expected={canon_object.sha256} actual={actual_digest}"
                )

            if value.get("dimension", {}).get("key") != key:
                failures.append(f"dimension mismatch: {destination}")

    return failures


def kinship_occurrences() -> list[str]:
    occurrences: list[str] = []

    for path in sorted(SAVANT_ROOT.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue

        if any(
            part in {
                ".git",
                ".venv",
                "__pycache__",
                "node_modules",
                "backups",
            }
            for part in path.parts
        ):
            continue

        if path.suffix.lower() not in SUPPORTED_SUFFIXES | {".py"}:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if KINSHIP_PATTERN.search(content):
            occurrences.append(str(path))

    return occurrences


def write_indexes(registry_value: dict[str, Any], canon_count: int) -> None:
    generated_at = utc_now()

    root_index = {
        "schema": "savant://vault/dimensions/index/1.3.0",
        "version": "1.3.0",
        "generated_at": generated_at,
        "dimension_count": 9,
        "canon_object_count": canon_count,
        "dimensions": registry_value["dimensions"],
        "sys": {
            "path": str(SYS_ROOT),
            "is_dimension": False,
            "function": "Implementation and governance boundary for the dimension subsystem."
        }
    }

    atomic_json_write(DIMENSIONS_ROOT / "DIMENSIONS.json", root_index)

    for dimension in registry_value["dimensions"]:
        atomic_json_write(
            DIMENSIONS_ROOT / dimension["key"] / "DIMENSION.json",
            {
                "schema": "savant://vault/dimensions/dimension-index/1.3.0",
                "version": "1.3.0",
                "generated_at": generated_at,
                "dimension": dimension,
                "canon_object_count": canon_count,
            },
        )


def action_counts(actions: Iterable[Action]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for action in actions:
        counts[action.kind] = counts.get(action.kind, 0) + 1

    return dict(sorted(counts.items()))


def write_report(
    operation: str,
    stamp: str,
    migration_actions: Sequence[Action],
    scaffold_actions: Sequence[Action],
    migration_counts: dict[str, int] | None,
    scaffold_counts: dict[str, int] | None,
    failures: Sequence[str],
    canon_count: int,
) -> Path:
    ensure_directory(REPORT_ROOT)

    report = {
        "schema": "savant://vault/dimensions/report/1.3.0",
        "version": "1.3.0",
        "operation": operation,
        "generated_at": utc_now(),
        "canon_object_count": canon_count,
        "migration_action_counts": action_counts(migration_actions),
        "scaffold_action_counts": action_counts(scaffold_actions),
        "migration_counts": migration_counts,
        "scaffold_counts": scaffold_counts,
        "kinship_occurrences": kinship_occurrences(),
        "failure_count": len(failures),
        "failures": list(failures),
        "migration_actions": [asdict(action) for action in migration_actions],
        "scaffold_actions": [asdict(action) for action in scaffold_actions],
    }

    historical = REPORT_ROOT / f"{stamp}__{operation}.json"
    latest = REPORT_ROOT / "latest.json"

    atomic_json_write(historical, report)
    atomic_json_write(latest, report)

    return historical


def run(mode: str, refresh: bool = False) -> int:
    stamp = timestamp_slug()
    registry_value = registry()
    migration_actions = migration_plan(registry_value)
    migration_counts: dict[str, int] | None = None
    scaffold_counts: dict[str, int] | None = None
    failures: list[str] = []

    pre_migration_canon = find_pre_migration_canon()

    if mode == "apply":
        migration_counts = apply_migration(migration_actions, stamp)

        ensure_directory(DIMENSIONS_ROOT)
        ensure_directory(SYS_ROOT)

        for dimension in registry_value["dimensions"]:
            ensure_directory(DIMENSIONS_ROOT / dimension["key"])

        canon_objects = discover_canon()
        scaffold_actions = scaffold_plan(
            registry_value,
            canon_objects,
            refresh,
        )
        scaffold_counts = apply_scaffold(
            scaffold_actions,
            registry_value,
            canon_objects,
            stamp,
        )
        write_indexes(registry_value, len(canon_objects))
        failures = verify(registry_value, canon_objects)

    elif mode == "verify":
        canon_objects = discover_canon()
        scaffold_actions = scaffold_plan(
            registry_value,
            canon_objects,
            False,
        )
        failures = verify(registry_value, canon_objects)

    elif mode == "plan":
        if pre_migration_canon is None:
            canon_objects = []
            scaffold_actions = []
            failures.append("No canon tree exists at an accepted migration source.")
        else:
            canon_objects = discover_canon(pre_migration_canon)

            if pre_migration_canon == CANON_ROOT:
                scaffold_actions = scaffold_plan(
                    registry_value,
                    canon_objects,
                    refresh,
                )
            else:
                scaffold_actions = [
                    Action(
                        kind="create-after-migration",
                        source=canon_object.absolute_path,
                        destination=str(
                            record_path(dimension["key"], canon_object)
                        ),
                        dimension=dimension["key"],
                        canon_relative_path=canon_object.relative_path,
                        reason="Record will be created after canon migration.",
                    )
                    for dimension in generated_dimensions(registry_value)
                    for canon_object in canon_objects
                ]
    else:
        raise RuntimeError(f"Unsupported mode: {mode}")

    report = write_report(
        operation=mode,
        stamp=stamp,
        migration_actions=migration_actions,
        scaffold_actions=scaffold_actions,
        migration_counts=migration_counts,
        scaffold_counts=scaffold_counts,
        failures=failures,
        canon_count=len(canon_objects),
    )

    result = {
        "operation": mode,
        "passed": not failures,
        "dimensions_root": str(DIMENSIONS_ROOT),
        "sys_root": str(SYS_ROOT),
        "canon_object_count": len(canon_objects),
        "expected_generated_record_count": len(canon_objects) * 8,
        "migration_action_counts": action_counts(migration_actions),
        "scaffold_action_counts": action_counts(scaffold_actions),
        "migration_counts": migration_counts,
        "scaffold_counts": scaffold_counts,
        "kinship_occurrences": kinship_occurrences(),
        "failure_count": len(failures),
        "failures": failures[:50],
        "report": str(report),
    }

    print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if not failures else 1


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage Savant's nine-dimensional Vault archive."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("plan")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--refresh", action="store_true")
    subparsers.add_parser("verify")
    subparsers.add_parser("status")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(
        argv if argv is not None else sys.argv[1:]
    )

    if arguments.command == "plan":
        return run("plan")

    if arguments.command == "apply":
        return run("apply", refresh=arguments.refresh)

    if arguments.command == "verify":
        return run("verify")

    if arguments.command == "status":
        registry_value = registry()
        value = {
            "version": "1.3.0",
            "dimensions_root": str(DIMENSIONS_ROOT),
            "sys_root": str(SYS_ROOT),
            "registered_dimensions": [
                dimension["key"]
                for dimension in registry_value["dimensions"]
            ],
            "canon_exists": CANON_ROOT.is_dir(),
            "legacy_paths": [
                forbidden
                for forbidden in registry_value[
                    "forbidden_top_level_dimension_paths"
                ]
                if Path(forbidden).exists()
                or Path(forbidden).is_symlink()
            ],
            "kinship_occurrences": kinship_occurrences(),
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0

    raise RuntimeError(f"Unknown command: {arguments.command}")


if __name__ == "__main__":
    raise SystemExit(main())
