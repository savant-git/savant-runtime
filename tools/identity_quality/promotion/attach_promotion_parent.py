#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

DEFINITION_ATTACHMENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "definition-attachments"
)

PARENT_ATTACHMENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "parent-attachments"
)

TRANSACTION_ROOT = (
    ROOT
    / "runtime"
    / "identity-promotion"
    / "parent-attachments"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "identity-quality"
    / "promotion-parents"
)

IDENTITY_ROOT = (
    ROOT
    / "edifices"
    / "identity"
)

VOLATILE_FIELDS = {
    "generated_at",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}

PARENT_RELATIONSHIP_TYPES = {
    "attaches_to",
    "belongs_to",
    "child_of",
    "composition",
}

DEFINITION_NAMES = (
    "definition.json",
    "identity.json",
    "authority.json",
)


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


def deterministic_projection(
    value: Any,
) -> Any:
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


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rendered = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


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


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def safe_key(
    value: str,
) -> str:
    return "".join(
        character
        if (
            character.isalnum()
            or character in {
                ".",
                "_",
                "-",
            }
        )
        else "_"
        for character in value
    ).strip("_")


def append_unique(
    collection: list[Any],
    candidate: Any,
) -> None:
    if candidate not in collection:
        collection.append(candidate)


def ensure_mapping(
    document: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    value = document.get(field)

    if isinstance(value, dict):
        return value

    value = {}
    document[field] = value

    return value


def ensure_list(
    document: dict[str, Any],
    field: str,
) -> list[Any]:
    value = document.get(field)

    if isinstance(value, list):
        return value

    value = []
    document[field] = value

    return value


def latest_attachment_paths() -> list[Path]:
    if not DEFINITION_ATTACHMENT_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in DEFINITION_ATTACHMENT_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_attachment_path() -> Path:
    paths = latest_attachment_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion definition attachment exists."
        )

    return paths[0]


def resolve_attachment_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_attachment_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def validate_attachment(
    attachment: dict[str, Any],
) -> None:
    if attachment.get("mode") != "apply":
        raise ValueError(
            "Definition attachment was not applied."
        )

    if attachment.get("passed") is not True:
        raise ValueError(
            "Definition attachment did not pass."
        )

    definition = attachment.get(
        "definition"
    )

    if not isinstance(definition, dict):
        raise ValueError(
            "Attachment has no definition record."
        )

    if definition.get("applied") is not True:
        raise ValueError(
            "Authoritative definition was not attached."
        )

    subject = attachment.get(
        "subject"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Attachment has no subject."
        )

    identifier = subject.get("id")

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
    ):
        raise ValueError(
            "Attachment subject has no identifier."
        )


def subject_definition_path(
    attachment: dict[str, Any],
) -> Path:
    definition = attachment[
        "definition"
    ].get("path")

    if not isinstance(definition, str):
        raise ValueError(
            "Attachment definition path is missing."
        )

    path = (ROOT / definition).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ValueError(
            "Subject definition escapes runtime root."
        ) from exc

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def declared_parent_id(
    subject_document: dict[str, Any],
    attachment: dict[str, Any],
) -> str | None:
    subject = attachment["subject"]

    direct = subject.get("parent")

    if (
        isinstance(direct, str)
        and direct.strip()
    ):
        return direct.strip()

    lineage = subject_document.get(
        "lineage"
    )

    if isinstance(lineage, dict):
        parents = lineage.get("parents")

        if (
            isinstance(parents, list)
            and parents
            and isinstance(parents[0], str)
            and parents[0].strip()
        ):
            return parents[0].strip()

    relationships = subject_document.get(
        "relationships"
    )

    if isinstance(relationships, list):
        for relationship in relationships:
            if not isinstance(
                relationship,
                dict,
            ):
                continue

            if relationship.get(
                "type"
            ) not in PARENT_RELATIONSHIP_TYPES:
                continue

            target = relationship.get(
                "target"
            )

            if (
                isinstance(target, str)
                and target.strip()
            ):
                return target.strip()

    return None


