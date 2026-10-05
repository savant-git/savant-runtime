#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import Sequence


runtime_root = Path(
    "/root/savant-runtime"
)

env_path = (
    runtime_root
    / ".env"
)

BUCKET = "savant-ai-cluster"

allowed_aws_environment = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_PROFILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
    "AWS_ENDPOINT_URL",
    "AWS_CA_BUNDLE",
}

environment_name = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


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


def parse_env_value(
    raw: str,
) -> str:
    value = raw.strip()

    if not value:
        return ""

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {
            "'",
            '"',
        }
    ):
        quote = value[0]
        value = value[
            1:-1
        ]

        if quote == '"':
            value = (
                value
                .replace(
                    r"\n",
                    "\n",
                )
                .replace(
                    r"\r",
                    "\r",
                )
                .replace(
                    r"\t",
                    "\t",
                )
                .replace(
                    r"\"",
                    '"',
                )
                .replace(
                    r"\\",
                    "\\",
                )
            )

        return value

    comment = value.find(
        " #"
    )

    if comment >= 0:
        value = value[
            :comment
        ].rstrip()

    return value


def load_aws_environment(
    base: dict[str, str],
) -> dict[str, str]:
    environment = dict(
        base
    )

    if not env_path.exists():
        return environment

    if not env_path.is_file():
        raise S3BoundaryError(
            f"expected regular environment file: {env_path}"
        )

    try:
        lines = env_path.read_text(
            encoding="utf-8",
        ).splitlines()

    except OSError as exc:
        raise S3BoundaryError(
            f"cannot read {env_path}: {exc}"
        ) from exc

    for number, original in enumerate(
        lines,
        start=1,
    ):
        line = original.strip()

        if (
            not line
            or line.startswith(
                "#"
            )
        ):
            continue

        if line.startswith(
            "export "
        ):
            line = line[
                len(
                    "export "
                ):
            ].lstrip()

        if "=" not in line:
            continue

        name, raw_value = line.split(
            "=",
            1,
        )

        name = name.strip()

        if not environment_name.fullmatch(
            name
        ):
            continue

        if name not in allowed_aws_environment:
            continue

        value = parse_env_value(
            raw_value
        )

        if not value:
            continue

# Existing process credentials outrank the local .env.
# This permits explicit temporary/session credentials or a
# deliberately selected profile to override persistent defaults.
        environment.setdefault(
            name,
            value,
        )

    return environment


class S3Boundary:
    def __init__(
        self,
        bucket: str = BUCKET,
    ) -> None:
        if bucket != BUCKET:
            raise S3BoundaryError(
                "S3 boundary is restricted to "
                f"{BUCKET!r}"
            )

        self.bucket = bucket

        self.aws = shutil.which(
            "aws"
        )

        if not self.aws:
            raise S3BoundaryError(
                "aws CLI is not installed or not on PATH"
            )

        self.env = load_aws_environment(
            dict(
                os.environ
            )
        )

        self.env[
            "AWS_PAGER"
        ] = ""

    def credential_source(
        self,
    ) -> str:
        if (
            self.env.get(
                "AWS_ACCESS_KEY_ID"
            )
            and self.env.get(
                "AWS_SECRET_ACCESS_KEY"
            )
        ):
            return "environment"

        if self.env.get(
            "AWS_PROFILE"
        ):
            return "profile"

        if self.env.get(
            "AWS_SHARED_CREDENTIALS_FILE"
        ):
            return "shared-credentials-file"

        return "aws-default-chain"

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
                or result.stdout
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

        try:
            value = json.loads(
                text
            )

        except json.JSONDecodeError as exc:
            raise S3BoundaryError(
                "aws returned invalid JSON"
            ) from exc

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
