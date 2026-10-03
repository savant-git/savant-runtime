#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess

from dataclasses import dataclass
from typing import Any
from typing import Iterator
from typing import Sequence


BUCKET = "savant-ai-cluster"


class S3BoundaryError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class S3Object:
    key: str
    size: int
    etag: str | None = None
    sha256: str | None = None


class S3Boundary:
    def __init__(
        self,
        bucket: str = BUCKET,
    ) -> None:
        self.bucket = bucket

        self.aws = shutil.which(
            "aws"
        )

        if not self.aws:
            raise S3BoundaryError(
                "aws CLI is not installed or not on PATH"
            )

        self.env = dict(
            os.environ
        )

        self.env.setdefault(
            "AWS_PAGER",
            "",
        )

    def _run(
        self,
        args: Sequence[str],
        *,
        capture: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:

        result = subprocess.run(
            [
                self.aws,
                *args,
            ],
            env=self.env,
            text=True,
            stdout=(
                subprocess.PIPE
                if capture
                else None
            ),
            stderr=(
                subprocess.PIPE
                if capture
                else None
            ),
            check=False,
        )

        if (
            check
            and result.returncode
            != 0
        ):
            message = (
                result.stderr
                or result.stdout
                or ""
            ).strip()

            raise S3BoundaryError(
                message
                or (
                    "aws exited with "
                    f"{result.returncode}"
                )
            )

        return result

    def _json(
        self,
        args: Sequence[str],
        *,
        allow_missing: bool = False,
    ) -> dict[str, Any] | None:

        result = self._run(
            [
                *args,
                "--output",
                "json",
            ],
            capture=True,
            check=False,
        )

        if result.returncode != 0:
            message = (
                result.stderr
                or ""
            ).strip()

            if (
                allow_missing
                and any(
                    token in message
                    for token in (
                        "404",
                        "Not Found",
                        "NoSuchKey",
                    )
                )
            ):
                return None

            raise S3BoundaryError(
                message
                or (
                    "aws exited with "
                    f"{result.returncode}"
                )
            )

        text = (
            result.stdout
            or ""
        ).strip()

        if not text:
            return {}

        value = json.loads(
            text
        )

        if not isinstance(
            value,
            dict,
        ):
            raise S3BoundaryError(
                "aws returned non-object JSON"
            )

        return value

    def status(
        self,
    ) -> tuple[
        bool,
        str | None,
    ]:

        result = self._run(
            [
                "s3api",
                "head-bucket",
                "--bucket",
                self.bucket,
            ],
            capture=True,
            check=False,
        )

        if result.returncode == 0:
            return (
                True,
                None,
            )

        message = (
            result.stderr
            or result.stdout
            or (
                "aws exited with "
                f"{result.returncode}"
            )
        ).strip()

        return (
            False,
            message,
        )

    def head(
        self,
        key: str,
        *,
        allow_missing: bool = False,
    ) -> S3Object | None:

        payload = self._json(
            [
                "s3api",
                "head-object",
                "--bucket",
                self.bucket,
                "--key",
                key,
            ],
            allow_missing=allow_missing,
        )

        if payload is None:
            return None

        metadata = (
            payload.get(
                "Metadata"
            )
            or {}
        )

        sha = (
            metadata.get(
                "savant-sha256"
            )
            if isinstance(
                metadata,
                dict,
            )
            else None
        )

        if not (
            isinstance(
                sha,
                str,
            )
            and len(
                sha
            )
            == 64
        ):
            sha = None

        etag = payload.get(
            "ETag"
        )

        return S3Object(
            key=key,
            size=int(
                payload.get(
                    "ContentLength",
                    0,
                )
            ),
            etag=(
                str(
                    etag
                )
                if etag
                else None
            ),
            sha256=sha,
        )

    def iter_objects(
        self,
        prefix: str,
    ) -> Iterator[S3Object]:

        token: str | None = None

        while True:
            args = [
                "s3api",
                "list-objects-v2",
                "--bucket",
                self.bucket,
                "--prefix",
                prefix,
            ]

            if token:
                args += [
                    "--continuation-token",
                    token,
                ]

            payload = (
                self._json(
                    args
                )
                or {}
            )

            for item in (
                payload.get(
                    "Contents"
                )
                or []
            ):
                if (
                    not isinstance(
                        item,
                        dict,
                    )
                    or not isinstance(
                        item.get(
                            "Key"
                        ),
                        str,
                    )
                ):
                    continue

                key = item[
                    "Key"
                ]

                if key.endswith(
                    "/"
                ):
                    continue

                yield S3Object(
                    key=key,
                    size=int(
                        item.get(
                            "Size",
                            0,
                        )
                    ),
                    etag=(
                        str(
                            item.get(
                                "ETag"
                            )
                        )
                        if item.get(
                            "ETag"
                        )
                        else None
                    ),
                )

            if not payload.get(
                "IsTruncated"
            ):
                return

            token = payload.get(
                "NextContinuationToken"
            )

            if (
                not isinstance(
                    token,
                    str,
                )
                or not token
            ):
                raise S3BoundaryError(
                    "truncated S3 listing without continuation token"
                )

    def upload(
        self,
        local_path: str,
        key: str,
        sha256: str,
    ) -> None:

        self._run(
            [
                "s3",
                "cp",
                local_path,
                (
                    f"s3://"
                    f"{self.bucket}/"
                    f"{key}"
                ),
                "--only-show-errors",
                "--metadata",
                (
                    "savant-sha256="
                    f"{sha256},"
                    "savant-transfer=1"
                ),
            ]
        )

    def download(
        self,
        key: str,
        local_path: str,
    ) -> None:

        self._run(
            [
                "s3",
                "cp",
                (
                    f"s3://"
                    f"{self.bucket}/"
                    f"{key}"
                ),
                local_path,
                "--only-show-errors",
            ]
        )
