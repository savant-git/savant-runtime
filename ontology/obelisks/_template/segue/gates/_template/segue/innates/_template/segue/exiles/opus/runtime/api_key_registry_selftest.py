from __future__ import annotations

import json
import stat
import tempfile
from pathlib import Path

from .api_key_registry import (
    authenticate,
    create_key,
    load_registry,
    public_keys,
    set_status,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        path = (
            Path(
                root
            )
            / "keys.json"
        )

        secret, public = create_key(
            owner="savant",
            environment="test",
            scopes=[
                "text:infer",
            ],
            allowed_routes=[
                "text_inference_route",
            ],
            path=path,
        )

        assert path.exists()

        mode = stat.S_IMODE(
            path.stat().st_mode
        )

        assert mode == 0o600

        registry = load_registry(
            path
        )

        serialized = json.dumps(
            registry,
            sort_keys=True,
        )

        assert secret not in serialized

        assert public[
            "key_id"
        ] in registry[
            "keys"
        ]

        authenticated = authenticate(
            secret,
            required_scope="text:infer",
            required_route=(
                "text_inference_route"
            ),
            path=path,
        )

        assert authenticated

        assert authenticated[
            "key_id"
        ] == public[
            "key_id"
        ]

        assert not authenticate(
            secret,
            required_scope="admin",
            path=path,
        )

        listed = public_keys(
            path=path
        )

        assert len(
            listed
        ) == 1

        assert (
            "secret_hash"
            not in listed[
                0
            ]
        )

        set_status(
            public[
                "key_id"
            ],
            "revoked",
            path=path,
        )

        assert not authenticate(
            secret,
            required_scope="text:infer",
            required_route=(
                "text_inference_route"
            ),
            path=path,
        )

        print(
            "opus api key registry: ok"
        )


if __name__ == "__main__":
    main()
