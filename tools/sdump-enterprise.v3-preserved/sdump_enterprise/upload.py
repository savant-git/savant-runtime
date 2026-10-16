from __future__ import annotations

import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import time
from typing import Any

from .model import UploadResult
from .util import (
    load_environment,
    runtime_root,
    sha256_file,
)


class UploadError(RuntimeError):
    pass


def _load_environment() -> None:
    load_environment(
        runtime_root()
    )


def _env(
    name: str,
) -> str | None:
    value = os.environ.get(
        name
    )

    if not value:
        return None

    normalized = value.strip()

    return (
        normalized
        or None
    )


def _bucket() -> str:
    bucket = _env(
        "AWS_S3_BUCKET"
    )

    if not bucket:
        raise UploadError(
            (
                "missing AWS_S3_BUCKET "
                "in the loaded environment"
            )
        )

    return bucket


def _key(
    path: Path,
    prefix: str | None,
) -> str:
    configured = (
        prefix
        if prefix is not None
        else (
            _env(
                "AWS_S3_PREFIX"
            )
            or ""
        )
    )

    configured = (
        configured
        .strip()
        .strip("/")
    )

    return (
        f"{configured}/{path.name}"
        if configured
        else path.name
    )


def _client():
    import boto3

    from botocore.config import (
        Config,
    )

    kwargs: dict[str, Any] = {
        "config":
            Config(
                retries={
                    "max_attempts":
                        10,
                    "mode":
                        "adaptive",
                },
                connect_timeout=15,
                read_timeout=180,
                tcp_keepalive=True,
                s3={
                    "addressing_style":
                        (
                            _env(
                                "AWS_S3_ADDRESSING_STYLE"
                            )
                            or "auto"
                        )
                },
            )
    }

    region = (
        _env(
            "AWS_REGION"
        )
        or _env(
            "AWS_DEFAULT_REGION"
        )
    )

    endpoint = (
        _env(
            "AWS_ENDPOINT_URL_S3"
        )
        or _env(
            "AWS_ENDPOINT_URL"
        )
    )

    if region:
        kwargs[
            "region_name"
        ] = region

    if endpoint:
        kwargs[
            "endpoint_url"
        ] = endpoint

    return boto3.client(
        "s3",
        **kwargs,
    )


