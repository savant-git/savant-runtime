from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .api_auth import (
    issue_key,
    public_record,
    verify_key,
)


SCHEMA = (
    "savant://runtime/opus/"
    "api/key-registry/1.0.0"
)

OWNER = "exile:opus"

OPUS_ROOT = Path(
    __file__
).resolve().parents[1]

DEFAULT_REGISTRY_PATH = (
    OPUS_ROOT
    / "runtime"
    / "state"
    / "api_keys.json"
)


def _empty_registry() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "type": "opus_api_key_registry",
        "keys": {},
    }


def _validate_registry(
    registry: dict[str, Any],
) -> None:
    if registry.get(
        "schema"
    ) != SCHEMA:
        raise ValueError(
            "invalid opus api key "
            "registry schema"
        )

    if registry.get(
        "owner"
    ) != OWNER:
        raise ValueError(
            "invalid opus api key "
            "registry owner"
        )

    if not isinstance(
        registry.get(
            "keys"
        ),
        dict,
    ):
        raise ValueError(
            "invalid opus api key "
            "registry keys"
        )


def load_registry(
    path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    if not path.exists():
        return _empty_registry()

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        registry = json.load(
            handle
        )

    if not isinstance(
        registry,
        dict,
    ):
        raise ValueError(
            "opus api key registry "
            "must be an object"
        )

    _validate_registry(
        registry
    )

    return registry


def save_registry(
    registry: dict[str, Any],
    path: Path = DEFAULT_REGISTRY_PATH,
) -> None:
    _validate_registry(
        registry
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary = (
        tempfile.mkstemp(
            prefix=(
                f".{path.name}."
            ),
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
    )

    temporary_path = Path(
        temporary
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                registry,
                handle,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            0o600,
        )

        os.replace(
            temporary_path,
            path,
        )

        os.chmod(
            path,
            0o600,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def create_key(
    *,
    owner: str,
    environment: str = "live",
    scopes: Iterable[Any] | None = None,
    allowed_routes: Iterable[Any] | None = None,
    expires_at: str | None = None,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> tuple[str, dict[str, Any]]:
    secret, record = issue_key(
        environment=environment,
        owner=owner,
        scopes=scopes,
        allowed_routes=allowed_routes,
        expires_at=expires_at,
    )

    registry = load_registry(
        path
    )

    key_id = str(
        record[
            "key_id"
        ]
    )

    if key_id in registry[
        "keys"
    ]:
        raise RuntimeError(
            "opus api key id collision"
        )

    registry[
        "keys"
    ][
        key_id
    ] = record

    save_registry(
        registry,
        path,
    )

    return (
        secret,
        public_record(
            record
        ),
    )


def key_id_from_secret(
    secret: str,
) -> str | None:
    parts = str(
        secret
    ).split(
        "_",
        3,
    )

    if len(
        parts
    ) != 4:
        return None

    if parts[
        0
    ] != "opus":
        return None

    if parts[
        1
    ] not in {
        "live",
        "dev",
        "test",
    }:
        return None

    key_id = parts[
        2
    ].strip()

    if not key_id:
        return None

    return key_id


def authenticate(
    secret: str,
    *,
    required_scope: str | None = None,
    required_route: str | None = None,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any] | None:
    key_id = key_id_from_secret(
        secret
    )

    if not key_id:
        return None

    registry = load_registry(
        path
    )

    record = registry[
        "keys"
    ].get(
        key_id
    )

    if not isinstance(
        record,
        dict,
    ):
        return None

    if not verify_key(
        secret,
        record,
        required_scope=required_scope,
        required_route=required_route,
    ):
        return None

    return public_record(
        record
    )


def set_status(
    key_id: str,
    status: str,
    *,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    status = str(
        status
    ).strip().lower()

    if status not in {
        "active",
        "revoked",
    }:
        raise ValueError(
            "invalid opus api key status"
        )

    registry = load_registry(
        path
    )

    record = registry[
        "keys"
    ].get(
        key_id
    )

    if not isinstance(
        record,
        dict,
    ):
        raise KeyError(
            key_id
        )

    record[
        "status"
    ] = status

    save_registry(
        registry,
        path,
    )

    return public_record(
        record
    )


def public_keys(
    *,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> list[dict[str, Any]]:
    registry = load_registry(
        path
    )

    return [
        public_record(
            registry[
                "keys"
            ][
                key_id
            ]
        )
        for key_id
        in sorted(
            registry[
                "keys"
            ]
        )
    ]
