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
from .util import sha256_file


class UploadError(RuntimeError):
    pass


def _bucket() -> str | None:
    for name in ("SDUMP_S3_BUCKET", "S3_BUCKET", "AWS_S3_BUCKET", "AWS_BUCKET"):
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def _key(path: Path, prefix: str | None) -> str:
    configured = prefix if prefix is not None else os.environ.get("SDUMP_S3_PREFIX", "")
    configured = configured.strip().strip("/")
    return f"{configured}/{path.name}" if configured else path.name


def _client():
    import boto3
    from botocore.config import Config

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    endpoint = os.environ.get("AWS_ENDPOINT_URL") or os.environ.get("S3_ENDPOINT_URL")
    kwargs: dict[str, Any] = {
        "config": Config(
            retries={"max_attempts": 10, "mode": "adaptive"},
            connect_timeout=15,
            read_timeout=180,
            tcp_keepalive=True,
        )
    }
    if region:
        kwargs["region_name"] = region
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def _verify_head(
    head: dict[str, Any],
    local_size: int,
    local_sha256: str,
) -> tuple[bool, str]:
    try:
        remote_size = int(head.get("ContentLength"))
    except (TypeError, ValueError):
        return False, "remote object has no valid ContentLength"
    if remote_size != local_size:
        return False, f"size mismatch local={local_size} remote={remote_size}"
    metadata = head.get("Metadata") if isinstance(head.get("Metadata"), dict) else {}
    metadata = {str(key).casefold(): str(value).casefold() for key, value in metadata.items()}
    recorded = metadata.get("sha256")
    if not recorded:
        return False, "remote object is missing authoritative sha256 metadata"
    if recorded != local_sha256.casefold():
        return False, "remote sha256 metadata mismatch"
    return True, "remote size and sha256 metadata verified"


def _boto_upload(
    path: Path,
    bucket: str,
    key: str,
    local_sha256: str,
    metadata: dict[str, str],
    concurrency: int,
) -> UploadResult:
    from boto3.s3.transfer import TransferConfig

    client = _client()
    transfer = TransferConfig(
        multipart_threshold=8 * 1024 * 1024,
        multipart_chunksize=8 * 1024 * 1024,
        max_concurrency=max(1, concurrency),
        use_threads=concurrency > 1,
    )
    extra_args: dict[str, Any] = {
        "Metadata": {**metadata, "sha256": local_sha256},
        "ContentType": "text/plain; charset=utf-8" if path.suffix != ".zst" else "application/zstd",
    }
    if path.suffix == ".zst":
        extra_args["ContentEncoding"] = "zstd"

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            client.upload_file(
                str(path),
                bucket,
                key,
                ExtraArgs=extra_args,
                Config=transfer,
            )
            head = client.head_object(Bucket=bucket, Key=key)
            verified, reason = _verify_head(head, path.stat().st_size, local_sha256)
            if not verified:
                raise UploadError(reason)
            return UploadResult(
                uploaded=True,
                verified=True,
                bucket=bucket,
                key=key,
                uri=f"s3://{bucket}/{key}",
                size=path.stat().st_size,
                sha256=local_sha256,
                etag=head.get("ETag"),
                version_id=head.get("VersionId"),
                reason=reason,
            )
        except Exception as error:
            last_error = error
            if attempt < 3:
                time.sleep((2 ** (attempt - 1)) + random.random())
    raise UploadError(f"S3 upload failed after retries: {last_error}")


def _aws_cli_upload(
    path: Path,
    bucket: str,
    key: str,
    local_sha256: str,
    metadata: dict[str, str],
) -> UploadResult:
    aws = shutil.which("aws")
    if not aws:
        raise UploadError("boto3 is unavailable and AWS CLI was not found")
    metadata_string = ",".join(f"{key_}={value}" for key_, value in {**metadata, "sha256": local_sha256}.items())
    uri = f"s3://{bucket}/{key}"
    upload = subprocess.run(
        [aws, "s3", "cp", str(path), uri, "--only-show-errors", "--metadata", metadata_string],
        capture_output=True,
        text=True,
        check=False,
    )
    if upload.returncode != 0:
        raise UploadError(upload.stderr.strip() or upload.stdout.strip() or "AWS CLI upload failed")
    head_process = subprocess.run(
        [aws, "s3api", "head-object", "--bucket", bucket, "--key", key],
        capture_output=True,
        text=True,
        check=False,
    )
    if head_process.returncode != 0:
        raise UploadError(head_process.stderr.strip() or "AWS CLI head-object failed")
    head = json.loads(head_process.stdout)
    verified, reason = _verify_head(head, path.stat().st_size, local_sha256)
    if not verified:
        raise UploadError(reason)
    return UploadResult(
        uploaded=True,
        verified=True,
        bucket=bucket,
        key=key,
        uri=uri,
        size=path.stat().st_size,
        sha256=local_sha256,
        etag=head.get("ETag"),
        version_id=head.get("VersionId"),
        reason=reason,
    )


def upload_verified(
    path: Path,
    prefix: str | None,
    metadata: dict[str, str],
    concurrency: int = 4,
) -> UploadResult:
    bucket = _bucket()
    if not bucket:
        raise UploadError("missing S3 bucket environment variable")
    key = _key(path, prefix)
    local_sha256 = sha256_file(path)
    try:
        return _boto_upload(path, bucket, key, local_sha256, metadata, concurrency)
    except ImportError:
        return _aws_cli_upload(path, bucket, key, local_sha256, metadata)