def looks_like_identity_definition(
    path: Path,
) -> bool:
    if not path.is_file():
        return False

    if path.name not in DEFINITION_NAMES:
        return False

    try:
        document = load_json(path)

    except Exception:
        return False

    identifier = document.get("id")

    return (
        isinstance(identifier, str)
        and bool(identifier.strip())
    )


def discover_identity_definitions() -> list[Path]:
    candidates: set[Path] = set()

    if not IDENTITY_ROOT.is_dir():
        return []

    for name in DEFINITION_NAMES:
        for path in IDENTITY_ROOT.rglob(name):
            if looks_like_identity_definition(path):
                candidates.add(
                    path.resolve()
                )

    return sorted(
        candidates,
        key=lambda path: path.as_posix(),
    )


def locate_parent_definition(
    parent_id: str,
) -> Path:
    matches: list[Path] = []

    for path in discover_identity_definitions():
        try:
            document = load_json(path)

        except Exception:
            continue

        if document.get("id") == parent_id:
            matches.append(path)

    if not matches:
        raise FileNotFoundError(
            f"Parent definition not found: {parent_id}"
        )

    if len(matches) > 1:
        rendered = ", ".join(
            relative_path(path)
            for path in matches
        )

        raise RuntimeError(
            f"Parent identity is ambiguous: {rendered}"
        )

    return matches[0]


