from __future__ import annotations

import json
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from . import api_request
from .api_http import OpusApiHandler
from .api_key_registry import (
    authenticate,
    create_key,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as root:
        registry_path = (
            Path(
                root
            )
            / "api_keys.json"
        )

        secret, client = create_key(
            owner="integration-client",
            environment="test",
            scopes=[
                "text:infer",
            ],
            allowed_routes=[
                "text_inference_route",
            ],
            path=registry_path,
        )

        original_authenticate = (
            api_request.authenticate
        )

        original_execute = (
            api_request.execute_text_request
        )

        captured = {}

        def test_authenticate(
            supplied_secret,
            *,
            required_scope=None,
            required_route=None,
        ):
            return authenticate(
                supplied_secret,
                required_scope=(
                    required_scope
                ),
                required_route=(
                    required_route
                ),
                path=registry_path,
            )

        def test_execute(
            request,
        ):
            captured[
                "request"
            ] = request

            return {
                "id": (
                    "integration-completion"
                ),
                "content": (
                    "opus integration ok"
                ),
                "usage": {
                    "prompt_tokens": 4,
                    "completion_tokens": 3,
                    "total_tokens": 7,
                },
                "lineage": {
                    "owner": "opus",
                    "route": (
                        "text_inference_route"
                    ),
                    "provider": (
                        "integration_provider"
                    ),
                    "model": (
                        "integration_model"
                    ),
                    "policy": (
                        "text_inference_policy"
                    ),
                },
            }

        api_request.authenticate = (
            test_authenticate
        )

        api_request.execute_text_request = (
            test_execute
        )

        server = ThreadingHTTPServer(
            (
                "127.0.0.1",
                0,
            ),
            OpusApiHandler,
        )

        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
        )

        thread.start()

        try:
            host, port = (
                server.server_address
            )

            payload = {
                "model": "opus:auto",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "integration test"
                        ),
                    }
                ],
                "required_capabilities": [],
                "required_layers": [],
            }

            request = urllib.request.Request(
                (
                    f"http://{host}:{port}"
                    "/v1/chat/completions"
                ),
                data=json.dumps(
                    payload
                ).encode(
                    "utf-8"
                ),
                headers={
                    "Authorization": (
                        f"Bearer {secret}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                },
                method="POST",
            )

            with urllib.request.urlopen(
                request,
                timeout=5,
            ) as response:
                assert (
                    response.status
                    == 200
                )

                body = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

            assert body[
                "object"
            ] == "chat.completion"

            assert body[
                "model"
            ] == "integration_model"

            assert body[
                "choices"
            ][
                0
            ][
                "message"
            ] == {
                "role": "assistant",
                "content": (
                    "opus integration ok"
                ),
            }

            assert body[
                "opus"
            ][
                "provider"
            ] == (
                "integration_provider"
            )

            assert body[
                "usage"
            ][
                "total_tokens"
            ] == 7

            assert captured[
                "request"
            ][
                "owner"
            ] == "opus_api"

            assert captured[
                "request"
            ][
                "client_key_id"
            ] == client[
                "key_id"
            ]

            assert captured[
                "request"
            ][
                "requested_model"
            ] == "opus:auto"

            assert captured[
                "request"
            ][
                "messages"
            ] == [
                {
                    "role": "user",
                    "content": (
                        "integration test"
                    ),
                }
            ]

            assert secret not in json.dumps(
                captured[
                    "request"
                ],
                sort_keys=True,
            )

            print(
                "opus api integration: ok"
            )

        finally:
            server.shutdown()

            server.server_close()

            thread.join(
                timeout=5
            )

            api_request.authenticate = (
                original_authenticate
            )

            api_request.execute_text_request = (
                original_execute
            )


if __name__ == "__main__":
    main()
