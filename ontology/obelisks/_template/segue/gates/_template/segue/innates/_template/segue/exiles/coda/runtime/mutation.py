#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path("/root/savant-runtime").resolve()

RECEIPT_ROOT = (
    ROOT
    / "vault"
    / "coda"
    / "mutation_receipts"
)

BACKUP_ROOT = (
    ROOT
    / "vault"
    / "coda"
    / "mutation_backups"
)

OWNER = "coda"

SCHEMA = "savant://coda/mutation-receipt/2"

BLOCKED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}

PROTECTED_ROOT_FILES = {
    ".env",
}

SUPPORTED_OPERATIONS = {
    "replace_text",
    "create_text",
    "append_text",
    "delete_file",
    "move_file",
    "copy_file",
    "make_directory",
    "remove_directory",
}


class MutationError(RuntimeError):
    pass


class MutationConflict(MutationError):
    pass


class MutationPolicyError(MutationError):
    pass


class MutationPlanError(MutationError):
    pass


def utc_now() -> str:
    return datetime.now(
        UTC
    ).isoformat()


def digest_bytes(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def digest_file(
    path: Path,
) -> str | None:
    if not path.exists():
        return None

    if not path.is_file():
        raise MutationError(
            f"target is not a file: {path}"
        )

    return digest_bytes(
        path.read_bytes()
    )


def _normalize_relative_path(
    relative_path: str,
) -> str:
    value = str(
        relative_path
        or ""
    ).strip()

    if not value:
        raise MutationError(
            "mutation path is required"
        )

    candidate = Path(
        value
    )

    if candidate.is_absolute():
        try:
            candidate = (
                candidate.resolve()
                .relative_to(ROOT)
            )
        except ValueError as exc:
            raise MutationPolicyError(
                "blocked outside Savant root"
            ) from exc

    normalized = str(
        candidate
    ).lstrip("/")

    if not normalized:
        raise MutationError(
            "mutation path resolves to root"
        )

    return normalized


def resolve_target(
    relative_path: str,
) -> tuple[Path, str]:
    normalized = (
        _normalize_relative_path(
            relative_path
        )
    )

    target = (
        ROOT
        / normalized
    ).resolve()

    if (
        target == ROOT
        or ROOT not in target.parents
    ):
        raise MutationPolicyError(
            "blocked outside Savant root"
        )

    relative = target.relative_to(
        ROOT
    )

    if any(
        part in BLOCKED_PARTS
        for part in relative.parts
    ):
        raise MutationPolicyError(
            "blocked protected path"
        )

    if (
        len(relative.parts) == 1
        and relative.name
        in PROTECTED_ROOT_FILES
    ):
        raise MutationPolicyError(
            "blocked protected root file"
        )

    return (
        target,
        str(relative),
    )


def _fsync_directory(
    path: Path,
) -> None:
    descriptor = os.open(
        str(path),
        os.O_RDONLY,
    )

    try:
        os.fsync(
            descriptor
        )
    finally:
        os.close(
            descriptor
        )


def _atomic_write_bytes(
    target: Path,
    payload: bytes,
) -> None:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                f".{target.name}.coda-"
            ),
            dir=str(
                target.parent
            ),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                payload
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            target,
        )

        _fsync_directory(
            target.parent
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def _atomic_write_json(
    destination: Path,
    payload: Mapping[str, Any],
) -> None:
    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    _atomic_write_bytes(
        destination,
        encoded,
    )


def _receipt_id(
    operation: str,
    material: Mapping[str, Any],
    timestamp: str,
) -> str:
    canonical = json.dumps(
        {
            "operation": operation,
            "material": material,
            "timestamp": timestamp,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode(
        "utf-8"
    )

    return (
        "coda_"
        + digest_bytes(
            canonical
        )[:24]
    )


def write_receipt(
    receipt: dict[str, Any],
) -> Path:
    RECEIPT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        RECEIPT_ROOT
        / f'{receipt["id"]}.json'
    )

    _atomic_write_json(
        destination,
        receipt,
    )

    return destination


def _backup_file(
    target: Path,
    relative: str,
    before_digest: str | None,
) -> str | None:
    if (
        before_digest is None
        or not target.is_file()
    ):
        return None

    destination = (
        BACKUP_ROOT
        / before_digest[:2]
        / before_digest
    )

    if not destination.exists():
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = target.read_bytes()

        _atomic_write_bytes(
            destination,
            payload,
        )

        if digest_file(
            destination
        ) != before_digest:
            destination.unlink(
                missing_ok=True
            )

            raise MutationError(
                "backup digest verification failed"
            )

    return str(
        destination.relative_to(
            ROOT
        )
    )


def _assert_expected_digest(
    before_digest: str | None,
    expected_digest: str | None,
) -> None:
    if (
        expected_digest is not None
        and before_digest
        != expected_digest
    ):
        raise MutationConflict(
            "target changed since inspection"
        )


def _base_receipt(
    *,
    operation: str,
    requester: str,
    intent: str,
    material: Mapping[str, Any],
) -> dict[str, Any]:
    timestamp = utc_now()

    receipt_id = _receipt_id(
        operation,
        material,
        timestamp,
    )

    return {
        "id": receipt_id,
        "schema": SCHEMA,
        "owner": OWNER,
        "operation": operation,
        "requester": str(
            requester
            or "unknown"
        ),
        "intent": str(
            intent
            or ""
        ),
        "atomic": True,
        "verified": True,
        "reversible": False,
        "authority_effect": "none",
        "timestamp": timestamp,
    }


def _finish_receipt(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    receipt_path = write_receipt(
        receipt
    )

    result = dict(
        receipt
    )

    result["receipt"] = str(
        receipt_path.relative_to(
            ROOT
        )
    )

    return result


def replace_text(
    relative_path: str,
    content: str,
    *,
    expected_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized file replacement"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if (
        target.exists()
        and not target.is_file()
    ):
        raise MutationError(
            "replacement target is not a file"
        )

    before_digest = digest_file(
        target
    )

    _assert_expected_digest(
        before_digest,
        expected_digest,
    )

    backup = _backup_file(
        target,
        relative,
        before_digest,
    )

    encoded = str(
        content
    ).encode(
        "utf-8"
    )

    after_digest = digest_bytes(
        encoded
    )

    _atomic_write_bytes(
        target,
        encoded,
    )

    confirmed_digest = digest_file(
        target
    )

    if confirmed_digest != after_digest:
        raise MutationError(
            "post-write digest verification failed"
        )

    receipt = _base_receipt(
        operation="replace_text",
        requester=requester,
        intent=intent,
        material={
            "path": relative,
            "before_digest": before_digest,
            "after_digest": after_digest,
        },
    )

    receipt.update(
        {
            "path": relative,
            "before_digest": before_digest,
            "after_digest": after_digest,
            "bytes": len(encoded),
            "backup": backup,
            "reversible": (
                backup is not None
            ),
        }
    )

    return _finish_receipt(
        receipt
    )


def create_text(
    relative_path: str,
    content: str,
    *,
    requester: str = "palaver",
    intent: str = (
        "authorized file creation"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if target.exists():
        raise MutationConflict(
            f"target already exists: {relative}"
        )

    return replace_text(
        relative,
        content,
        expected_digest=None,
        requester=requester,
        intent=intent,
    )


def append_text(
    relative_path: str,
    content: str,
    *,
    expected_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized file append"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if not target.is_file():
        raise MutationError(
            "append target must exist as a file"
        )

    before_digest = digest_file(
        target
    )

    _assert_expected_digest(
        before_digest,
        expected_digest,
    )

    current = target.read_text(
        encoding="utf-8"
    )

    result = replace_text(
        relative,
        current + str(content),
        expected_digest=before_digest,
        requester=requester,
        intent=intent,
    )

    result[
        "requested_operation"
    ] = "append_text"

    return result


def delete_file(
    relative_path: str,
    *,
    expected_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized file deletion"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if not target.is_file():
        raise MutationError(
            "delete target is not a file"
        )

    before_digest = digest_file(
        target
    )

    _assert_expected_digest(
        before_digest,
        expected_digest,
    )

    backup = _backup_file(
        target,
        relative,
        before_digest,
    )

    target.unlink()

    _fsync_directory(
        target.parent
    )

    if target.exists():
        raise MutationError(
            "file deletion verification failed"
        )

    receipt = _base_receipt(
        operation="delete_file",
        requester=requester,
        intent=intent,
        material={
            "path": relative,
            "before_digest": before_digest,
        },
    )

    receipt.update(
        {
            "path": relative,
            "before_digest": before_digest,
            "after_digest": None,
            "backup": backup,
            "reversible": (
                backup is not None
            ),
        }
    )

    return _finish_receipt(
        receipt
    )


def copy_file(
    source_path: str,
    destination_path: str,
    *,
    expected_source_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized file copy"
    ),
) -> dict[str, Any]:
    source, source_relative = (
        resolve_target(
            source_path
        )
    )

    destination, destination_relative = (
        resolve_target(
            destination_path
        )
    )

    if not source.is_file():
        raise MutationError(
            "copy source is not a file"
        )

    if destination.exists():
        raise MutationConflict(
            "copy destination already exists"
        )

    source_digest = digest_file(
        source
    )

    _assert_expected_digest(
        source_digest,
        expected_source_digest,
    )

    payload = source.read_bytes()

    _atomic_write_bytes(
        destination,
        payload,
    )

    after_digest = digest_file(
        destination
    )

    if after_digest != source_digest:
        raise MutationError(
            "copy digest verification failed"
        )

    receipt = _base_receipt(
        operation="copy_file",
        requester=requester,
        intent=intent,
        material={
            "source": source_relative,
            "destination": (
                destination_relative
            ),
            "digest": source_digest,
        },
    )

    receipt.update(
        {
            "source": source_relative,
            "destination": (
                destination_relative
            ),
            "before_digest": None,
            "after_digest": after_digest,
            "bytes": len(payload),
        }
    )

    return _finish_receipt(
        receipt
    )


def move_file(
    source_path: str,
    destination_path: str,
    *,
    expected_source_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized file move"
    ),
) -> dict[str, Any]:
    source, source_relative = (
        resolve_target(
            source_path
        )
    )

    destination, destination_relative = (
        resolve_target(
            destination_path
        )
    )

    if not source.is_file():
        raise MutationError(
            "move source is not a file"
        )

    if destination.exists():
        raise MutationConflict(
            "move destination already exists"
        )

    source_digest = digest_file(
        source
    )

    _assert_expected_digest(
        source_digest,
        expected_source_digest,
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        os.replace(
            source,
            destination,
        )
    except OSError:
        shutil.copy2(
            source,
            destination,
        )
        source.unlink()

    if (
        source.exists()
        or digest_file(destination)
        != source_digest
    ):
        raise MutationError(
            "move verification failed"
        )

    _fsync_directory(
        destination.parent
    )

    if (
        source.parent
        != destination.parent
    ):
        _fsync_directory(
            source.parent
        )

    receipt = _base_receipt(
        operation="move_file",
        requester=requester,
        intent=intent,
        material={
            "source": source_relative,
            "destination": (
                destination_relative
            ),
            "digest": source_digest,
        },
    )

    receipt.update(
        {
            "source": source_relative,
            "destination": (
                destination_relative
            ),
            "before_digest": source_digest,
            "after_digest": source_digest,
            "reversible": True,
        }
    )

    return _finish_receipt(
        receipt
    )


def make_directory(
    relative_path: str,
    *,
    requester: str = "palaver",
    intent: str = (
        "authorized directory creation"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if target.exists():
        raise MutationConflict(
            "directory target already exists"
        )

    target.mkdir(
        parents=True,
        exist_ok=False,
    )

    if not target.is_dir():
        raise MutationError(
            "directory creation verification failed"
        )

    receipt = _base_receipt(
        operation="make_directory",
        requester=requester,
        intent=intent,
        material={
            "path": relative,
        },
    )

    receipt.update(
        {
            "path": relative,
            "reversible": True,
        }
    )

    return _finish_receipt(
        receipt
    )


def remove_directory(
    relative_path: str,
    *,
    require_empty: bool = True,
    requester: str = "palaver",
    intent: str = (
        "authorized directory removal"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    if not target.is_dir():
        raise MutationError(
            "directory removal target is not a directory"
        )

    if not require_empty:
        raise MutationPolicyError(
            "recursive directory deletion is not authorized"
        )

    try:
        target.rmdir()
    except OSError as exc:
        raise MutationConflict(
            "directory is not empty"
        ) from exc

    receipt = _base_receipt(
        operation="remove_directory",
        requester=requester,
        intent=intent,
        material={
            "path": relative,
        },
    )

    receipt.update(
        {
            "path": relative,
            "reversible": True,
        }
    )

    return _finish_receipt(
        receipt
    )


def restore_backup(
    relative_path: str,
    backup_path: str,
    *,
    expected_digest: str | None = None,
    requester: str = "palaver",
    intent: str = (
        "authorized Coda rollback"
    ),
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    backup, backup_relative = (
        resolve_target(
            backup_path
        )
    )

    if (
        BACKUP_ROOT
        not in backup.parents
    ):
        raise MutationPolicyError(
            "rollback source is not a Coda backup"
        )

    if not backup.is_file():
        raise MutationError(
            "rollback backup is missing"
        )

    current_digest = digest_file(
        target
    )

    _assert_expected_digest(
        current_digest,
        expected_digest,
    )

    payload = backup.read_bytes()

    restored_digest = digest_bytes(
        payload
    )

    _atomic_write_bytes(
        target,
        payload,
    )

    if digest_file(
        target
    ) != restored_digest:
        raise MutationError(
            "rollback verification failed"
        )

    receipt = _base_receipt(
        operation="restore_backup",
        requester=requester,
        intent=intent,
        material={
            "path": relative,
            "backup": backup_relative,
            "before_digest": (
                current_digest
            ),
            "after_digest": (
                restored_digest
            ),
        },
    )

    receipt.update(
        {
            "path": relative,
            "backup": backup_relative,
            "before_digest": (
                current_digest
            ),
            "after_digest": (
                restored_digest
            ),
            "reversible": True,
        }
    )

    return _finish_receipt(
        receipt
    )


def inspect_path(
    relative_path: str,
) -> dict[str, Any]:
    target, relative = resolve_target(
        relative_path
    )

    exists = target.exists()

    return {
        "owner": OWNER,
        "path": relative,
        "exists": exists,
        "is_file": (
            target.is_file()
            if exists
            else False
        ),
        "is_directory": (
            target.is_dir()
            if exists
            else False
        ),
        "digest": (
            digest_file(target)
            if target.is_file()
            else None
        ),
        "bytes": (
            target.stat().st_size
            if target.is_file()
            else None
        ),
        "authority_effect": "none",
    }


def execute_operation(
    operation: Mapping[str, Any],
    *,
    requester: str = "palaver",
    intent: str = (
        "authorized Coda operation"
    ),
) -> dict[str, Any]:
    if not isinstance(
        operation,
        Mapping,
    ):
        raise MutationPlanError(
            "operation must be an object"
        )

    kind = str(
        operation.get(
            "operation"
        )
        or ""
    ).strip()

    if kind not in SUPPORTED_OPERATIONS:
        raise MutationPlanError(
            f"unsupported operation: {kind!r}"
        )

    if kind == "replace_text":
        return replace_text(
            str(operation.get("path") or ""),
            str(operation.get("content") or ""),
            expected_digest=operation.get(
                "expected_digest"
            ),
            requester=requester,
            intent=intent,
        )

    if kind == "create_text":
        return create_text(
            str(operation.get("path") or ""),
            str(operation.get("content") or ""),
            requester=requester,
            intent=intent,
        )

    if kind == "append_text":
        return append_text(
            str(operation.get("path") or ""),
            str(operation.get("content") or ""),
            expected_digest=operation.get(
                "expected_digest"
            ),
            requester=requester,
            intent=intent,
        )

    if kind == "delete_file":
        return delete_file(
            str(operation.get("path") or ""),
            expected_digest=operation.get(
                "expected_digest"
            ),
            requester=requester,
            intent=intent,
        )

    if kind == "copy_file":
        return copy_file(
            str(operation.get("source") or ""),
            str(
                operation.get(
                    "destination"
                )
                or ""
            ),
            expected_source_digest=(
                operation.get(
                    "expected_source_digest"
                )
            ),
            requester=requester,
            intent=intent,
        )

    if kind == "move_file":
        return move_file(
            str(operation.get("source") or ""),
            str(
                operation.get(
                    "destination"
                )
                or ""
            ),
            expected_source_digest=(
                operation.get(
                    "expected_source_digest"
                )
            ),
            requester=requester,
            intent=intent,
        )

    if kind == "make_directory":
        return make_directory(
            str(operation.get("path") or ""),
            requester=requester,
            intent=intent,
        )

    if kind == "remove_directory":
        return remove_directory(
            str(operation.get("path") or ""),
            require_empty=True,
            requester=requester,
            intent=intent,
        )

    raise MutationPlanError(
        "operation dispatch failed"
    )


def execute_plan(
    operations: Sequence[
        Mapping[str, Any]
    ],
    *,
    requester: str = "palaver",
    intent: str = (
        "authorized Coda mutation plan"
    ),
) -> dict[str, Any]:
    if not isinstance(
        operations,
        Sequence,
    ) or isinstance(
        operations,
        (str, bytes),
    ):
        raise MutationPlanError(
            "operations must be a sequence"
        )

    results: list[
        dict[str, Any]
    ] = []

    for index, operation in enumerate(
        operations
    ):
        try:
            result = execute_operation(
                operation,
                requester=requester,
                intent=(
                    f"{intent}; "
                    f"operation={index}"
                ),
            )
        except Exception as exc:
            raise MutationPlanError(
                "mutation plan failed at "
                f"operation {index}: {exc}"
            ) from exc

        results.append(
            result
        )

    material = [
        {
            "operation": item.get(
                "operation"
            ),
            "path": item.get(
                "path"
            ),
            "source": item.get(
                "source"
            ),
            "destination": item.get(
                "destination"
            ),
            "receipt": item.get(
                "receipt"
            ),
        }
        for item in results
    ]

    timestamp = utc_now()

    return {
        "schema": (
            "savant://coda/"
            "mutation-plan-result/1"
        ),
        "owner": OWNER,
        "requester": requester,
        "intent": intent,
        "operation_count": len(
            results
        ),
        "results": results,
        "digest": digest_bytes(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
            ).encode(
                "utf-8"
            )
        ),
        "timestamp": timestamp,
        "authority_effect": "none",
    }


def status() -> dict[str, Any]:
    return {
        "owner": OWNER,
        "purpose": (
            "durable filesystem mutation"
        ),
        "root": str(ROOT),
        "schema": SCHEMA,
        "operations": sorted(
            SUPPORTED_OPERATIONS
        ),
        "atomic_file_writes": True,
        "optimistic_concurrency": True,
        "digest_verification": True,
        "content_addressed_backups": True,
        "rollback": True,
        "receipts": True,
        "mutation_plans": True,
        "path_containment": True,
        "protected_paths": True,
        "recursive_delete": False,
        "authority_effect": "none",
        "ready": True,
    }


def main() -> int:
    print(
        json.dumps(
            status(),
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