def backup_file(
    source: Path,
    subject_id: str,
    run_id: str,
    role: str,
) -> Path:
    destination = (
        BACKUP_ROOT
        / safe_key(subject_id)
        / run_id
        / role
        / source.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    if sha256_path(source) != sha256_path(destination):
        raise RuntimeError(
            f"Backup hash mismatch: {source}"
        )

    return destination


def subject_relationship(
    subject_id: str,
    parent_id: str,
    subject_definition: Path,
) -> dict[str, Any]:
    return {
        "type": "attaches_to",
        "target": parent_id,
        "direction": "outbound",
        "authority_transfer": False,
        "reversible": True,
        "contract_governed": True,
        "subject_definition": relative_path(
            subject_definition
        ),
    }


def parent_relationship(
    subject_id: str,
    subject_definition: Path,
) -> dict[str, Any]:
    return {
        "type": "composes",
        "target": subject_id,
        "direction": "outbound",
        "authority_transfer": False,
        "reversible": True,
        "contract_governed": True,
        "subject_definition": relative_path(
            subject_definition
        ),
    }


def extend_subject_definition(
    document: dict[str, Any],
    subject_id: str,
    parent_id: str,
    subject_definition: Path,
) -> dict[str, Any]:
    lineage = ensure_mapping(
        document,
        "lineage",
    )

    parents = lineage.setdefault(
        "parents",
        [],
    )

    if not isinstance(parents, list):
        parents = []
        lineage["parents"] = parents

    append_unique(
        parents,
        parent_id,
    )

    relationships = ensure_list(
        document,
        "relationships",
    )

    append_unique(
        relationships,
        subject_relationship(
            subject_id,
            parent_id,
            subject_definition,
        ),
    )

    authority = ensure_mapping(
        document,
        "authority",
    )

    authority.setdefault(
        "inherited",
        False,
    )

    authority[
        "parent_authority_transfer"
    ] = False

    authority[
        "attachment_reversible"
    ] = True

    dependencies = ensure_mapping(
        document,
        "dependencies",
    )

    optional = dependencies.setdefault(
        "optional",
        [],
    )

    if not isinstance(optional, list):
        optional = []
        dependencies["optional"] = optional

    append_unique(
        optional,
        {
            "id": parent_id,
            "kind": "parent_identity",
            "required": False,
            "authority_transfer": False,
        },
    )

    apertures = ensure_list(
        document,
        "apertures",
    )

    append_unique(
        apertures,
        {
            "id": f"{subject_id}.parent",
            "purpose": (
                "Preserve reversible attachment to "
                "the declared parent identity."
            ),
            "admission": (
                "Requires separate authority, explicit contracts, "
                "lineage, provenance, deterministic behavior, "
                "security review, and passing integration tests."
            ),
        },
    )

    provenance = ensure_mapping(
        document,
        "provenance",
    )

    transformations = provenance.setdefault(
        "transformations",
        [],
    )

    if not isinstance(transformations, list):
        transformations = []
        provenance["transformations"] = transformations

    append_unique(
        transformations,
        "attach_to_declared_parent_without_authority_transfer",
    )

    return document


def extend_parent_definition(
    document: dict[str, Any],
    subject_id: str,
    subject_definition: Path,
) -> dict[str, Any]:
    relationships = ensure_list(
        document,
        "relationships",
    )

    append_unique(
        relationships,
        parent_relationship(
            subject_id,
            subject_definition,
        ),
    )

    composition = ensure_mapping(
        document,
        "composition",
    )

    children = composition.setdefault(
        "children",
        [],
    )

    if not isinstance(children, list):
        children = []
        composition["children"] = children

    append_unique(
        children,
        subject_id,
    )

    dependencies = ensure_mapping(
        document,
        "dependencies",
    )

    runtime = dependencies.setdefault(
        "runtime",
        [],
    )

    if not isinstance(runtime, list):
        runtime = []
        dependencies["runtime"] = runtime

    append_unique(
        runtime,
        {
            "id": subject_id,
            "kind": "child_identity",
            "required": False,
            "authority_transfer": False,
        },
    )

    apertures = ensure_list(
        document,
        "apertures",
    )

    append_unique(
        apertures,
        {
            "id": f"{subject_id}.attachment",
            "purpose": (
                "Admit the declared child through a reversible "
                "contract-governed attachment."
            ),
            "admission": (
                "Parent retains its authority. Child retains its "
                "internal authority. No authority is inherited."
            ),
        },
    )

    provenance = ensure_mapping(
        document,
        "provenance",
    )

    transformations = provenance.setdefault(
        "transformations",
        [],
    )

    if not isinstance(transformations, list):
        transformations = []
        provenance["transformations"] = transformations

    append_unique(
        transformations,
        "admit_child_without_authority_transfer",
    )

    return document


def restore_file(
    backup: Path,
    destination: Path,
) -> dict[str, Any]:
    if not backup.is_file():
        return {
            "passed": False,
            "code": "rollback.backup_missing",
            "backup": relative_path(backup),
        }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        backup,
        destination,
    )

    backup_hash = sha256_path(backup)
    restored_hash = sha256_path(destination)

    return {
        "passed": (
            backup_hash == restored_hash
        ),
        "backup": relative_path(backup),
        "destination": relative_path(
            destination
        ),
        "backup_sha256": backup_hash,
        "restored_sha256": restored_hash,
    }


