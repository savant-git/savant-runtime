#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable


runtime_root = Path(
    "/root/savant-runtime"
)

adapter_dir = (
    runtime_root
    / "runtime"
    / "adapters"
)

if str(
    adapter_dir
) not in sys.path:
    sys.path.insert(
        0,
        str(
            adapter_dir
        ),
    )


from aws_s3_boundary import S3Boundary
from aws_s3_boundary import S3BoundaryError


version = "1.1.0"

receipt_root = (
    runtime_root
    / "runtime"
    / "receipts"
    / "wax"
)


class WaxError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class UploadItem:
    source: Path
    key: str
    size: int
    sha256: str


def now_utc() -> str:
    return (
        dt.datetime.now(
            dt.timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def stamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
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


def semantic_digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def invocation_cwd() -> Path:
    return Path.cwd().resolve()


def require_source(
    raw: str,
    cwd: Path,
) -> Path:
    source = Path(
        raw
    )

    if not source.is_absolute():
        source = (
            cwd
            / source
        )

    source = source.absolute()

    if source.is_symlink():
        raise WaxError(
            "symbolic-link sources are not admitted: "
            f"{source}"
        )

    try:
        resolved = source.resolve(
            strict=True
        )

    except FileNotFoundError as exc:
        raise WaxError(
            f"source does not exist: {raw}"
        ) from exc

    if not resolved.is_file():
        raise WaxError(
            "wax currently admits files only: "
            f"{resolved}"
        )

    return resolved


def plan(
    targets: Iterable[str],
    cwd: Path,
) -> list[UploadItem]:
    result: list[
        UploadItem
    ] = []

    keys: dict[
        str,
        Path,
    ] = {}

    for raw in targets:
        source = require_source(
            raw,
            cwd,
        )

        key = source.name

        if not key:
            raise WaxError(
                "source has no basename: "
                f"{source}"
            )

        prior = keys.get(
            key
        )

        if (
            prior is not None
            and prior != source
        ):
            raise WaxError(
                "multiple sources map to "
                f"bucket-root key {key!r}: "
                f"{prior} and {source}"
            )

        keys[
            key
        ] = source

        result.append(
            UploadItem(
                source=source,
                key=key,
                size=(
                    source
                    .stat()
                    .st_size
                ),
                sha256=sha256_file(
                    source
                ),
            )
        )

    return result


def upload_one(
    item: UploadItem,
    s3: S3Boundary,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "source": str(
                item.source
            ),
            "key": item.key,
            "size": item.size,
            "sha256": item.sha256,
            "status": "would-upload",
        }

    s3.upload(
        str(
            item.source
        ),
        item.key,
        item.sha256,
    )

    remote = s3.head(
        item.key
    )

    if remote is None:
        raise WaxError(
            "uploaded object cannot be read back: "
            f"s3://{s3.bucket}/{item.key}"
        )

    if remote.size != item.size:
        raise WaxError(
            "remote size mismatch for "
            f"s3://{s3.bucket}/{item.key}: "
            f"expected {item.size}, "
            f"got {remote.size}"
        )

    hash_verified: (
        bool | None
    ) = None

    if remote.sha256 is not None:
        hash_verified = (
            remote.sha256
            == item.sha256
        )

    if not hash_verified:
        raise WaxError(
            "remote SHA-256 metadata mismatch for "
            f"s3://{s3.bucket}/{item.key}"
        )

    return {
        "source": str(
            item.source
        ),
        "key": item.key,
        "size": item.size,
        "sha256": item.sha256,
        "remote_sha256": remote.sha256,
        "hash_verified": hash_verified,
        "status": "uploaded",
    }


def write_receipt(
    cwd: Path,
    results: list[
        dict[str, Any]
    ],
    dry_run: bool,
    bucket: str,
) -> Path:
    semantic = {
        "schema":
            "savant://utility/tactic/wax/receipt/1.1.0",
        "version":
            version,
        "operation":
            "wax",
        "bucket":
            bucket,
        "cwd":
            str(
                cwd
            ),
        "dry_run":
            dry_run,
        "results":
            results,
        "authority_effect":
            "none",
    }

    payload = dict(
        semantic
    )

    payload[
        "occurred_at"
    ] = now_utc()

    payload[
        "semantic_digest"
    ] = semantic_digest(
        semantic
    )

    receipt_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        receipt_root
        / (
            stamp()
            + "__"
            + payload[
                "semantic_digest"
            ][
                :16
            ]
            + ".json"
        )
    )

    temporary = path.with_name(
        "."
        + path.name
        + ".tmp-"
        + str(
            os.getpid()
        )
    )

    with temporary.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

        handle.write(
            "\n"
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    os.chmod(
        temporary,
        0o600,
    )

    os.replace(
        temporary,
        path,
    )

    return path


def selftest(
    s3: S3Boundary,
) -> dict[
    str,
    Any,
]:
    digest_a = semantic_digest(
        {
            "a": 1,
            "b": 2,
        }
    )

    digest_b = semantic_digest(
        {
            "b": 2,
            "a": 1,
        }
    )

    cwd = invocation_cwd()

    checks = {
        "bucket_configured":
            bool(
                s3.bucket
            ),
        "global_invocation":
            cwd.is_absolute(),
        "deterministic_digest":
            digest_a
            == digest_b,
        "configured_prefix_not_applied":
            True,
    }

    return {
        "schema":
            "savant://utility/tactic/wax/selftest/1.1.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="wax",
        description=(
            "Upload explicitly selected files "
            "from any invocation directory "
            "to the root of the configured "
            "Savant S3 bucket."
        ),
    )

    parser.add_argument(
        "targets",
        nargs="*",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
    )

    parser.add_argument(
        "--status",
        action="store_true",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    args = parser.parse_args()

    cwd = invocation_cwd()

    s3 = S3Boundary()
    bucket = s3.bucket

    if args.selftest:
        payload = selftest(
            s3
        )

        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )

        return (
            0
            if payload[
                "ok"
            ]
            else 1
        )

    if args.status:
        (
            reachable,
            error,
        ) = s3.status()

        payload = {
            "schema":
                "savant://utility/tactic/wax/status/1.1.0",
            "bucket":
                bucket,
            "cwd":
                str(
                    cwd
                ),
            "bucket_reachable":
                reachable,
            "error":
                error,
        }

        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )

        return (
            0
            if reachable
            else 1
        )

    if not args.targets:
        parser.error(
            "at least one file is required"
        )

    items = plan(
        args.targets,
        cwd,
    )

    results = [
        upload_one(
            item,
            s3,
            dry_run=args.dry_run,
        )
        for item
        in items
    ]

    receipt = write_receipt(
        cwd,
        results,
        args.dry_run,
        bucket,
    )

    payload = {
        "schema":
            "savant://utility/tactic/wax/result/1.1.0",
        "bucket":
            bucket,
        "cwd":
            str(
                cwd
            ),
        "results":
            results,
        "receipt":
            str(
                receipt
            ),
    }

    if args.json_output:
        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )

    else:
        for row in results:
            print(
                "["
                + row[
                    "status"
                ].upper()
                + "] "
                + row[
                    "source"
                ]
                + " -> "
                + f"s3://{bucket}/"
                + row[
                    "key"
                ]
            )

        print(
            f"[RECEIPT] {receipt}"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        WaxError,
        S3BoundaryError,
    ) as exc:
        print(
            f"wax: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
