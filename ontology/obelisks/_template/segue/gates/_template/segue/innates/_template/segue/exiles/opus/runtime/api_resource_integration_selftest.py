from __future__ import annotations

from . import api_request
from .api_request import (
    ApiRequestError,
)


def main() -> None:
    original_authenticate = (
        api_request.authenticate
    )

    original_execute = (
        api_request.execute_text_request
    )

    executed = {
        "count": 0,
    }

    try:
        def fake_authenticate(
            secret,
            *,
            required_scope,
            required_route,
        ):
            assert secret == "test-secret"

            assert required_scope == (
                "text:infer"
            )

            assert required_route == (
                "text_inference_route"
            )

            return {
                "key_id": "test-key",
                "client_owner": (
                    "selftest"
                ),
            }

        def fake_execute(
            request,
        ):
            executed[
                "count"
            ] += 1

            assert request[
                "client_key_id"
            ] == "test-key"

            return {
                "content": "ok",
                "lineage": {
                    "provider": (
                        "test-provider"
                    ),
                    "model": (
                        "test-model"
                    ),
                },
            }

        api_request.authenticate = (
            fake_authenticate
        )

        api_request.execute_text_request = (
            fake_execute
        )

        result = (
            api_request
            .execute_authenticated_text(
                secret="test-secret",
                payload={
                    "model": "opus:auto",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "hello"
                            ),
                        }
                    ],
                    "max_tokens": 128,
                },
            )
        )

        assert executed[
            "count"
        ] == 1

        governance = result[
            "lineage"
        ][
            "api"
        ][
            "resource_governance"
        ]

        assert governance[
            "accepted"
        ] is True

        assert governance[
            "digest"
        ]

        assert governance[
            "metrics"
        ][
            "body_bytes"
        ] > 0

        oversized = {
            "model": "opus:auto",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "x"
                        * 1_000_001
                    ),
                }
            ],
        }

        failed = False

        try:
            (
                api_request
                .execute_authenticated_text(
                    secret=(
                        "test-secret"
                    ),
                    payload=oversized,
                )
            )

        except ApiRequestError:
            failed = True

        assert failed

        assert executed[
            "count"
        ] == 1

        print(
            "opus api resource "
            "integration: ok"
        )

    finally:
        api_request.authenticate = (
            original_authenticate
        )

        api_request.execute_text_request = (
            original_execute
        )


if __name__ == "__main__":
    main()
