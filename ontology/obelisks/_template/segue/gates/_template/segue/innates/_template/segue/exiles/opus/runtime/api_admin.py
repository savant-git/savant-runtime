from __future__ import annotations

import argparse
import json
from typing import Any

from .api_key_registry import (
    create_key,
    public_keys,
    set_status,
)


SCHEMA = (
    "savant://runtime/opus/"
    "api/admin/1.0.0"
)

OWNER = "exile:opus"


def _json(
    value: Any,
) -> None:
    print(
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opus-api-admin",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    create = subparsers.add_parser(
        "create-key"
    )

    create.add_argument(
        "--owner",
        required=True,
    )

    create.add_argument(
        "--environment",
        choices=(
            "live",
            "dev",
            "test",
        ),
        default="live",
    )

    create.add_argument(
        "--scope",
        action="append",
        dest="scopes",
        default=None,
    )

    create.add_argument(
        "--route",
        action="append",
        dest="routes",
        default=None,
    )

    create.add_argument(
        "--expires-at",
        default=None,
    )

    subparsers.add_parser(
        "list-keys"
    )

    revoke = subparsers.add_parser(
        "revoke-key"
    )

    revoke.add_argument(
        "key_id"
    )

    activate = subparsers.add_parser(
        "activate-key"
    )

    activate.add_argument(
        "key_id"
    )

    return parser


def create_key_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    scopes = (
        args.scopes
        if args.scopes is not None
        else [
            "text:infer",
        ]
    )

    routes = (
        args.routes
        if args.routes is not None
        else [
            "text_inference_route",
        ]
    )

    secret, record = create_key(
        owner=args.owner,
        environment=args.environment,
        scopes=scopes,
        allowed_routes=routes,
        expires_at=args.expires_at,
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "operation": "create_key",
        "secret": secret,
        "secret_disclosure": "once",
        "record": record,
    }


def list_keys_command() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "operation": "list_keys",
        "keys": public_keys(),
    }


def set_status_command(
    key_id: str,
    status: str,
) -> dict[str, Any]:
    record = set_status(
        key_id,
        status,
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "operation": (
            f"{status}_key"
        ),
        "record": record,
    }


def main() -> None:
    parser = _parser()

    args = parser.parse_args()

    if args.command == "create-key":
        result = create_key_command(
            args
        )

    elif args.command == "list-keys":
        result = list_keys_command()

    elif args.command == "revoke-key":
        result = set_status_command(
            args.key_id,
            "revoked",
        )

    elif args.command == "activate-key":
        result = set_status_command(
            args.key_id,
            "active",
        )

    else:
        parser.error(
            "unknown command"
        )

        return

    _json(
        result
    )


if __name__ == "__main__":
    main()