def _verify_head(
    head: dict[str, Any],
    local_size: int,
    local_sha256: str,
) -> tuple[
    bool,
    str,
]:
    try:
        remote_size = int(
            head.get(
                "ContentLength"
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            False,
            (
                "remote object has no "
                "valid ContentLength"
            ),
        )

    if remote_size != local_size:
        return (
            False,
            (
                "size mismatch "
                f"local={local_size} "
                f"remote={remote_size}"
            ),
        )

    raw = head.get(
        "Metadata"
    )

    metadata = (
        raw
        if isinstance(
            raw,
            dict,
        )
        else {}
    )

    normalized = {
        str(
            key
        ).casefold():
        str(
            value
        ).casefold()
        for key, value
        in metadata.items()
    }

    recorded = normalized.get(
        "sha256"
    )

    if not recorded:
        return (
            False,
            (
                "remote object is missing "
                "sha256 metadata"
            ),
        )

    if (
        recorded
        != local_sha256.casefold()
    ):
        return (
            False,
            (
                "remote sha256 "
                "metadata mismatch"
            ),
        )

    return (
        True,
        (
            "remote size and "
            "sha256 metadata verified"
        ),
    )


def _extra_args(
    path: Path,
    metadata: dict[str, str],
    local_sha256: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "Metadata":
            {
                **metadata,
                "sha256":
                    local_sha256,
            },
        "ContentType":
            (
                "application/zstd"
                if path.suffix
                == ".zst"
                else (
                    "text/plain; "
                    "charset=utf-8"
                )
            ),
    }

    if path.suffix == ".zst":
        result[
            "ContentEncoding"
        ] = "zstd"

    encryption = _env(
        "AWS_S3_SERVER_SIDE_ENCRYPTION"
    )

    kms_key = _env(
        "AWS_S3_KMS_KEY_ID"
    )

    storage_class = _env(
        "AWS_S3_STORAGE_CLASS"
    )

    if encryption:
        result[
            "ServerSideEncryption"
        ] = encryption

    if kms_key:
        result[
            "SSEKMSKeyId"
        ] = kms_key

    if storage_class:
        result[
            "StorageClass"
        ] = storage_class

    return result


def _boto_upload(
    path: Path,
    bucket: str,
    key: str,
    local_sha256: str,
    metadata: dict[str, str],
    concurrency: int,
) -> UploadResult:
    from boto3.s3.transfer import (
        TransferConfig,
    )

    client = _client()

    transfer = TransferConfig(
        multipart_threshold=(
            8
            * 1024
            * 1024
        ),
        multipart_chunksize=(
            8
            * 1024
            * 1024
        ),
        max_concurrency=max(
            1,
            concurrency,
        ),
        use_threads=(
            concurrency > 1
        ),
    )

    last_error: Exception | None = None

    for attempt in range(
        1,
        4,
    ):
        try:
            client.upload_file(
                str(
                    path
                ),
                bucket,
                key,
                ExtraArgs=_extra_args(
                    path,
                    metadata,
                    local_sha256,
                ),
                Config=transfer,
            )

            head = client.head_object(
                Bucket=bucket,
                Key=key,
            )

            verified, reason = (
                _verify_head(
                    head,
                    path.stat().st_size,
                    local_sha256,
                )
            )

            if not verified:
                raise UploadError(
                    reason
                )

            return UploadResult(
                uploaded=True,
                verified=True,
                bucket=bucket,
                key=key,
                uri=(
                    f"s3://{bucket}/{key}"
                ),
                size=(
                    path.stat().st_size
                ),
                sha256=local_sha256,
                etag=head.get(
                    "ETag"
                ),
                version_id=head.get(
                    "VersionId"
                ),
                reason=reason,
            )

        except Exception as error:
            last_error = error

            if attempt < 3:
                time.sleep(
                    (
                        2
                        ** (
                            attempt - 1
                        )
                    )
                    + random.random()
                )

    raise UploadError(
        (
            "S3 upload failed "
            f"after retries: {last_error}"
        )
    )


def _aws_cli_upload(
    path: Path,
    bucket: str,
    key: str,
    local_sha256: str,
    metadata: dict[str, str],
) -> UploadResult:
    executable = shutil.which(
        "aws"
    )

    if not executable:
        raise UploadError(
            (
                "boto3 is unavailable "
                "and AWS CLI was not found"
            )
        )

    uri = (
        f"s3://{bucket}/{key}"
    )

    metadata_string = ",".join(
        (
            f"{name}="
            f"{value}"
        )
        for name, value
        in {
            **metadata,
            "sha256":
                local_sha256,
        }.items()
    )

    command = [
        executable,
        "s3",
        "cp",
        str(
            path
        ),
        uri,
        "--only-show-errors",
        "--metadata",
        metadata_string,
    ]

    endpoint = (
        _env(
            "AWS_ENDPOINT_URL_S3"
        )
        or _env(
            "AWS_ENDPOINT_URL"
        )
    )

    if endpoint:
        command.extend(
            [
                "--endpoint-url",
                endpoint,
            ]
        )

    upload = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if upload.returncode != 0:
        raise UploadError(
            (
                upload.stderr.strip()
                or upload.stdout.strip()
                or "AWS CLI upload failed"
            )
        )

    head_command = [
        executable,
        "s3api",
        "head-object",
        "--bucket",
        bucket,
        "--key",
        key,
    ]

    if endpoint:
        head_command.extend(
            [
                "--endpoint-url",
                endpoint,
            ]
        )

    head_process = subprocess.run(
        head_command,
        capture_output=True,
        text=True,
        check=False,
    )

    if head_process.returncode != 0:
        raise UploadError(
            (
                head_process.stderr.strip()
                or (
                    "AWS CLI "
                    "head-object failed"
                )
            )
        )

    head = json.loads(
        head_process.stdout
    )

    verified, reason = (
        _verify_head(
            head,
            path.stat().st_size,
            local_sha256,
        )
    )

    if not verified:
        raise UploadError(
            reason
        )

    return UploadResult(
        uploaded=True,
        verified=True,
        bucket=bucket,
        key=key,
        uri=uri,
        size=path.stat().st_size,
        sha256=local_sha256,
        etag=head.get(
            "ETag"
        ),
        version_id=head.get(
            "VersionId"
        ),
        reason=reason,
    )


def upload_verified(
    path: Path,
    prefix: str | None,
    metadata: dict[str, str],
    concurrency: int = 4,
) -> UploadResult:
    _load_environment()

    if not path.is_file():
        raise UploadError(
            (
                "upload artifact "
                f"not found: {path}"
            )
        )

    bucket = _bucket()

    key = _key(
        path,
        prefix,
    )

    local_sha256 = (
        sha256_file(
            path
        )
    )

    try:
        return _boto_upload(
            path,
            bucket,
            key,
            local_sha256,
            metadata,
            concurrency,
        )

    except ImportError:
        return _aws_cli_upload(
            path,
            bucket,
            key,
            local_sha256,
            metadata,
        )
