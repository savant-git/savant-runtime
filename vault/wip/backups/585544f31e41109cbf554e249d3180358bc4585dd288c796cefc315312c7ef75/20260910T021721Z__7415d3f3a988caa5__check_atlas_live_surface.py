#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
import socket
from typing import Any


schema_version = (
    "savant.assurance."
    "atlas-live-surface-check.v1"
)

authority_effect = "none"

host = "127.0.0.1"
port = 8765

checks = (
    (
        "/atlas/",
        "text/html",
    ),
    (
        "/atlas/assets/atlas.css",
        "text/css",
    ),
    (
        "/atlas/assets/atlas.js",
        "javascript",
    ),
    (
        "/api/atlas/health",
        "application/json",
    ),
    (
        "/api/atlas/summary",
        "application/json",
    ),
)


class LiveCheckError(
    RuntimeError
):
    pass


def request(
    path: str,
) -> tuple[
    int,
    dict[str, str],
    bytes,
]:
    connection = http.client.HTTPConnection(
        host,
        port,
        timeout=5,
    )

    try:
        connection.request(
            "GET",
            path,
            headers={
                "Accept":
                    "*/*",
                "Connection":
                    "close",
            },
        )

        response = connection.getresponse()

        body = response.read()

        headers = {
            key.lower():
                value
            for key, value
            in response.getheaders()
        }

        return (
            response.status,
            headers,
            body,
        )

    finally:
        connection.close()


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise LiveCheckError(
            message
        )


def check_path(
    path: str,
    expected_type: str,
) -> dict[str, Any]:
    (
        status,
        headers,
        body,
    ) = request(
        path
    )

    require(
        status == 200,
        f"{path} returned HTTP {status}",
    )

    content_type = headers.get(
        "content-type",
        "",
    ).lower()

    if expected_type == "javascript":
        require(
            (
                "javascript"
                in content_type
                or "text/plain"
                in content_type
            ),
            f"{path} returned unexpected content type "
            f"{content_type!r}",
        )

    else:
        require(
            expected_type
            in content_type,
            f"{path} returned unexpected content type "
            f"{content_type!r}",
        )

    require(
        len(body) > 0,
        f"{path} returned an empty body",
    )

    result: dict[str, Any] = {
        "status":
            "passed",
        "http_status":
            status,
        "content_type":
            content_type,
        "bytes":
            len(body),
    }

    if expected_type == "application/json":
        try:
            payload = json.loads(
                body.decode(
                    "utf-8"
                )
            )

        except Exception as exc:
            raise LiveCheckError(
                f"{path} did not return valid JSON: {exc}"
            ) from exc

        require(
            isinstance(
                payload,
                dict,
            ),
            f"{path} JSON payload is not an object",
        )

        require(
            payload.get(
                "authority_effect"
            )
            in (
                None,
                "none",
            ),
            f"{path} reports unexpected authority effect",
        )

        require(
            payload.get(
                "mutation_authority"
            )
            in (
                None,
                False,
            ),
            f"{path} reports mutation authority",
        )

        result[
            "json_schema"
        ] = payload.get(
            "schema"
        )

    return result


def main() -> int:
    results: dict[
        str,
        Any,
    ] = {}

    try:
        for (
            path,
            expected_type,
        ) in checks:
            results[
                path
            ] = check_path(
                path,
                expected_type,
            )

    except (
        ConnectionRefusedError,
        socket.timeout,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "blocked",
                    "host":
                        host,
                    "port":
                        port,
                    "checks":
                        results,
                    "error":
                        str(
                            exc
                        ),
                    "reason":
                        "niche taskboard is not reachable "
                        "at the configured local endpoint",
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "host":
                        host,
                    "port":
                        port,
                    "checks":
                        results,
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            {
                "schema":
                    schema_version,
                "authority_effect":
                    authority_effect,
                "status":
                    "passed",
                "host":
                    host,
                "port":
                    port,
                "projection_only":
                    True,
                "mutation_authority":
                    False,
                "checks":
                    results,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
