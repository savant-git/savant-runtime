#!/usr/bin/env python3

from __future__ import annotations

import sys


ADAPTER_DIRECTORY = (
    "/root/savant-runtime/runtime/adapters"
)

if ADAPTER_DIRECTORY not in sys.path:
    sys.path.insert(
        0,
        ADAPTER_DIRECTORY,
    )


from aws_s3_boundary import S3Boundary
from aws_s3_boundary import S3BoundaryError


def main() -> int:
    s3 = S3Boundary()

    status = (
        s3.configuration_status()
    )

    print(
        "configuration_source:",
        status[
            "configuration_source"
        ],
    )

    print(
        "bucket:",
        status[
            "bucket"
        ],
    )

    print(
        "region:",
        status[
            "region"
        ],
    )

    print(
        "access_key_present:",
        status[
            "access_key_present"
        ],
    )

    print(
        "secret_key_present:",
        status[
            "secret_key_present"
        ],
    )

    print(
        "session_token_present:",
        status[
            "session_token_present"
        ],
    )

    print(
        "configured_prefix_present:",
        status[
            "configured_prefix_present"
        ],
    )

    print(
        "configured_prefix_applied:",
        status[
            "configured_prefix_applied"
        ],
    )

    reachable, error = (
        s3.status()
    )

    print(
        "bucket_reachable:",
        reachable,
    )

    if error:
        print(
            "error:",
            error,
        )

    return (
        0
        if reachable
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except S3BoundaryError as exc:
        print(
            f"test_aws_s3_boundary: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
