from __future__ import annotations

import argparse

from .api_http import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    serve,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opus-api",
    )

    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
    )

    return parser


def main() -> None:
    args = _parser().parse_args()

    if (
        args.port < 1
        or args.port > 65535
    ):
        raise SystemExit(
            "port must be between "
            "1 and 65535"
        )

    serve(
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
