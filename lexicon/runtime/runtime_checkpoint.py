#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = RUNTIME_ROOT.parent

CHECKPOINT_ROOT = (
    RUNTIME_ROOT
    / "checkpoints"
)

OBJECT_ROOT = (
    CHECKPOINT_ROOT
    / "objects"
)

MANIFEST_ROOT = (
    CHECKPOINT_ROOT
    / "manifests"
)

REF_ROOT = (
    CHECKPOINT_ROOT
    / "refs"
)

HEAD_PATH = (
    REF_ROOT
    / "HEAD.json"
)

INDEX_PATH = (
    CHECKPOINT_ROOT
    / "checkpoint_index.json"
)

EVENT_LOG_PATH = (
    CHECKPOINT_ROOT
    / "checkpoint_events.jsonl"
)

TRANSACTION_HEAD_PATH = (
    RUNTIME_ROOT
    / "transactions"
    / "transaction_head.json"
)

DEFAULT_TARGETS = (
    LEXICON_ROOT / "compiled",
    RUNTIME_ROOT / "compiled",
)


class RuntimeCheckpointError(
    RuntimeError
):
    pass


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_digest(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def load_json(
    path: Path,
    default: Any = None,
) -> Any:
    if not path.is_file():
        return default

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(
            handle
        )


def write_json_atomic(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
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
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )

            handle.write(
                "\n"
            )

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


def append_jsonl(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            canonical_json(
                payload
            )
        )

        handle.write(
            "\n"
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                payload = json.loads(
                    line
                )

            except json.JSONDecodeError as error:
                raise RuntimeCheckpointError(
                    f"Invalid JSONL at "
                    f"{path}:{line_number}: "
                    f"{error}"
                ) from error

            if not isinstance(
                payload,
                dict,
            ):
                raise RuntimeCheckpointError(
                    f"Checkpoint event must be "
                    f"an object at "
                    f"{path}:{line_number}"
                )

            records.append(
                payload
            )

    return records


def normalize_path(
    path: Path,
) -> Path:
    return path.expanduser().resolve()


def object_path(
    sha256: str,
) -> Path:
    return (
        OBJECT_ROOT
        / sha256[
            :2
        ]
        / sha256[
            2:
        ]
    )


class RuntimeCheckpoint:

    def __init__(
        self,
    ) -> None:
        for path in (
            CHECKPOINT_ROOT,
            OBJECT_ROOT,
            MANIFEST_ROOT,
            REF_ROOT,
        ):
            path.mkdir(
                parents=True,
                exist_ok=True,
            )

    def source_targets(
        self,
        supplied: list[str],
    ) -> list[Path]:
        candidates = (
            [
                normalize_path(
                    Path(
                        value
                    )
                )
                for value in supplied
            ]
            if supplied
            else [
                normalize_path(
                    path
                )
                for path in DEFAULT_TARGETS
            ]
        )

        targets = {}

        for candidate in candidates:
            if not candidate.exists():
                continue

            try:
                candidate.relative_to(
                    LEXICON_ROOT
                )

            except ValueError as error:
                raise RuntimeCheckpointError(
                    f"Checkpoint target is outside "
                    f"lexicon root: {candidate}"
                ) from error

            targets[
                str(
                    candidate
                )
            ] = candidate

        return [
            targets[
                key
            ]
            for key in sorted(
                targets
            )
        ]

    def inventory(
        self,
        targets: list[Path],
    ) -> list[dict[str, Any]]:
        records = []

        for target in targets:
            if target.is_file():
                records.append(
                    self.file_record(
                        target
                    )
                )

                continue

            for path in sorted(
                target.rglob(
                    "*"
                )
            ):
                if not path.is_file():
                    continue

                if "__pycache__" in path.parts:
                    continue

                if path.suffix in {
                    ".pyc",
                    ".pyo",
                }:
                    continue

                records.append(
                    self.file_record(
                        path
                    )
                )

        records.sort(
            key=lambda record: (
                record[
                    "relative_path"
                ]
            )
        )

        return records

    def file_record(
        self,
        path: Path,
    ) -> dict[str, Any]:
        relative = path.relative_to(
            LEXICON_ROOT
        )

        stat = path.stat()

        sha256 = file_digest(
            path
        )

        return {
            "relative_path": str(
                relative
            ),
            "source_path": str(
                path
            ),
            "sha256": sha256,
            "size": stat.st_size,
            "mode": stat.st_mode & 0o7777,
            "object": str(
                object_path(
                    sha256
                )
            ),
        }

    def store_object(
        self,
        source: Path,
        sha256: str,
    ) -> dict[str, Any]:
        destination = object_path(
            sha256
        )

        if destination.is_file():
            actual = file_digest(
                destination
            )

            if actual != sha256:
                raise RuntimeCheckpointError(
                    f"Object collision or corruption: "
                    f"{destination}"
                )

            return {
                "created": False,
                "path": str(
                    destination
                ),
                "sha256": sha256,
            }

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".object.",
            suffix=".tmp",
            dir=str(
                destination.parent
            ),
        )

        temporary_path = Path(
            temporary_name
        )

        try:
            with os.fdopen(
                descriptor,
                "wb",
            ) as destination_handle:
                with source.open(
                    "rb"
                ) as source_handle:
                    shutil.copyfileobj(
                        source_handle,
                        destination_handle,
                        length=1024 * 1024,
                    )

                destination_handle.flush()

                os.fsync(
                    destination_handle.fileno()
                )

            actual = file_digest(
                temporary_path
            )

            if actual != sha256:
                raise RuntimeCheckpointError(
                    f"Object digest mismatch: "
                    f"{source}"
                )

            try:
                os.link(
                    temporary_path,
                    destination,
                )

            except FileExistsError:
                pass

            if not destination.is_file():
                os.replace(
                    temporary_path,
                    destination,
                )

            os.chmod(
                destination,
                0o444,
            )

        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return {
            "created": True,
            "path": str(
                destination
            ),
            "sha256": sha256,
        }

    def next_sequence(
        self,
    ) -> int:
        index = load_json(
            INDEX_PATH,
            default={},
        )

        if not isinstance(
            index,
            dict,
        ):
            return 1

        return int(
            index.get(
                "sequence",
                0,
            )
        ) + 1

    def append_event(
        self,
        checkpoint_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        events = read_jsonl(
            EVENT_LOG_PATH
        )

        previous_digest = (
            events[
                -1
            ].get(
                "digest"
            )
            if events
            else None
        )

        event = {
            "event_id": (
                "runtime:checkpoint:event:"
                f"{len(events) + 1:012d}"
            ),
            "sequence": len(
                events
            ) + 1,
            "checkpoint_id": checkpoint_id,
            "event_type": event_type,
            "timestamp": utc_now(),
            "previous_digest": previous_digest,
            "payload": payload,
        }

        event[
            "digest"
        ] = digest(
            event
        )

        append_jsonl(
            EVENT_LOG_PATH,
            event,
        )

        return event

    def update_index(
        self,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        existing = load_json(
            INDEX_PATH,
            default={},
        )

        if not isinstance(
            existing,
            dict,
        ):
            existing = {}

        records = existing.get(
            "records",
            {}
        )

        if not isinstance(
            records,
            dict,
        ):
            records = {}

        checkpoint_id = str(
            manifest[
                "checkpoint_id"
            ]
        )

        records[
            checkpoint_id
        ] = {
            "checkpoint_id": checkpoint_id,
            "sequence": manifest[
                "sequence"
            ],
            "created_at": manifest[
                "created_at"
            ],
            "label": manifest.get(
                "label"
            ),
            "manifest_path": str(
                MANIFEST_ROOT
                / f"{checkpoint_id}.json"
            ),
            "manifest_digest": manifest[
                "digest"
            ],
            "tree_digest": manifest[
                "tree_digest"
            ],
            "record_count": manifest[
                "record_count"
            ],
            "total_size": manifest[
                "total_size"
            ],
            "parent_checkpoint": manifest.get(
                "parent_checkpoint"
            ),
            "transaction": manifest.get(
                "transaction"
            ),
        }

        ordered = {
            checkpoint: records[
                checkpoint
            ]
            for checkpoint in sorted(
                records,
                key=lambda key: (
                    int(
                        records[
                            key
                        ].get(
                            "sequence",
                            0,
                        )
                    ),
                    key,
                ),
            )
        }

        payload = {
            "index_id": (
                "runtime:checkpoint:index"
            ),
            "sequence": max(
                (
                    int(
                        record.get(
                            "sequence",
                            0,
                        )
                    )
                    for record in ordered.values()
                ),
                default=0,
            ),
            "checkpoint_count": len(
                ordered
            ),
            "records": ordered,
            "updated_at": utc_now(),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        write_json_atomic(
            INDEX_PATH,
            payload,
        )

        return payload

    def create(
        self,
        *,
        label: str | None,
        supplied_targets: list[str],
    ) -> dict[str, Any]:
        targets = self.source_targets(
            supplied_targets
        )

        if not targets:
            raise RuntimeCheckpointError(
                "No checkpoint targets exist"
            )

        records = self.inventory(
            targets
        )

        for record in records:
            self.store_object(
                Path(
                    record[
                        "source_path"
                    ]
                ),
                record[
                    "sha256"
                ],
            )

        sequence = self.next_sequence()

        checkpoint_id = (
            "runtime-checkpoint-"
            f"{sequence:012d}-"
            f"{uuid.uuid4().hex[:12]}"
        )

        head = load_json(
            HEAD_PATH,
            default={},
        )

        parent_checkpoint = (
            head.get(
                "checkpoint_id"
            )
            if isinstance(
                head,
                dict,
            )
            else None
        )

        transaction = load_json(
            TRANSACTION_HEAD_PATH,
            default=None,
        )

        tree_projection = [
            {
                "relative_path": record[
                    "relative_path"
                ],
                "sha256": record[
                    "sha256"
                ],
                "size": record[
                    "size"
                ],
                "mode": record[
                    "mode"
                ],
            }
            for record in records
        ]

        manifest = {
            "checkpoint_id": checkpoint_id,
            "sequence": sequence,
            "created_at": utc_now(),
            "label": (
                label.strip()
                if label
                else None
            ),
            "lexicon_root": str(
                LEXICON_ROOT
            ),
            "targets": [
                str(
                    target.relative_to(
                        LEXICON_ROOT
                    )
                )
                for target in targets
            ],
            "record_count": len(
                records
            ),
            "total_size": sum(
                int(
                    record[
                        "size"
                    ]
                )
                for record in records
            ),
            "tree_digest": digest(
                tree_projection
            ),
            "parent_checkpoint": (
                parent_checkpoint
            ),
            "transaction": transaction,
            "records": records,
            "dependencies": {
                "object_store": str(
                    OBJECT_ROOT
                ),
                "lexicon_root": str(
                    LEXICON_ROOT
                ),
            },
            "provenance": {
                "generator": str(
                    Path(
                        __file__
                    ).resolve()
                ),
                "transaction_head": str(
                    TRANSACTION_HEAD_PATH
                ),
            },
            "lineage": {
                "derived_from": [
                    record[
                        "sha256"
                    ]
                    for record in records
                ],
                "follows": (
                    [
                        parent_checkpoint
                    ]
                    if parent_checkpoint
                    else []
                ),
            },
        }

        manifest[
            "digest"
        ] = digest(
            manifest
        )

        manifest_path = (
            MANIFEST_ROOT
            / f"{checkpoint_id}.json"
        )

        write_json_atomic(
            manifest_path,
            manifest,
        )

        head_payload = {
            "ref_id": (
                "runtime:checkpoint:ref:HEAD"
            ),
            "checkpoint_id": checkpoint_id,
            "sequence": sequence,
            "manifest_path": str(
                manifest_path
            ),
            "manifest_digest": manifest[
                "digest"
            ],
            "tree_digest": manifest[
                "tree_digest"
            ],
            "updated_at": utc_now(),
        }

        head_payload[
            "digest"
        ] = digest(
            head_payload
        )

        write_json_atomic(
            HEAD_PATH,
            head_payload,
        )

        index = self.update_index(
            manifest
        )

        event = self.append_event(
            checkpoint_id,
            "create",
            {
                "manifest_digest": manifest[
                    "digest"
                ],
                "tree_digest": manifest[
                    "tree_digest"
                ],
                "record_count": manifest[
                    "record_count"
                ],
                "parent_checkpoint": (
                    parent_checkpoint
                ),
            },
        )

        return {
            "operation": "create",
            "passed": True,
            "checkpoint_id": checkpoint_id,
            "manifest_path": str(
                manifest_path
            ),
            "manifest_digest": manifest[
                "digest"
            ],
            "tree_digest": manifest[
                "tree_digest"
            ],
            "record_count": manifest[
                "record_count"
            ],
            "total_size": manifest[
                "total_size"
            ],
            "head": head_payload,
            "index_digest": index[
                "digest"
            ],
            "event": event,
        }

    def resolve_checkpoint(
        self,
        checkpoint_id: str,
    ) -> tuple[
        str,
        Path,
        dict[str, Any],
    ]:
        requested = checkpoint_id.strip()

        if requested in {
            "HEAD",
            "head",
            "@",
        }:
            head = load_json(
                HEAD_PATH,
                default={},
            )

            if not isinstance(
                head,
                dict,
            ):
                raise RuntimeCheckpointError(
                    "Checkpoint HEAD is missing"
                )

            requested = str(
                head.get(
                    "checkpoint_id",
                    "",
                )
            )

        if not requested:
            raise RuntimeCheckpointError(
                "Checkpoint ID is empty"
            )

        manifest_path = (
            MANIFEST_ROOT
            / f"{requested}.json"
        )

        manifest = load_json(
            manifest_path,
            default=None,
        )

        if not isinstance(
            manifest,
            dict,
        ):
            raise FileNotFoundError(
                requested
            )

        return (
            requested,
            manifest_path,
            manifest,
        )

    def verify_manifest(
        self,
        checkpoint_id: str,
        manifest: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues = []

        expected_manifest_digest = digest(
            {
                key: value
                for key, value
                in manifest.items()
                if key != "digest"
            }
        )

        if manifest.get(
            "digest"
        ) != expected_manifest_digest:
            issues.append(
                {
                    "code": (
                        "manifest_digest_mismatch"
                    ),
                    "checkpoint_id": (
                        checkpoint_id
                    ),
                    "expected": (
                        expected_manifest_digest
                    ),
                    "actual": manifest.get(
                        "digest"
                    ),
                }
            )

        records = manifest.get(
            "records",
            []
        )

        if not isinstance(
            records,
            list,
        ):
            issues.append(
                {
                    "code": (
                        "manifest_records_invalid"
                    ),
                    "checkpoint_id": (
                        checkpoint_id
                    ),
                }
            )

            return issues

        tree_projection = []

        for record in records:
            if not isinstance(
                record,
                dict,
            ):
                issues.append(
                    {
                        "code": (
                            "record_invalid"
                        ),
                        "checkpoint_id": (
                            checkpoint_id
                        ),
                    }
                )

                continue

            sha256 = str(
                record.get(
                    "sha256",
                    "",
                )
            )

            stored_object = object_path(
                sha256
            )

            if not stored_object.is_file():
                issues.append(
                    {
                        "code": (
                            "object_missing"
                        ),
                        "checkpoint_id": (
                            checkpoint_id
                        ),
                        "sha256": sha256,
                        "path": str(
                            stored_object
                        ),
                    }
                )

                continue

            actual_sha256 = file_digest(
                stored_object
            )

            if actual_sha256 != sha256:
                issues.append(
                    {
                        "code": (
                            "object_digest_mismatch"
                        ),
                        "checkpoint_id": (
                            checkpoint_id
                        ),
                        "path": str(
                            stored_object
                        ),
                        "expected": sha256,
                        "actual": actual_sha256,
                    }
                )

            tree_projection.append(
                {
                    "relative_path": (
                        record.get(
                            "relative_path"
                        )
                    ),
                    "sha256": sha256,
                    "size": record.get(
                        "size"
                    ),
                    "mode": record.get(
                        "mode"
                    ),
                }
            )

        expected_tree_digest = digest(
            tree_projection
        )

        if manifest.get(
            "tree_digest"
        ) != expected_tree_digest:
            issues.append(
                {
                    "code": (
                        "tree_digest_mismatch"
                    ),
                    "checkpoint_id": (
                        checkpoint_id
                    ),
                    "expected": (
                        expected_tree_digest
                    ),
                    "actual": manifest.get(
                        "tree_digest"
                    ),
                }
            )

        if manifest.get(
            "record_count"
        ) != len(
            records
        ):
            issues.append(
                {
                    "code": (
                        "record_count_mismatch"
                    ),
                    "checkpoint_id": (
                        checkpoint_id
                    ),
                    "expected": len(
                        records
                    ),
                    "actual": manifest.get(
                        "record_count"
                    ),
                }
            )

        return issues

    def verify(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        resolved_id, manifest_path, manifest = (
            self.resolve_checkpoint(
                checkpoint_id
            )
        )

        issues = self.verify_manifest(
            resolved_id,
            manifest,
        )

        payload = {
            "operation": "verify",
            "passed": not issues,
            "checkpoint_id": resolved_id,
            "manifest_path": str(
                manifest_path
            ),
            "manifest_digest": manifest.get(
                "digest"
            ),
            "tree_digest": manifest.get(
                "tree_digest"
            ),
            "record_count": manifest.get(
                "record_count"
            ),
            "issue_count": len(
                issues
            ),
            "issues": issues,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def verify_all(
        self,
    ) -> dict[str, Any]:
        manifests = []

        issues = []

        for manifest_path in sorted(
            MANIFEST_ROOT.glob(
                "*.json"
            )
        ):
            manifest = load_json(
                manifest_path,
                default=None,
            )

            if not isinstance(
                manifest,
                dict,
            ):
                issues.append(
                    {
                        "code": (
                            "manifest_invalid"
                        ),
                        "path": str(
                            manifest_path
                        ),
                    }
                )

                continue

            checkpoint_id = str(
                manifest.get(
                    "checkpoint_id",
                    manifest_path.stem,
                )
            )

            manifest_issues = (
                self.verify_manifest(
                    checkpoint_id,
                    manifest,
                )
            )

            manifests.append(
                {
                    "checkpoint_id": (
                        checkpoint_id
                    ),
                    "path": str(
                        manifest_path
                    ),
                    "passed": (
                        not manifest_issues
                    ),
                    "issue_count": len(
                        manifest_issues
                    ),
                    "manifest_digest": (
                        manifest.get(
                            "digest"
                        )
                    ),
                    "tree_digest": (
                        manifest.get(
                            "tree_digest"
                        )
                    ),
                }
            )

            issues.extend(
                manifest_issues
            )

        event_issues = self.verify_events()

        issues.extend(
            event_issues
        )

        payload = {
            "operation": "verify_all",
            "passed": not issues,
            "manifest_count": len(
                manifests
            ),
            "event_count": len(
                read_jsonl(
                    EVENT_LOG_PATH
                )
            ),
            "issue_count": len(
                issues
            ),
            "manifests": manifests,
            "issues": issues,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def verify_events(
        self,
    ) -> list[dict[str, Any]]:
        events = read_jsonl(
            EVENT_LOG_PATH
        )

        issues = []

        previous_digest = None

        for expected_sequence, event in enumerate(
            events,
            start=1,
        ):
            if event.get(
                "sequence"
            ) != expected_sequence:
                issues.append(
                    {
                        "code": (
                            "event_sequence_mismatch"
                        ),
                        "expected": (
                            expected_sequence
                        ),
                        "actual": event.get(
                            "sequence"
                        ),
                    }
                )

            if event.get(
                "previous_digest"
            ) != previous_digest:
                issues.append(
                    {
                        "code": (
                            "event_previous_digest_mismatch"
                        ),
                        "sequence": (
                            expected_sequence
                        ),
                        "expected": (
                            previous_digest
                        ),
                        "actual": event.get(
                            "previous_digest"
                        ),
                    }
                )

            expected_digest = digest(
                {
                    key: value
                    for key, value
                    in event.items()
                    if key != "digest"
                }
            )

            if event.get(
                "digest"
            ) != expected_digest:
                issues.append(
                    {
                        "code": (
                            "event_digest_mismatch"
                        ),
                        "sequence": (
                            expected_sequence
                        ),
                        "expected": (
                            expected_digest
                        ),
                        "actual": event.get(
                            "digest"
                        ),
                    }
                )

            previous_digest = event.get(
                "digest"
            )

        return issues

    def restore(
        self,
        checkpoint_id: str,
        *,
        destination: Path,
        overwrite: bool,
    ) -> dict[str, Any]:
        resolved_id, manifest_path, manifest = (
            self.resolve_checkpoint(
                checkpoint_id
            )
        )

        issues = self.verify_manifest(
            resolved_id,
            manifest,
        )

        if issues:
            raise RuntimeCheckpointError(
                f"Checkpoint verification failed: "
                f"{resolved_id}"
            )

        destination = normalize_path(
            destination
        )

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        restored = []

        skipped = []

        for record in manifest[
            "records"
        ]:
            relative = Path(
                record[
                    "relative_path"
                ]
            )

            target = (
                destination
                / relative
            )

            stored_object = object_path(
                record[
                    "sha256"
                ]
            )

            if target.exists() and not overwrite:
                skipped.append(
                    {
                        "relative_path": str(
                            relative
                        ),
                        "reason": (
                            "destination_exists"
                        ),
                    }
                )

                continue

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".restore",
                dir=str(
                    target.parent
                ),
            )

            temporary_path = Path(
                temporary_name
            )

            try:
                with os.fdopen(
                    descriptor,
                    "wb",
                ) as output_handle:
                    with stored_object.open(
                        "rb"
                    ) as input_handle:
                        shutil.copyfileobj(
                            input_handle,
                            output_handle,
                            length=1024 * 1024,
                        )

                    output_handle.flush()

                    os.fsync(
                        output_handle.fileno()
                    )

                actual_sha256 = file_digest(
                    temporary_path
                )

                if actual_sha256 != record[
                    "sha256"
                ]:
                    raise RuntimeCheckpointError(
                        f"Restored file digest mismatch: "
                        f"{relative}"
                    )

                os.chmod(
                    temporary_path,
                    int(
                        record.get(
                            "mode",
                            0o644,
                        )
                    ),
                )

                os.replace(
                    temporary_path,
                    target,
                )

            finally:
                if temporary_path.exists():
                    temporary_path.unlink()

            restored.append(
                {
                    "relative_path": str(
                        relative
                    ),
                    "destination": str(
                        target
                    ),
                    "sha256": record[
                        "sha256"
                    ],
                    "size": record[
                        "size"
                    ],
                }
            )

        event = self.append_event(
            resolved_id,
            "restore",
            {
                "destination": str(
                    destination
                ),
                "overwrite": overwrite,
                "restored_count": len(
                    restored
                ),
                "skipped_count": len(
                    skipped
                ),
            },
        )

        payload = {
            "operation": "restore",
            "passed": True,
            "checkpoint_id": resolved_id,
            "manifest_path": str(
                manifest_path
            ),
            "destination": str(
                destination
            ),
            "overwrite": overwrite,
            "restored_count": len(
                restored
            ),
            "skipped_count": len(
                skipped
            ),
            "restored": restored,
            "skipped": skipped,
            "event": event,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def diff(
        self,
        left_id: str,
        right_id: str,
    ) -> dict[str, Any]:
        left_resolved, _, left = (
            self.resolve_checkpoint(
                left_id
            )
        )

        right_resolved, _, right = (
            self.resolve_checkpoint(
                right_id
            )
        )

        left_records = {
            record[
                "relative_path"
            ]: record
            for record in left.get(
                "records",
                []
            )
            if isinstance(
                record,
                dict,
            )
        }

        right_records = {
            record[
                "relative_path"
            ]: record
            for record in right.get(
                "records",
                []
            )
            if isinstance(
                record,
                dict,
            )
        }

        left_paths = set(
            left_records
        )

        right_paths = set(
            right_records
        )

        added = []

        removed = []

        modified = []

        unchanged = []

        for relative_path in sorted(
            right_paths - left_paths
        ):
            added.append(
                right_records[
                    relative_path
                ]
            )

        for relative_path in sorted(
            left_paths - right_paths
        ):
            removed.append(
                left_records[
                    relative_path
                ]
            )

        for relative_path in sorted(
            left_paths & right_paths
        ):
            left_record = left_records[
                relative_path
            ]

            right_record = right_records[
                relative_path
            ]

            if (
                left_record.get(
                    "sha256"
                )
                == right_record.get(
                    "sha256"
                )
                and left_record.get(
                    "mode"
                )
                == right_record.get(
                    "mode"
                )
            ):
                unchanged.append(
                    {
                        "relative_path": (
                            relative_path
                        ),
                        "sha256": (
                            left_record.get(
                                "sha256"
                            )
                        ),
                    }
                )

                continue

            modified.append(
                {
                    "relative_path": (
                        relative_path
                    ),
                    "left": left_record,
                    "right": right_record,
                }
            )

        payload = {
            "operation": "diff",
            "passed": True,
            "left": left_resolved,
            "right": right_resolved,
            "added_count": len(
                added
            ),
            "removed_count": len(
                removed
            ),
            "modified_count": len(
                modified
            ),
            "unchanged_count": len(
                unchanged
            ),
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def list_checkpoints(
        self,
    ) -> dict[str, Any]:
        index = load_json(
            INDEX_PATH,
            default={},
        )

        head = load_json(
            HEAD_PATH,
            default={},
        )

        if not isinstance(
            index,
            dict,
        ):
            index = {}

        if not isinstance(
            head,
            dict,
        ):
            head = {}

        records = index.get(
            "records",
            {}
        )

        if not isinstance(
            records,
            dict,
        ):
            records = {}

        payload = {
            "operation": "list",
            "passed": True,
            "checkpoint_count": len(
                records
            ),
            "head": head,
            "records": [
                records[
                    key
                ]
                for key in sorted(
                    records,
                    key=lambda checkpoint_id: (
                        int(
                            records[
                                checkpoint_id
                            ].get(
                                "sequence",
                                0,
                            )
                        ),
                        checkpoint_id,
                    ),
                    reverse=True,
                )
            ],
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def show(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        resolved_id, manifest_path, manifest = (
            self.resolve_checkpoint(
                checkpoint_id
            )
        )

        return {
            "operation": "show",
            "passed": True,
            "checkpoint_id": resolved_id,
            "manifest_path": str(
                manifest_path
            ),
            "manifest": manifest,
        }

    def garbage_collect(
        self,
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        referenced = set()

        manifest_count = 0

        for manifest_path in sorted(
            MANIFEST_ROOT.glob(
                "*.json"
            )
        ):
            manifest = load_json(
                manifest_path,
                default=None,
            )

            if not isinstance(
                manifest,
                dict,
            ):
                continue

            manifest_count += 1

            for record in manifest.get(
                "records",
                []
            ):
                if not isinstance(
                    record,
                    dict,
                ):
                    continue

                sha256 = str(
                    record.get(
                        "sha256",
                        "",
                    )
                )

                if sha256:
                    referenced.add(
                        sha256
                    )

        unreferenced = []

        removed = []

        retained = []

        for path in sorted(
            OBJECT_ROOT.rglob(
                "*"
            )
        ):
            if not path.is_file():
                continue

            relative = path.relative_to(
                OBJECT_ROOT
            )

            if len(
                relative.parts
            ) != 2:
                continue

            sha256 = (
                relative.parts[
                    0
                ]
                + relative.parts[
                    1
                ]
            )

            record = {
                "sha256": sha256,
                "path": str(
                    path
                ),
                "size": path.stat().st_size,
            }

            if sha256 in referenced:
                retained.append(
                    record
                )

                continue

            unreferenced.append(
                record
            )

            if not dry_run:
                os.chmod(
                    path,
                    0o644,
                )

                path.unlink()

                removed.append(
                    record
                )

        if not dry_run:
            for directory in sorted(
                (
                    path
                    for path in OBJECT_ROOT.iterdir()
                    if path.is_dir()
                ),
                reverse=True,
            ):
                try:
                    directory.rmdir()

                except OSError:
                    pass

        payload = {
            "operation": "garbage_collect",
            "passed": True,
            "dry_run": dry_run,
            "manifest_count": manifest_count,
            "referenced_count": len(
                referenced
            ),
            "retained_count": len(
                retained
            ),
            "unreferenced_count": len(
                unreferenced
            ),
            "removed_count": len(
                removed
            ),
            "unreferenced": unreferenced,
            "removed": removed,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def print_result(
    payload: Any,
) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    create_parser = subparsers.add_parser(
        "create"
    )

    create_parser.add_argument(
        "--label"
    )

    create_parser.add_argument(
        "--target",
        action="append",
        default=[],
    )

    verify_parser = subparsers.add_parser(
        "verify"
    )

    verify_parser.add_argument(
        "checkpoint_id",
        nargs="?",
        default="HEAD",
    )

    subparsers.add_parser(
        "verify-all"
    )

    restore_parser = subparsers.add_parser(
        "restore"
    )

    restore_parser.add_argument(
        "checkpoint_id"
    )

    restore_parser.add_argument(
        "--destination",
        default=str(
            LEXICON_ROOT
        ),
    )

    restore_parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    diff_parser = subparsers.add_parser(
        "diff"
    )

    diff_parser.add_argument(
        "left"
    )

    diff_parser.add_argument(
        "right"
    )

    show_parser = subparsers.add_parser(
        "show"
    )

    show_parser.add_argument(
        "checkpoint_id",
        nargs="?",
        default="HEAD",
    )

    subparsers.add_parser(
        "list"
    )

    gc_parser = subparsers.add_parser(
        "gc"
    )

    gc_parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    checkpoint = RuntimeCheckpoint()

    if args.command == "create":
        result = checkpoint.create(
            label=args.label,
            supplied_targets=args.target,
        )

    elif args.command == "verify":
        result = checkpoint.verify(
            args.checkpoint_id
        )

    elif args.command == "verify-all":
        result = checkpoint.verify_all()

    elif args.command == "restore":
        result = checkpoint.restore(
            args.checkpoint_id,
            destination=Path(
                args.destination
            ),
            overwrite=args.overwrite,
        )

    elif args.command == "diff":
        result = checkpoint.diff(
            args.left,
            args.right,
        )

    elif args.command == "show":
        result = checkpoint.show(
            args.checkpoint_id
        )

    elif args.command == "list":
        result = checkpoint.list_checkpoints()

    elif args.command == "gc":
        result = checkpoint.garbage_collect(
            dry_run=(
                not args.apply
            ),
        )

    else:
        raise RuntimeCheckpointError(
            args.command
        )

    print_result(
        result
    )

    return (
        0
        if result.get(
            "passed",
            True,
        )
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        RuntimeCheckpointError,
        FileNotFoundError,
    ) as error:
        print_result(
            {
                "operation": "error",
                "passed": False,
                "error": type(
                    error
                ).__name__,
                "message": str(
                    error
                ),
            }
        )

        raise SystemExit(
            1
        )
