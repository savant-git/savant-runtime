from __future__ import annotations

from .api_http import (
    MAX_AUTHORIZATION_BYTES,
    MAX_REQUEST_BYTES,
    ApiHttpError,
    OpusApiServer,
    _content_type,
    _request_id,
    bearer_secret,
    openai_chat_response,
)


def main() -> None:
    assert (
        _content_type(
            "application/json; charset=utf-8"
        )
        == "application/json"
    )

    assert (
        MAX_REQUEST_BYTES
        == 4 * 1024 * 1024
    )

    assert (
        MAX_AUTHORIZATION_BYTES
        == 8192
    )

    assert (
        bearer_secret(
            "Bearer opus_test_secret"
        )
        == "opus_test_secret"
    )

    failed = False

    try:
        bearer_secret(
            "Bearer "
            + (
                "x"
                * (
                    MAX_AUTHORIZATION_BYTES
                    + 1
                )
            )
        )

    except ApiHttpError as exc:
        failed = True

        assert exc.status == 401

        assert (
            exc.error_type
            == "authentication_error"
        )

    assert failed

    supplied = _request_id(
        "client-request-123"
    )

    assert (
        supplied
        == "client-request-123"
    )

    generated = _request_id(
        "invalid request id"
    )

    assert generated.startswith(
        "opusreq_"
    )

    response = (
        openai_chat_response(
            {
                "content": "ok",
                "lineage": {
                    "route": (
                        "text_inference_route"
                    ),
                    "provider": "test",
                    "model": "test-model",
                },
            },
            requested_model="opus:auto",
            request_id=(
                "client-request-123"
            ),
        )
    )

    assert (
        response[
            "opus"
        ][
            "request_id"
        ]
        == "client-request-123"
    )

    assert (
        response[
            "opus"
        ][
            "authority_effect"
        ]
        == "none"
    )

    assert (
        OpusApiServer.daemon_threads
        is True
    )

    assert (
        OpusApiServer.allow_reuse_address
        is True
    )

    print(
        "opus api http enterprise: ok"
    )


if __name__ == "__main__":
    main()
