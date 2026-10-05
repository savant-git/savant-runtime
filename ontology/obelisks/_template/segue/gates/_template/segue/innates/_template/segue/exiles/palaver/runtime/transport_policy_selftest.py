from __future__ import annotations

from .deployment import (
    load_config,
)
from .transport_policy import (
    admit,
    forwarded_client,
    public_error,
    response_headers,
)


def main() -> int:
    config = load_config(
        {
            "PALAVER_ENVIRONMENT":
                "production",
            "PALAVER_BIND_HOST":
                "127.0.0.1",
            "PALAVER_WEB_PORT":
                "8787",
            "PALAVER_ALLOWED_ORIGINS":
                "https://palaver.example",
            "PALAVER_REQUEST_BODY_LIMIT_BYTES":
                "1024",
            "PALAVER_ATTACHMENT_LIMIT_BYTES":
                "4096",
            "PALAVER_ATTACHMENT_COUNT_LIMIT":
                "8",
            "PALAVER_CONVERSATION_TIMEOUT_SECONDS":
                "60",
        }
    )

    admitted = admit(
        method="POST",
        target="/api/chat?mode=normal",
        headers={
            "Content-Type":
                "application/json; charset=utf-8",
            "Content-Length":
                "128",
            "Origin":
                "https://palaver.example",
            "X-Request-ID":
                "test-request-1",
        },
        config=config,
    )

    assert admitted.allowed is True
    assert admitted.status == 200
    assert admitted.request_id == "test-request-1"
    assert admitted.path == "/api/chat"

    oversized = admit(
        method="POST",
        target="/api/chat",
        headers={
            "Content-Type":
                "application/json",
            "Content-Length":
                "1025",
        },
        config=config,
    )

    assert oversized.allowed is False
    assert oversized.status == 413

    wrong_type = admit(
        method="POST",
        target="/api/chat",
        headers={
            "Content-Type":
                "text/plain",
            "Content-Length":
                "10",
        },
        config=config,
    )

    assert wrong_type.allowed is False
    assert wrong_type.status == 415

    forbidden_origin = admit(
        method="POST",
        target="/api/chat",
        headers={
            "Content-Type":
                "application/json",
            "Content-Length":
                "10",
            "Origin":
                "https://attacker.example",
        },
        config=config,
    )

    assert forbidden_origin.allowed is False
    assert forbidden_origin.status == 403

    traversal = admit(
        method="GET",
        target="/api/../secret",
        headers={},
        config=config,
    )

    assert traversal.allowed is False
    assert traversal.status == 400

    unsupported_method = admit(
        method="TRACE",
        target="/",
        headers={},
        config=config,
    )

    assert unsupported_method.allowed is False
    assert unsupported_method.status == 405

    headers = response_headers(
        path="/api/chat",
        request_identifier=
            "test-request-1",
        origin=
            "https://palaver.example",
        config=config,
    )

    assert (
        headers[
            "cache-control"
        ]
        == "no-store, max-age=0"
    )

    assert (
        headers[
            "x-content-type-options"
        ]
        == "nosniff"
    )

    assert (
        headers[
            "x-frame-options"
        ]
        == "DENY"
    )

    assert (
        headers[
            "access-control-allow-origin"
        ]
        == "https://palaver.example"
    )

    error = public_error(
        status=500,
        code="palaver_request_failed",
        message=(
            "Palaver could not complete "
            "this request."
        ),
        request_identifier=
            "test-request-1",
    )

    assert (
        "diagnostic"
        not in error
    )

    proxy_config = load_config(
        {
            "PALAVER_ENVIRONMENT":
                "production",
            "PALAVER_BIND_HOST":
                "127.0.0.1",
            "PALAVER_WEB_PORT":
                "8787",
            "PALAVER_REVERSE_PROXY":
                "1",
            "PALAVER_FORWARDED_HEADERS":
                "1",
            "PALAVER_TRUSTED_PROXIES":
                "127.0.0.1,10.0.0.0/8",
            "PALAVER_REQUEST_BODY_LIMIT_BYTES":
                "1024",
            "PALAVER_ATTACHMENT_LIMIT_BYTES":
                "4096",
            "PALAVER_ATTACHMENT_COUNT_LIMIT":
                "8",
            "PALAVER_CONVERSATION_TIMEOUT_SECONDS":
                "60",
        }
    )

    assert (
        forwarded_client(
            peer="127.0.0.1",
            forwarded_for=
                "203.0.113.8, 127.0.0.1",
            config=proxy_config,
        )
        == "203.0.113.8"
    )

    assert (
        forwarded_client(
            peer="192.0.2.9",
            forwarded_for=
                "203.0.113.8",
            config=proxy_config,
        )
        == "192.0.2.9"
    )

    repeat = admit(
        method="POST",
        target="/api/chat?mode=normal",
        headers={
            "Content-Type":
                "application/json",
            "Content-Length":
                "128",
            "Origin":
                "https://palaver.example",
            "X-Request-ID":
                "test-request-1",
        },
        config=config,
    )

    assert (
        repeat.projection()[
            "projection_digest"
        ]
        == admitted.projection()[
            "projection_digest"
        ]
    )

    print(
        "palaver transport policy: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
