from __future__ import annotations

from .api_auth import (
    issue_key,
    public_record,
    verify_key,
)


def main() -> None:
    secret, record = issue_key(
        environment="test",
        owner="savant",
        scopes=[
            "text:infer",
        ],
        allowed_routes=[
            "text_inference_route",
        ],
    )

    assert secret.startswith(
        "opus_test_"
    )

    assert secret not in str(
        record
    )

    assert record[
        "secret_hash"
    ]

    assert verify_key(
        secret,
        record,
    )

    assert verify_key(
        secret,
        record,
        required_scope="text:infer",
        required_route=(
            "text_inference_route"
        ),
    )

    assert not verify_key(
        secret + "invalid",
        record,
    )

    assert not verify_key(
        secret,
        record,
        required_scope="admin",
    )

    revoked = dict(
        record
    )

    revoked[
        "status"
    ] = "revoked"

    assert not verify_key(
        secret,
        revoked,
    )

    public = public_record(
        record
    )

    assert "secret_hash" not in public

    print(
        "opus api auth: ok"
    )


if __name__ == "__main__":
    main()
