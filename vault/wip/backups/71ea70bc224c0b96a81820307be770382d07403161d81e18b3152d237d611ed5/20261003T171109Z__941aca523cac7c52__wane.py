#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import sys
import tempfile

from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
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


version = "1.0.0"

receipt_root = (
    runtime_root
    / "runtime"
    / "receipts"
    / "wane"
)

glob_chars = "*?["


class WaneError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class DownloadItem:
    key: str
    destination: Path
    size: int
    sha256: str | None


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


def require_runtime_cwd() -> Path:
    cwd = Path.cwd().resolve()
    root = runtime_root.resolve()

    if (
        cwd != root
        and root not in cwd.parents
    ):
        raise WaneError(
            "wane must be run from inside "
            f"{runtime_root}; "
            f"current directory is {cwd}"
        )

    return cwd


def normalize_target(
    raw: str,
    bucket: str,
) -> str:
    value = raw.strip()

    if not value:
        raise WaneError(
            "empty S3 target"
        )

    if value.startswith(
        "s3://"
    ):
        bucket_root = (
            f"s3://{bucket}"
        )

        prefix = (
            bucket_root
            + "/"
        )

        if value == bucket_root:
            return ""

        if not value.startswith(
            prefix
        ):
            raise WaneError(
                "wane is bound to "
                f"{bucket_root}; "
                f"received {value}"
            )

        value = value[
            len(
                prefix
            ):
        ]

    value = value.lstrip(
        "/"
    )

    if "\x00" in value:
        raise WaneError(
            "S3 key contains NUL"
        )

    if any(
        part in {
            ".",
            "..",
        }
        for part
        in PurePosixPath(
            value
        ).parts
    ):
        raise WaneError(
            f"unsafe S3 key: {raw}"
        )

    return value


def first_glob_index(
    value: str,
) -> int | None:

    indices = [
        value.find(
            character
        )
        for character
        in glob_chars
        if character in value
    ]

    return (
        min(
            indices
        )
        if indices
        else None
    )


def safe_destination(
    cwd: Path,
    relative: str,
) -> Path:

    parts = PurePosixPath(
        relative
    ).parts

    if (
        not parts
        or any(
            part in {
                ".",
                "..",
            }
            for part
            in parts
        )
    ):
        raise WaneError(
            "unsafe relative destination: "
            f"{relative}"
        )

    destination = cwd.joinpath(
        *parts
    )

    parent = (
        destination
        .parent
        .resolve(
            strict=False
        )
    )

    cwd_resolved = (
        cwd.resolve()
    )

    if (
        parent != cwd_resolved
        and cwd_resolved
        not in parent.parents
    ):
        raise WaneError(
            "destination escapes invocation directory: "
            f"{destination}"
        )

    return destination


def plan(
    targets: Iterable[str],
    cwd: Path,
    s3: S3Boundary,
) -> list[DownloadItem]:

    bucket = s3.bucket

    result: list[
        DownloadItem
    ] = []

    destinations: dict[
        Path,
        str,
    ] = {}

    for raw in targets:
        target = normalize_target(
            raw,
            bucket,
        )

        if not target:
            raise WaneError(
                "bucket-root download requires "
                "an explicit key, prefix, or glob"
            )

        glob_index = (
            first_glob_index(
                target
            )
        )

        if glob_index is not None:
            slash = target.rfind(
                "/",
                0,
                glob_index,
            )

            base_prefix = (
                target[
                    :slash + 1
                ]
                if slash >= 0
                else ""
            )

            matches = [
                obj
                for obj
                in s3.iter_objects(
                    base_prefix
                )
                if fnmatch.fnmatchcase(
                    obj.key,
                    target,
                )
            ]

            if not matches:
                raise WaneError(
                    f"no objects match {raw!r}"
                )

            for obj in matches:
                relative = obj.key[
                    len(
                        base_prefix
                    ):
                ].lstrip(
                    "/"
                )

                destination = safe_destination(
                    cwd,
                    relative,
                )

                head = (
                    s3.head(
                        obj.key
                    )
                    or obj
                )

                result.append(
                    DownloadItem(
                        key=obj.key,
                        destination=destination,
                        size=head.size,
                        sha256=head.sha256,
                    )
                )

        elif target.endswith(
            "/"
        ):
            matches = list(
                s3.iter_objects(
                    target
                )
            )

            if not matches:
                raise WaneError(
                    "prefix contains no objects: "
                    f"{raw!r}"
                )

            for obj in matches:
                relative = obj.key[
                    len(
                        target
                    ):
                ].lstrip(
                    "/"
                )

                destination = safe_destination(
                    cwd,
                    relative,
                )

                head = (
                    s3.head(
                        obj.key
                    )
                    or obj
                )

                result.append(
                    DownloadItem(
                        key=obj.key,
                        destination=destination,
                        size=head.size,
                        sha256=head.sha256,
                    )
                )

        else:
            head = s3.head(
                target,
                allow_missing=True,
            )

            if head is None:
                raise WaneError(
                    "object not found: "
                    f"s3://{bucket}/{target}"
                )

            basename = (
                PurePosixPath(
                    target
                ).name
            )

            if not basename:
                raise WaneError(
                    "object key has no filename: "
                    f"{target}"
                )

            destination = (
                safe_destination(
                    cwd,
                    basename,
                )
            )

            result.append(
                DownloadItem(
                    key=target,
                    destination=destination,
                    size=head.size,
                    sha256=head.sha256,
                )
            )

    for item in result:
        prior = destinations.get(
            item.destination
        )

        if (
            prior is not None
            and prior != item.key
        ):
            raise WaneError(
                "multiple objects map to "
                f"{item.destination}: "
                f"{prior} and "
                f"{item.key}"
            )

        destinations[
            item.destination
        ] = item.key

    return result