def attach_parent(
    attachment_path: Path,
    *,
    apply: bool,
    rollback_on_failure: bool,
) -> dict[str, Any]:
    attachment = load_json(
        attachment_path
    )

    validate_attachment(
        attachment
    )

    subject = attachment["subject"]
    subject_id = subject["id"]

    subject_definition = (
        subject_definition_path(
            attachment
        )
    )

    subject_document = load_json(
        subject_definition
    )

    parent_id = declared_parent_id(
        subject_document,
        attachment,
    )

    if parent_id is None:
        raise ValueError(
            "Subject has no declared parent."
        )

    parent_definition = locate_parent_definition(
        parent_id
    )

    parent_document = load_json(
        parent_definition
    )

    subject_before_hash = sha256_path(
        subject_definition
    )

    parent_before_hash = sha256_path(
        parent_definition
    )

    proposed_subject = extend_subject_definition(
        json.loads(
            json.dumps(subject_document)
        ),
        subject_id,
        parent_id,
        subject_definition,
    )

    proposed_parent = extend_parent_definition(
        json.loads(
            json.dumps(parent_document)
        ),
        subject_id,
        subject_definition,
    )

    proposed_subject_digest = digest(
        deterministic_projection(
            proposed_subject
        )
    )

    proposed_parent_digest = digest(
        deterministic_projection(
            proposed_parent
        )
    )

    transaction_seed = {
        "subject": subject_id,
        "parent": parent_id,
        "subject_digest": proposed_subject_digest,
        "parent_digest": proposed_parent_digest,
    }

    run_id = (
        f"parent-{timestamp()}-"
        f"{digest(transaction_seed)[:16]}"
    )

    transaction_root = (
        TRANSACTION_ROOT
        / safe_key(subject_id)
        / run_id
    )

    transaction_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    atomic_write_json(
        transaction_root
        / "definition_attachment.json",
        attachment,
    )

    atomic_write_json(
        transaction_root
        / "proposed_subject.json",
        proposed_subject,
    )

    atomic_write_json(
        transaction_root
        / "proposed_parent.json",
        proposed_parent,
    )

    subject_backup: Path | None = None
    parent_backup: Path | None = None

    subject_after_hash: str | None = None
    parent_after_hash: str | None = None

    rollback: dict[str, Any] | None = None

    applied = False
    passed = True

    if apply:
        subject_backup = backup_file(
            subject_definition,
            subject_id,
            run_id,
            "subject",
        )

        parent_backup = backup_file(
            parent_definition,
            subject_id,
            run_id,
            "parent",
        )

        try:
            atomic_write_json(
                subject_definition,
                proposed_subject,
            )

            atomic_write_json(
                parent_definition,
                proposed_parent,
            )

            written_subject = load_json(
                subject_definition
            )

            written_parent = load_json(
                parent_definition
            )

            written_subject_digest = digest(
                deterministic_projection(
                    written_subject
                )
            )

            written_parent_digest = digest(
                deterministic_projection(
                    written_parent
                )
            )

            subject_after_hash = sha256_path(
                subject_definition
            )

            parent_after_hash = sha256_path(
                parent_definition
            )

            passed = all(
                (
                    written_subject_digest
                    == proposed_subject_digest,
                    written_parent_digest
                    == proposed_parent_digest,
                )
            )

            if not passed:
                raise RuntimeError(
                    "Parent attachment digest mismatch."
                )

            applied = True

        except Exception:
            passed = False

            if (
                rollback_on_failure
                and subject_backup is not None
                and parent_backup is not None
            ):
                subject_restore = restore_file(
                    subject_backup,
                    subject_definition,
                )

                parent_restore = restore_file(
                    parent_backup,
                    parent_definition,
                )

                rollback = {
                    "passed": (
                        subject_restore["passed"]
                        and parent_restore["passed"]
                    ),
                    "subject": subject_restore,
                    "parent": parent_restore,
                }

    result: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-parent-attachment/1.0.0"
        ),
        "operation": (
            "attach_promotion_parent"
        ),
        "generated_at": utc_now(),
        "mode": (
            "apply"
            if apply
            else "plan"
        ),
        "definition_attachment": {
            "path": relative_path(
                attachment_path
            ),
            "sha256": sha256_path(
                attachment_path
            ),
            "digest": attachment.get(
                "digest"
            ),
        },
        "subject": {
            **subject,
            "definition": relative_path(
                subject_definition
            ),
            "before_sha256": (
                subject_before_hash
            ),
            "proposed_digest": (
                proposed_subject_digest
            ),
            "after_sha256": (
                subject_after_hash
            ),
            "backup": (
                relative_path(
                    subject_backup
                )
                if subject_backup
                else None
            ),
        },
        "parent": {
            "id": parent_id,
            "definition": relative_path(
                parent_definition
            ),
            "before_sha256": (
                parent_before_hash
            ),
            "proposed_digest": (
                proposed_parent_digest
            ),
            "after_sha256": (
                parent_after_hash
            ),
            "backup": (
                relative_path(
                    parent_backup
                )
                if parent_backup
                else None
            ),
        },
        "boundary": {
            "authority_transfer": False,
            "subject_inherits_parent_authority": False,
            "parent_inherits_subject_authority": False,
            "contract_governed": True,
            "reversible": True,
        },
        "transaction": {
            "id": run_id,
            "root": relative_path(
                transaction_root
            ),
        },
        "applied": applied,
        "rollback": rollback,
        "passed": passed,
    }

    result["digest"] = digest(
        deterministic_projection(
            result
        )
    )

    atomic_write_json(
        transaction_root
        / "result.json",
        result,
    )

    return result


