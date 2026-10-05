from __future__ import annotations

from . import enterprise_execution


def main() -> None:
    original = (
        enterprise_execution
        .execute_text_request
    )

    captured = {}

    try:
        def fake_execute(
            request,
        ):
            captured[
                "request"
            ] = request

            return {
                "id": "enterprise-test",
                "content": "ok",
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
                "lineage": {
                    "owner": "opus",
                    "provider": (
                        "test-provider"
                    ),
                    "model": (
                        "test-model"
                    ),
                },
            }

        enterprise_execution.execute_text_request = (
            fake_execute
        )

        result = (
            enterprise_execution.execute(
                {
                    "request_id": (
                        "enterprise-test"
                    ),
                    "trace_id": (
                        "trace-enterprise"
                    ),
                    "tenant_id": (
                        "tenant-enterprise"
                    ),
                    "owner": "opus_api",
                    "request_origin": (
                        "external_client"
                    ),
                    "client_key_id": (
                        "client-key"
                    ),
                    "client_owner": (
                        "client-owner"
                    ),
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "test"
                            ),
                        }
                    ],
                    "requested_model": (
                        "opus:auto"
                    ),
                    "required_capabilities": [
                        "text",
                    ],
                    "timeout_seconds": 30,
                }
            )
        )

        assert result[
            "result"
        ][
            "content"
        ] == "ok"

        assert result[
            "execution_receipt"
        ][
            "status"
        ] == "succeeded"

        assert result[
            "lineage"
        ][
            "canonical_executor"
        ] == (
            "opus.runtime.router."
            "execute_text_request"
        )

        assert captured[
            "request"
        ][
            "owner"
        ] == "opus_api"

        assert captured[
            "request"
        ][
            "request_origin"
        ] == (
            "external_client"
        )

        assert captured[
            "request"
        ][
            "client_key_id"
        ] == "client-key"

        assert captured[
            "request"
        ][
            "requested_model"
        ] == "opus:auto"

        assert captured[
            "request"
        ][
            "required_capabilities"
        ] == [
            "text",
        ]

        print(
            "opus enterprise execution: ok"
        )

    finally:
        enterprise_execution.execute_text_request = (
            original
        )


if __name__ == "__main__":
    main()
