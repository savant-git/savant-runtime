#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

TRANSACTION_ROOT = (
    RUNTIME_ROOT
    / "transactions"
)

ACTIVE_ROOT = (
    TRANSACTION_ROOT
    / "active"
)

FAILED_ROOT = (
    TRANSACTION_ROOT
    / "failed"
)

RECOVERY_REPORT_PATH = (
    TRANSACTION_ROOT
    / "runtime_recovery_report.json"
)


class RuntimeRecoveryError(
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


class RuntimeRecovery:

    def scan(
        self,
    ) -> dict[str, Any]:
        ACTIVE_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        records = []

        for transaction_path in sorted(
            ACTIVE_ROOT.iterdir()
        ):
            if not transaction_path.is_dir():
                continue

            metadata_path = (
                transaction_path
                / "transaction.json"
            )

            metadata = load_json(
                metadata_path,
                default={},
            )

            if not isinstance(
                metadata,
                dict,
            ):
                metadata = {}

            snapshot_path = (
                transaction_path
                / "snapshot"
            )

            snapshot_manifest_path = (
                transaction_path
                / "snapshot_manifest.json"
            )

            records.append(
                {
                    "transaction_id": (
                        transaction_path.name
                    ),
                    "path": str(
                        transaction_path
                    ),
                    "metadata_exists": (
                        metadata_path.is_file()
                    ),
                    "state": metadata.get(
                        "state"
                    ),
                    "action": metadata.get(
                        "action"
                    ),
                    "subsystems": metadata.get(
                        "subsystems",
                        [],
                    ),
                    "created_at": metadata.get(
                        "created_at"
                    ),
                    "updated_at": metadata.get(
                        "updated_at"
                    ),
                    "snapshot_exists": (
                        snapshot_path.is_dir()
                    ),
                    "snapshot_manifest_exists": (
                        snapshot_manifest_path.is_file()
                    ),
                    "result_count": len(
                        metadata.get(
                            "results",
                            [],
                        )
                    )
                    if isinstance(
                        metadata.get(
                            "results",
                            [],
                        ),
                        list,
                    )
                    else 0,
                    "recoverable": (
                        metadata_path.is_file()
                        and snapshot_path.is_dir()
                        and snapshot_manifest_path.is_file()
                    ),
                }
            )

        payload = {
            "operation": "scan",
            "passed": True,
            "timestamp": utc_now(),
            "active_count": len(
                records
            ),
            "recoverable_count": len(
                [
                    record
                    for record in records
                    if record[
                        "recoverable"
                    ]
                ]
            ),
            "records": records,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        write_json_atomic(
            RECOVERY_REPORT_PATH,
            payload,
        )

        return payload

    def mark_failed(
        self,
        transaction_id: str,
        reason: str,
    ) -> dict[str, Any]:
        source = (
            ACTIVE_ROOT
            / transaction_id
        )

        if not source.is_dir():
            raise FileNotFoundError(
                transaction_id
            )

        metadata_path = (
            source
            / "transaction.json"
        )

        metadata = load_json(
            metadata_path,
            default={},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        failure = {
            "failed_at": utc_now(),
            "reason": reason,
            "recovery_action": (
                "mark_failed"
            ),
        }

        failure[
            "digest"
        ] = digest(
            failure
        )

        metadata[
            "state"
        ] = "failed"

        metadata[
            "failure"
        ] = failure

        metadata[
            "updated_at"
        ] = utc_now()

        metadata[
            "digest"
        ] = digest(
            {
                key: value
                for key, value
                in metadata.items()
                if key != "digest"
            }
        )

        write_json_atomic(
            metadata_path,
            metadata,
        )

        FAILED_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            FAILED_ROOT
            / transaction_id
        )

        os.replace(
            source,
            destination,
        )

        return {
            "operation": "mark_failed",
            "passed": True,
            "transaction_id": (
                transaction_id
            ),
            "state": "failed",
            "path": str(
                destination
            ),
            "failure": failure,
        }


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

    subparsers.add_parser(
        "scan"
    )

    fail_parser = subparsers.add_parser(
        "mark-failed"
    )

    fail_parser.add_argument(
        "transaction_id"
    )

    fail_parser.add_argument(
        "--reason",
        default=(
            "orphaned active transaction"
        ),
    )

    args = parser.parse_args()

    recovery = RuntimeRecovery()

    if args.command == "scan":
        result = recovery.scan()

    elif args.command == "mark-failed":
        result = recovery.mark_failed(
            args.transaction_id,
            args.reason,
        )

    else:
        raise RuntimeRecoveryError(
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
        RuntimeRecoveryError,
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
