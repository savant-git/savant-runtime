from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any, Iterable


SCHEMA = "savant://runtime/opus/api/auth/1.0.0"
OWNER = "exile:opus"

_ALLOWED_ENVIRONMENTS = {
    "live",
    "dev",
    "test",
}


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _normalized(
    values: Iterable[Any] | None,
) -> list[str]:
    return sorted(
        {
            str(value).strip()
            for value in (
                values or ()
            )
            if str(value).strip()
        }
    )


def _hash_secret(
    secret: str,
) -> str:
    return hashlib.sha256(
        secret.encode("utf-8")
    ).hexdigest()


def issue_key(
    *,
    environment: str = "live",
    owner: str,
    scopes: Iterable[Any] | None = None,
    allowed_routes: Iterable[Any] | None = None,
    expires_at: str | None = None,
) -> tuple[str, dict[str, Any]]:
    environment = str(
        environment
    ).strip().lower()

    if environment not in _ALLOWED_ENVIRONMENTS:
        raise ValueError(
            "invalid opus api key environment"
        )

    owner = str(
        owner
    ).strip()

    if not owner:
        raise ValueError(
            "opus api key owner is required"
        )

    key_id = secrets.token_hex(
        12
    )

    secret_material = (
        secrets.token_urlsafe(
            32
        )
    )

    secret = (
        f"opus_{environment}_"
        f"{key_id}_{secret_material}"
    )

    record = {
        "schema": SCHEMA,
        "owner": OWNER,
        "type": "opus_api_client_key",
        "key_id": key_id,
        "environment": environment,
        "client_owner": owner,
        "secret_hash": _hash_secret(
            secret
        ),
        "created_at": _utc_now(),
        "expires_at": expires_at,
        "status": "active",
        "scopes": _normalized(
            scopes
        ),
        "allowed_routes": _normalized(
            allowed_routes
        ),
        "authority_effect": "none",
    }

    return (
        secret,
        record,
    )


def verify_key(
    secret: str,
    record: dict[str, Any],
    *,
    required_scope: str | None = None,
    required_route: str | None = None,
) -> bool:
    if record.get(
        "type"
    ) != "opus_api_client_key":
        return False

    if record.get(
        "status"
    ) != "active":
        return False

    supplied_hash = _hash_secret(
        str(
            secret
        )
    )

    expected_hash = str(
        record.get(
            "secret_hash"
        )
        or ""
    )

    if not expected_hash:
        return False

    if not hmac.compare_digest(
        supplied_hash,
        expected_hash,
    ):
        return False

    expires_at = record.get(
        "expires_at"
    )

    if expires_at:
        try:
            expiration = (
                datetime.fromisoformat(
                    str(
                        expires_at
                    ).replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

            if expiration.tzinfo is None:
                expiration = (
                    expiration.replace(
                        tzinfo=timezone.utc
                    )
                )

            if datetime.now(
                timezone.utc
            ) >= expiration.astimezone(
                timezone.utc
            ):
                return False

        except ValueError:
            return False

    if required_scope:
        scopes = set(
            _normalized(
                record.get(
                    "scopes"
                )
            )
        )

        if required_scope not in scopes:
            return False

    if required_route:
        routes = set(
            _normalized(
                record.get(
                    "allowed_routes"
                )
            )
        )

        if (
            routes
            and required_route
            not in routes
        ):
            return False

    return True


def public_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value
        in record.items()
        if key != "secret_hash"
    }
