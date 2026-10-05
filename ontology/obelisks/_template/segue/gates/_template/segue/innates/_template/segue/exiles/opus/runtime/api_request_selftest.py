from __future__ import annotations

import tempfile
from pathlib import Path

from . import api_request
from .api_key_registry import create_key


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        registry_path = (
            Path(
                root
            )
            / "keys.json"
        )

        secret, client = create_key(
            owner="test-client",
            environment="test",
            scopes=[
                "text:infer",
            ],
            allowed_routes=[
                "text_inference_route",
            ],
            path=registry_path,
        )

        normalized = (
            api_request.normalize_text_request(
                {
                    "model": "opus:auto",
                    "messages": [
                        {
                            "role": "user",
                            "content": "hello",
                        }
                    ],
                    "required_capabilities": [
                        "text",
                    ],
                    "required_layers": [
                        "reasoning",
                    ],
                    "temperature": 0.5,
                },
                client=client,
            )
        )

        assert normalized[
            "owner"
        ] == "opus_api"

        assert normalized[
            "requested_model"
        ] == "opus:auto"

        assert normalized[
            "messages"
        ] == [
            {
                "role": "user",
                "content": "hello",
            }
        ]

        assert normalized[
            "required_capabilities"
        ] == [
            "text",
        ]

        assert normalized[
            "required_layers"
        ] == [
            "reasoning",
        ]

        failed = False

        try:
            api_request.normalize_text_request(
                {
                    "messages": [],
                },
                client=client,
            )
        except api_request.ApiRequestError:
            failed = True

        assert failed

        original_authenticate = (
            api_request.authenticate
        )

        original_execute = (
            api_request.execute_text_request
        )

        captured = {}

        try:
            def fake_authenticate(
                supplied_secret,
                *,
                required_scope=None,
                required_route=None,
            ):
                assert (
                    supplied_secret
                    == secret
                )

                assert (
                    required_scope
                    == "text:infer"
                )

                assert (
                    required_route
                    == "text_inference_route"
                )

                return client

            def fake_execute(
                request,
            ):
                captured[
                    "request"
                ] = request

                return {
                    "id": "test-result",
                    "lineage": {
                        "owner": "opus",
                        "route": (
                            "text_inference_route"
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
                api_request.execute_authenticated_text(
                    secret=secret,
                    payload={
                        "model": "opus:auto",
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "test request"
                                ),
                            }
                        ],
                    },
                )
            )

        finally:
            api_request.authenticate = (
                original_authenticate
            )

            api_request.execute_text_request = (
                original_execute
            )

        assert captured[
            "request"
        ][
            "owner"
        ] == "opus_api"

        assert result[
            "lineage"
        ][
            "owner"
        ] == "opus"

        assert result[
            "lineage"
        ][
            "api"
        ][
            "client_key_id"
        ] == client[
            "key_id"
        ]

        assert result[
            "lineage"
        ][
            "api"
        ][
            "canonical_execution"
        ] == (
            "opus.runtime.router."
            "execute_text_request"
        )

        print(
            "opus api request boundary: ok"
        )


if __name__ == "__main__":
    main()
