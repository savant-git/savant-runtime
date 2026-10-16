from __future__ import annotations

import io
from typing import Any

from .deployment import (
    load_config,
)
from .transport_integration import (
    integration_status,
    install,
    make_transport_handler,
)


class fake_headers(dict):
    pass


class fake_canonical_handler:
    def __init__(self) -> None:
        self.path = "/"
        self.command = "GET"
        self.headers = (
            fake_headers()
        )
        self.wfile = (
            io.BytesIO()
        )
        self.response_status = None
        self.response_headers: list[
            tuple[str, str]
        ] = []
        self.ended = False
        self.get_called = False
        self.post_called = False
        self.head_called = False

    def send_response(
        self,
        status: int,
    ) -> None:
        self.response_status = (
            status
        )

    def send_header(
        self,
        name: str,
        value: str,
    ) -> None:
        self.response_headers.append(
            (
                name,
                value,
            )
        )

    def end_headers(
        self,
    ) -> None:
        self.ended = True

    def do_GET(
        self,
    ) -> None:
        self.get_called = True

        self.send_response(
            200
        )

        self.end_headers()

    def do_POST(
        self,
    ) -> None:
        self.post_called = True

        self.send_response(
            200
        )

        self.end_headers()

    def do_HEAD(
        self,
    ) -> None:
        self.head_called = True

        self.send_response(
            200
        )

        self.end_headers()


def fake_factory(
    legacy: Any,
):
    return (
        fake_canonical_handler
    )


def _headers(
    handler: Any,
) -> dict[str, str]:
    return {
        key.casefold():
            value
        for key, value
        in handler.response_headers
    }


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

    hardened = (
        make_transport_handler(
            fake_factory,
            object(),
            config=config,
        )
    )

    get_handler = (
        hardened()
    )

    get_handler.path = (
        "/api/health"
    )

    get_handler.headers = (
        fake_headers(
            {
                "X-Request-ID":
                    "transport-test-get",
            }
        )
    )

    get_handler.do_GET()

    assert (
        get_handler.get_called
        is True
    )

    assert (
        get_handler.response_status
        == 200
    )

    get_headers = _headers(
        get_handler
    )

    assert (
        get_headers[
            "x-palaver-request-id"
        ]
        == "transport-test-get"
    )

    assert (
        get_headers[
            "cache-control"
        ]
        == "no-store, max-age=0"
    )

    assert (
        get_headers[
            "x-content-type-options"
        ]
        == "nosniff"
    )

    oversized = (
        hardened()
    )

    oversized.path = (
        "/api/chat"
    )

    oversized.headers = (
        fake_headers(
            {
                "Content-Type":
                    "application/json",
                "Content-Length":
                    "2048",
            }
        )
    )

    oversized.do_POST()

    assert (
        oversized.post_called
        is False
    )

    assert (
        oversized.response_status
        == 413
    )

    body = (
        oversized
        .wfile
        .getvalue()
        .decode(
            "utf-8"
        )
    )

    assert (
        "request_body_too_large"
        in body
    )

    wrong_media = (
        hardened()
    )

    wrong_media.path = (
        "/api/chat"
    )

    wrong_media.headers = (
        fake_headers(
            {
                "Content-Type":
                    "text/plain",
                "Content-Length":
                    "10",
            }
        )
    )

    wrong_media.do_POST()

    assert (
        wrong_media.post_called
        is False
    )

    assert (
        wrong_media.response_status
        == 415
    )

    forbidden = (
        hardened()
    )

    forbidden.path = (
        "/api/chat"
    )

    forbidden.headers = (
        fake_headers(
            {
                "Content-Type":
                    "application/json",
                "Content-Length":
                    "10",
                "Origin":
                    "https://attacker.example",
            }
        )
    )

    forbidden.do_POST()

    assert (
        forbidden.post_called
        is False
    )

    assert (
        forbidden.response_status
        == 403
    )

    options = (
        hardened()
    )

    options.path = (
        "/api/chat"
    )

    options.headers = (
        fake_headers(
            {
                "Origin":
                    "https://palaver.example",
            }
        )
    )

    options.do_OPTIONS()

    assert (
        options.response_status
        == 204
    )

    option_headers = _headers(
        options
    )

    assert (
        option_headers[
            "access-control-allow-methods"
        ]
        == "GET, HEAD, OPTIONS, POST"
    )

    trace = (
        hardened()
    )

    trace.path = "/"

    trace.headers = (
        fake_headers()
    )

    trace.do_TRACE()

    assert (
        trace.response_status
        == 405
    )

    class fake_server_module:
        make_canonical_handler = (
            staticmethod(
                fake_factory
            )
        )

    module = (
        fake_server_module()
    )

    install(
        module,
        config=config,
    )

    first_factory = (
        module.make_canonical_handler
    )

    install(
        module,
        config=config,
    )

    assert (
        module.make_canonical_handler
        is first_factory
    )

    status = (
        integration_status(
            module
        )
    )

    assert (
        status[
            "installed"
        ]
        is True
    )

    assert (
        status[
            "boundaries"
        ][
            "replaces_canonical_server"
        ]
        is False
    )

    assert (
        status[
            "ownership"
        ][
            "conversation"
        ]
        == "palaver"
    )

    assert (
        status[
            "ownership"
        ][
            "provider"
        ]
        == "opus"
    )

    assert (
        status[
            "authority_effect"
        ]
        == "none"
    )

    print(
        "palaver transport integration: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
