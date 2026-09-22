from __future__ import annotations

from .api_admin import _parser
from .api_server import _parser as server_parser


def main() -> None:
    admin = _parser()

    create = admin.parse_args(
        [
            "create-key",
            "--owner",
            "test-client",
            "--environment",
            "test",
        ]
    )

    assert create.command == (
        "create-key"
    )

    assert create.owner == (
        "test-client"
    )

    assert create.environment == (
        "test"
    )

    revoke = admin.parse_args(
        [
            "revoke-key",
            "abc123",
        ]
    )

    assert revoke.command == (
        "revoke-key"
    )

    assert revoke.key_id == (
        "abc123"
    )

    server = server_parser()

    defaults = server.parse_args(
        []
    )

    assert defaults.host == (
        "127.0.0.1"
    )

    assert defaults.port == 8787

    configured = server.parse_args(
        [
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
        ]
    )

    assert configured.host == (
        "0.0.0.0"
    )

    assert configured.port == 9000

    print(
        "opus api operational "
        "surface: ok"
    )


if __name__ == "__main__":
    main()
