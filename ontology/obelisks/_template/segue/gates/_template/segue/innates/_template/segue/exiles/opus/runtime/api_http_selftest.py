from __future__ import annotations

from . import api_http


def main() -> None:
    assert api_http.bearer_secret(
        "Bearer opus_test_example"
    ) == "opus_test_example"

    failed = False

    try:
        api_http.bearer_secret(
            None
        )

    except api_http.ApiHttpError as exc:
        failed = True

        assert exc.status == 401

    assert failed

    original_execute = (
        api_http.execute_authenticated_text
    )

    captured = {}

    try:
        def fake_execute(
            *,
            secret,
            payload,
        ):
            captured[
                "secret"
            ] = secret

            captured[
                "payload"
            ] = payload

            return {
                "id": "completion-test",
                "content": "hello from opus",
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 3,
                    "total_tokens": 6,
                },
                "lineage": {
                    "owner": "opus",
                    "route": (
                        "text_inference_route"
                    ),
                    "provider": (
                        "test_provider"
                    ),
                    "model": (
                        "test_model"
                    ),
                },
            }

        api_http.execute_authenticated_text = (
            fake_execute
        )

        response = (
            api_http.dispatch_chat_completion(
                authorization=(
                    "Bearer opus_test_example"
                ),
                payload={
                    "model": "opus:auto",
                    "messages": [
                        {
                            "role": "user",
                            "content": "hello",
                        }
                    ],
                },
            )
        )

    finally:
        api_http.execute_authenticated_text = (
            original_execute
        )

    assert captured[
        "secret"
    ] == "opus_test_example"

    assert captured[
        "payload"
    ][
        "model"
    ] == "opus:auto"

    assert response[
        "object"
    ] == "chat.completion"

    assert response[
        "model"
    ] == "test_model"

    assert response[
        "choices"
    ][
        0
    ][
        "message"
    ] == {
        "role": "assistant",
        "content": "hello from opus",
    }

    assert response[
        "opus"
    ][
        "provider"
    ] == "test_provider"

    assert response[
        "opus"
    ][
        "authority_effect"
    ] == "none"

    assert response[
        "usage"
    ][
        "total_tokens"
    ] == 6

    print(
        "opus api http compatibility: ok"
    )


if __name__ == "__main__":
    main()
