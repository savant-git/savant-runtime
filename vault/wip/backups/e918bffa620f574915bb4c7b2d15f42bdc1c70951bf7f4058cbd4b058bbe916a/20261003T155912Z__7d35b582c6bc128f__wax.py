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


from aws_s3_boundary import BUCKET
from aws_s3_boundary import S3Boundary
from aws_s3_boundary import S3BoundaryError


version = "1.0.0"

receipt_root = (
    runtime_root
    / "runtime"
    / "receipts"
    / "wax"
)

sensitive_names = {
    ".env",
    "credentials",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
}

sensitive_suffixes = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


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


def require_runtime_cwd() -> Path:
    cwd = Path.cwd().resolve()
    root = runtime_root.resolve()

    if (
        cwd != root
        and root not in cwd.parents
    ):
        raise WaxError(
            "wax must be run from inside "
            f"{runtime_root}; "
            f"current directory is {cwd}"
        )

    return cwd


def require_runtime_source(
    path: Path,
) -> Path:
    resolved = path.resolve(
        strict=True
    )

    root = runtime_root.resolve()

    if (
        resolved != root
        and root not in resolved.parents
    ):
        raise WaxError(
            "source escapes "
            f"{runtime_root}: "
            f"{resolved}"
        )

    return resolved


def sensitive(
    path: Path,
) -> bool:
    lower_parts = {
        part.lower()
        for part
        in path.parts
    }

    if (
        ".aws"
        in lower_parts
        or "secrets"
        in lower_parts
    ):
        return True

    name = path.name.lower()

    return (
        name.startswith(
            ".env"
        )
        or name
        in sensitive_names
        or any(
            name.endswith(
                suffix
            )
            for suffix
            in sensitive_suffixes
        )
    )


def files_for_source(
    source: Path,
    allow_sensitive: bool,
) -> list[Path]:

    source = (
        require_runtime_source(
            source
        )
    )

    if source.is_symlink():
        raise WaxError(
            "symlink upload is refused: "
            f"{source}"
        )

    if source.is_file():
        if (
            sensitive(
                source
            )
            and not allow_sensitive
        ):
            raise WaxError(
                "sensitive-looking file refused: "
                f"{source}"
            )

        return [
            source
        ]

    if not source.is_dir():
        raise WaxError(
            "not a file or directory: "
            f"{source}"
        )

    files: list[
        Path
    ] = []

    for path in sorted(
        source.rglob(
            "*"
        )
    ):
        if path.is_symlink():
            raise WaxError(
                "symlink inside upload tree is refused: "
                f"{path}"
            )

        if not path.is_file():
            continue

        if (
            sensitive(
                path
            )
            and not allow_sensitive
        ):
            raise WaxError(
                "sensitive-looking file inside upload tree refused: "
                f"{path}"
            )

        files.append(
            path
        )

    return files


def plan(
    inputs: Iterable[str],
    allow_sensitive: bool,
) -> list[UploadItem]:

    result: list[
        UploadItem
    ] = []

    seen: dict[
        str,
        Path,
    ] = {}

    for raw in inputs:
        candidate = Path(
            raw
        ).expanduser()

        if not candidate.is_absolute():
            candidate = (
                Path.cwd()
                / candidate
            )

        source = (
            require_runtime_source(
                candidate
            )
        )

        files = files_for_source(
            source,
            allow_sensitive,
        )

        if source.is_file():
            mapping = [
                (
                    files[0],
                    files[0].name,
                )
            ]

        else:
            mapping = [
                (
                    path,
                    (
                        f"{source.name}/"
                        f"{path.relative_to(source).as_posix()}"
                    ),
                )
                for path
                in files
            ]

        for (
            file_path,
            key,
        ) in mapping:
            previous = seen.get(
                key
            )

            if (
                previous
                is not None
                and previous
                != file_path
            ):
                raise WaxError(
                    "upload-key collision for "
                    f"{key!r}: "
                    f"{previous} and "
                    f"{file_path}"
                )

            seen[
                key
            ] = file_path

            result.append(
                UploadItem(
                    source=file_path,
                    key=key,
                    size=(
                        file_path
                        .stat()
                        .st_size
                    ),
                    sha256=(
                        sha256_file(
                            file_path
                        )
                    ),
                )
            )

    if not result:
        raise WaxError(
            "no regular files found to upload"
        )

    return result


def write_receipt(
    cwd: Path,
    results: list[
        dict[str, Any]
    ],
    dry_run: bool,
) -> Path:

    semantic = {
        "schema":
            "savant://utility/tactic/wax/receipt/1.0.0",
        "version":
            version,
        "operation":
            "wax",
        "bucket":
            BUCKET,
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


def selftest() -> dict[
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

    checks = {
        "bucket":
            BUCKET
            == "savant-ai-cluster",
        "runtime_root_absolute":
            runtime_root.is_absolute(),
        "deterministic_digest":
            digest_a
            == digest_b,
        "sensitive_env":
            sensitive(
                Path(
                    "/root/savant-runtime/.env"
                )
            ),
        "ordinary_zip":
            not sensitive(
                Path(
                    "/root/savant-runtime/archive.zip"
                )
            ),
    }

    return {
        "schema":
            "savant://utility/tactic/wax/selftest/1.0.0",
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
            "Upload Savant runtime files "
            "to the root of "
            "s3://savant-ai-cluster."
        ),
    )

    parser.add_argument(
        "sources",
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
        "--allow-sensitive",
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

    if args.selftest:
        payload = selftest()

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

    cwd = require_runtime_cwd()

    s3 = S3Boundary()

    if args.status:
        (
            reachable,
            error,
        ) = s3.status()

        payload = {
            "schema":
                "savant://utility/tactic/wax/status/1.0.0",
            "bucket":
                BUCKET,
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

    if not args.sources:
        parser.error(
            "at least one source is required"
        )

    items = plan(
        args.sources,
        args.allow_sensitive,
    )

    results: list[
        dict[str, Any]
    ] = []

    for item in items:
        current = s3.head(
            item.key,
            allow_missing=True,
        )

        if (
            current is not None
            and current.size
            == item.size
            and current.sha256
            == item.sha256
        ):
            status = (
                "unchanged"
            )

        elif args.dry_run:
            status = (
                "would-upload"
            )

        else:
            s3.upload(
                str(
                    item.source
                ),
                item.key,
                item.sha256,
            )

            if not args.no_verify:
                after = s3.head(
                    item.key
                )

                if (
                    after is None
                    or after.size
                    != item.size
                    or after.sha256
                    != item.sha256
                ):
                    raise WaxError(
                        "post-upload verification failed for "
                        f"s3://{BUCKET}/{item.key}"
                    )

            status = "uploaded"

        results.append(
            {
                "source":
                    str(
                        item.source
                    ),
                "key":
                    item.key,
                "size":
                    item.size,
                "sha256":
                    item.sha256,
                "status":
                    status,
            }
        )

    receipt = write_receipt(
        cwd,
        results,
        args.dry_run,
    )

    payload = {
        "schema":
            "savant://utility/tactic/wax/result/1.0.0",
        "bucket":
            BUCKET,
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
                + f"s3://{BUCKET}/"
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