def download_one(
    item: DownloadItem,
    s3: S3Boundary,
    *,
    dry_run: bool,
    no_clobber: bool,
    verify: bool,
) -> dict[str, Any]:

    bucket = s3.bucket

    if (
        item.destination.exists()
        and no_clobber
    ):
        raise WaneError(
            "destination exists: "
            f"{item.destination}"
        )

    if dry_run:
        return {
            "key":
                item.key,
            "destination":
                str(
                    item.destination
                ),
            "size":
                item.size,
            "remote_sha256":
                item.sha256,
            "status":
                "would-download",
        }

    item.destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        file_descriptor,
        temporary_name,
    ) = tempfile.mkstemp(
        prefix=(
            "."
            + item.destination.name
            + ".wane-"
        ),
        dir=str(
            item.destination.parent
        ),
    )

    os.close(
        file_descriptor
    )

    temporary = Path(
        temporary_name
    )

    try:
        s3.download(
            item.key,
            str(
                temporary
            ),
        )

        actual_size = (
            temporary
            .stat()
            .st_size
        )

        if actual_size != item.size:
            raise WaneError(
                "size mismatch for "
                f"s3://{bucket}/{item.key}: "
                f"expected {item.size}, "
                f"got {actual_size}"
            )

        actual_hash = (
            sha256_file(
                temporary
            )
        )

        verified: (
            bool | None
        ) = None

        if item.sha256 is not None:
            verified = (
                actual_hash
                == item.sha256
            )

            if (
                verify
                and not verified
            ):
                raise WaneError(
                    "SHA-256 mismatch for "
                    f"s3://{bucket}/{item.key}"
                )

        os.replace(
            temporary,
            item.destination,
        )

        return {
            "key":
                item.key,
            "destination":
                str(
                    item.destination
                ),
            "size":
                actual_size,
            "sha256":
                actual_hash,
            "remote_sha256":
                item.sha256,
            "hash_verified":
                verified,
            "status":
                "downloaded",
        }

    finally:
        if temporary.exists():
            temporary.unlink()


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
            "savant://utility/tactic/wane/receipt/1.0.0",
        "version":
            version,
        "operation":
            "wane",
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
    bucket = s3.bucket

    wrong_bucket = False
    traversal = False

    try:
        normalize_target(
            "s3://other-bucket/a.zip",
            bucket,
        )

    except WaneError:
        wrong_bucket = True

    try:
        normalize_target(
            "../secret",
            bucket,
        )

    except WaneError:
        traversal = True

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

    checks = {
        "bucket_configured":
            bool(
                bucket
            ),
        "wrong_bucket_rejected":
            wrong_bucket,
        "traversal_rejected":
            traversal,
        "deterministic_digest":
            digest_a
            == digest_b,
    }

    return {
        "schema":
            "savant://utility/tactic/wane/selftest/1.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="wane",
        description=(
            "Download objects from the configured "
            "Savant S3 bucket into the directory "
            "where wane is invoked."
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
        "--no-clobber",
        action="store_true",
    )

    parser.add_argument(
        "--no-verify",
        action="store_true",
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

    cwd = require_runtime_cwd()

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
                "savant://utility/tactic/wane/status/1.0.0",
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
            "at least one key, prefix, or glob is required"
        )

    items = plan(
        args.targets,
        cwd,
        s3,
    )

    results = [
        download_one(
            item,
            s3,
            dry_run=args.dry_run,
            no_clobber=(
                args.no_clobber
            ),
            verify=(
                not args.no_verify
            ),
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
            "savant://utility/tactic/wane/result/1.0.0",
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
                + f"s3://{bucket}/"
                + row[
                    "key"
                ]
                + " -> "
                + row[
                    "destination"
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
        WaneError,
        S3BoundaryError,
    ) as exc:
        print(
            f"wane: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
