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


ENV_PATH = Path("/root/.env")

REQUIRED_CONFIGURATION = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "AWS_S3_BUCKET",
)

OPTIONAL_CONFIGURATION = (
    "AWS_SESSION_TOKEN",
    "AWS_S3_PREFIX",
)

ENVIRONMENT_NAME = re.compile(
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
class S3Configuration:
    bucket: str
    region: str
    configured_prefix: str | None
    environment: dict[str, str]


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

    comment_index = value.find(
        " #"
    )

    if comment_index >= 0:
        value = value[
            :comment_index
        ].rstrip()

    return value


def read_configuration_file() -> dict[
    str,
    str,
]:
    if not ENV_PATH.is_file():
        raise S3BoundaryError(
            f"missing AWS configuration: {ENV_PATH}"
        )

    try:
        lines = ENV_PATH.read_text(
            encoding="utf-8",
        ).splitlines()

    except OSError as exc:
        raise S3BoundaryError(
            f"cannot read {ENV_PATH}: {exc}"
        ) from exc

    admitted = set(
        REQUIRED_CONFIGURATION
        + OPTIONAL_CONFIGURATION
    )

    values: dict[
        str,
        str,
    ] = {}

    for original in lines:
        line = original.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if line.startswith(
            "export "
        ):
            line = line[
                len("export "):
            ].lstrip()

        if "=" not in line:
            continue

        name, raw_value = line.split(
            "=",
            1,
        )

        name = name.strip()

        if not ENVIRONMENT_NAME.fullmatch(
            name
        ):
            continue

        if name not in admitted:
            continue

        value = parse_env_value(
            raw_value
        )

        if value:
            values[
                name
            ] = value

    return values


def build_configuration() -> S3Configuration:
    file_values = (
        read_configuration_file()
    )

    values: dict[
        str,
        str,
    ] = {}

    for name in (
        REQUIRED_CONFIGURATION
        + OPTIONAL_CONFIGURATION
    ):
        process_value = (
            os.environ.get(
                name
            )
        )

        if process_value:
            values[
                name
            ] = process_value

        elif name in file_values:
            values[
                name
            ] = file_values[
                name
            ]

    missing = [
        name
        for name
        in REQUIRED_CONFIGURATION
        if not values.get(
            name
        )
    ]

    if missing:
        raise S3BoundaryError(
            "missing required AWS configuration names in "
            f"{ENV_PATH}: "
            + ", ".join(
                missing
            )
        )

    environment = dict(
        os.environ
    )

    environment[
        "AWS_ACCESS_KEY_ID"
    ] = values[
        "AWS_ACCESS_KEY_ID"
    ]

    environment[
        "AWS_SECRET_ACCESS_KEY"
    ] = values[
        "AWS_SECRET_ACCESS_KEY"
    ]

    environment[
        "AWS_REGION"
    ] = values[
        "AWS_REGION"
    ]

    environment[
        "AWS_DEFAULT_REGION"
    ] = values[
        "AWS_REGION"
    ]

    session_token = values.get(
        "AWS_SESSION_TOKEN"
    )

    if session_token:
        environment[
            "AWS_SESSION_TOKEN"
        ] = session_token

    environment[
        "AWS_PAGER"
    ] = ""

    configured_prefix = (
        values.get(
            "AWS_S3_PREFIX"
        )
    )

    if configured_prefix is not None:
        configured_prefix = (
            configured_prefix
            .strip()
            .strip("/")
        )

        if not configured_prefix:
            configured_prefix = None

    return S3Configuration(
        bucket=values[
            "AWS_S3_BUCKET"
        ],
        region=values[
            "AWS_REGION"
        ],
        configured_prefix=(
            configured_prefix
        ),
        environment=environment,
    )


class S3Boundary:
    def __init__(
        self,
    ) -> None:
        self.configuration = (
            build_configuration()
        )

        self.bucket = (
            self.configuration.bucket
        )

        self.region = (
            self.configuration.region
        )

        self.configured_prefix = (
            self.configuration
            .configured_prefix
        )

        self.env = (
            self.configuration.environment
        )

        self.aws = shutil.which(
            "aws"
        )

        if not self.aws:
            raise S3BoundaryError(
                "aws CLI is not installed or not on PATH"
            )

    def configuration_status(
        self,
    ) -> dict[str, Any]:
        return {
            "configuration_source":
                str(
                    ENV_PATH
                ),
            "bucket":
                self.bucket,
            "region":
                self.region,
            "configured_prefix_present":
                self.configured_prefix
                is not None,
            "configured_prefix_applied":
                False,
            "access_key_present":
                bool(
                    self.env.get(
                        "AWS_ACCESS_KEY_ID"
                    )
                ),
            "secret_key_present":
                bool(
                    self.env.get(
                        "AWS_SECRET_ACCESS_KEY"
                    )
                ),
            "session_token_present":
                bool(
                    self.env.get(
                        "AWS_SESSION_TOKEN"
                    )
                ),
        }

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

        sha256 = (
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
                sha256,
                str,
            )
            and re.fullmatch(
                r"[0-9a-fA-F]{64}",
                sha256,
            )
        ):
            sha256 = None

        elif sha256 is not None:
            sha256 = (
                sha256.lower()
            )

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
            sha256=sha256,
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
                args.extend(
                    [
                        "--continuation-token",
                        token,
                    ]
                )

            payload = (
                self._json(
                    args
                )
                or {}
            )

            contents = (
                payload.get(
                    "Contents"
                )
                or []
            )

            for item in contents:
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