def markdown(
    result: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Promotion Parent Attachment",
            "",
            (
                f"- Generated: "
                f"`{result['generated_at']}`"
            ),
            (
                f"- Subject: "
                f"`{result['subject']['id']}`"
            ),
            (
                f"- Parent: "
                f"`{result['parent']['id']}`"
            ),
            (
                f"- Mode: "
                f"`{result['mode']}`"
            ),
            (
                f"- Applied: "
                f"**{result['applied']}**"
            ),
            (
                f"- Passed: "
                f"**{result['passed']}**"
            ),
            (
                f"- Authority transfer: "
                f"`{result['boundary']['authority_transfer']}`"
            ),
            (
                f"- Reversible: "
                f"`{result['boundary']['reversible']}`"
            ),
            (
                f"- Digest: "
                f"`{result['digest']}`"
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Attach a promoted identity to its declared parent "
            "without transferring authority."
        )
    )

    parser.add_argument(
        "--attachment",
        type=Path,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--no-rollback",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=PARENT_ATTACHMENT_ROOT,
    )

    arguments = parser.parse_args()

    try:
        attachment_path = (
            resolve_attachment_path(
                arguments.attachment
            )
        )

        result = attach_parent(
            attachment_path,
            apply=arguments.apply,
            rollback_on_failure=(
                not arguments.no_rollback
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "attach_promotion_parent"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    subject_key = safe_key(
        result["subject"]["id"]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / f"{run_id}__parent-attachment.json"
    )

    markdown_path = (
        output_root
        / f"{run_id}__parent-attachment.md"
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    atomic_write_json(
        json_path,
        result,
    )

    atomic_write_json(
        latest_json,
        result,
    )

    rendered = markdown(result)

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": result[
            "generated_at"
        ],
        "subject": result[
            "subject"
        ][
            "id"
        ],
        "parent": result[
            "parent"
        ][
            "id"
        ],
        "mode": result["mode"],
        "applied": result["applied"],
        "passed": result["passed"],
        "attachment_digest": (
            result["digest"]
        ),
        "files": {
            json_path.name: sha256_path(
                json_path
            ),
            markdown_path.name: sha256_path(
                markdown_path
            ),
            latest_json.name: sha256_path(
                latest_json
            ),
            latest_markdown.name: sha256_path(
                latest_markdown
            ),
        },
    }

    manifest_path = (
        output_root
        / f"{run_id}__manifest.json"
    )

    atomic_write_json(
        manifest_path,
        manifest,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "attach_promotion_parent"
                ),
                "passed": result["passed"],
                "mode": result["mode"],
                "applied": result["applied"],
                "subject": result["subject"],
                "parent": result["parent"],
                "boundary": result["boundary"],
                "digest": result["digest"],
                "transaction": (
                    result["transaction"]
                ),
                "rollback": result["rollback"],
                "reports": {
                    "json": str(json_path),
                    "markdown": str(
                        markdown_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
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

    if (
        arguments.strict
        and not result["passed"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
