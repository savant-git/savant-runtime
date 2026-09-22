#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
from typing import Any


schema_version = (
    "savant.assurance."
    "atlas-live-surface-check.v3"
)

authority_effect = "none"

host = "127.0.0.1"
port = 8765


class LiveCheckError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise LiveCheckError(
            message
        )


def request(
    method: str,
    path: str,
) -> tuple[
    int,
    dict[str, str],
    bytes,
]:
    connection = http.client.HTTPConnection(
        host,
        port,
        timeout=30,
    )

    try:
        connection.request(
            method,
            path,
            headers={
                "Accept": "*/*",
                "Connection": "close",
            },
        )

        response = connection.getresponse()
        body = response.read()

        headers = {
            key.lower(): value
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


def check_frontend() -> dict[str, Any]:
    status, headers, body = request(
        "GET",
        "/atlas/",
    )

    require(
        status == 200,
        f"/atlas/ returned HTTP {status}",
    )

    content_type = headers.get(
        "content-type",
        "",
    ).lower()

    require(
        "text/html" in content_type,
        "Atlas frontend is not HTML",
    )

    text = body.decode(
        "utf-8"
    )

    require(
        'data-savant-atlas-inline="true"'
        in text,
        "Atlas inline composition unavailable",
    )

    require(
        "<canvas"
        in text.lower(),
        "Atlas canvas unavailable",
    )

    require(
        "atlas.js"
        in text
        or "requestAnimationFrame"
        in text,
        "Atlas JavaScript substance unavailable",
    )

    require(
        "sha256-"
        in headers.get(
            "content-security-policy",
            "",
        ),
        "Atlas CSP hash unavailable",
    )

    return {
        "status":
            "passed",
        "http_status":
            status,
        "bytes":
            len(body),
        "content_type":
            content_type,
        "delivery":
            "inline-composed",
    }


def check_json(
    path: str,
) -> dict[str, Any]:
    status, headers, body = request(
        "GET",
        path,
    )

    require(
        status == 200,
        f"{path} returned HTTP {status}",
    )

    content_type = headers.get(
        "content-type",
        "",
    ).lower()

    require(
        "application/json"
        in content_type,
        f"{path} is not JSON",
    )

    payload = json.loads(
        body.decode(
            "utf-8"
        )
    )

    require(
        isinstance(payload, dict),
        f"{path} did not return an object",
    )

    require(
        payload.get(
            "authority_effect"
        ) in (
            None,
            "none",
        ),
        f"{path} acquired authority effect",
    )

    require(
        payload.get(
            "mutation_authority"
        ) in (
            None,
            False,
        ),
        f"{path} acquired mutation authority",
    )

    return {
        "status":
            "passed",
        "http_status":
            status,
        "bytes":
            len(body),
        "content_type":
            content_type,
        "schema":
            payload.get(
                "schema"
            ),
    }


def check_mutation() -> dict[str, Any]:
    status, _, body = request(
        "POST",
        "/api/atlas",
    )

    require(
        status == 405,
        "Atlas mutation boundary "
        f"returned HTTP {status}",
    )

    payload = json.loads(
        body.decode(
            "utf-8"
        )
    )

    require(
        payload.get(
            "mutation_authority"
        )
        is False,
        "Atlas mutation rejection is invalid",
    )

    return {
        "status":
            "passed",
        "http_status":
            status,
        "mutation_authority":
            False,
    }


def main() -> int:
    checks: dict[
        str,
        Any,
    ] = {}

    try:
        checks[
            "frontend"
        ] = check_frontend()

        checks[
            "health"
        ] = check_json(
            "/api/atlas/health"
        )

        checks[
            "summary"
        ] = check_json(
            "/api/atlas/summary"
        )

        checks[
            "mutation"
        ] = check_mutation()

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
                        checks,
                    "error":
                        str(exc),
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
                "delivery":
                    "inline-composed",
                "checks":
                    checks,
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
