#!/usr/bin/env python3

from __future__ import annotations

import http.client
import json
from typing import Any


schema_version = (
    "savant.assurance."
    "atlas-live-surface-check.v2"
)

authority_effect = "none"

host = "127.0.0.1"
port = 8765


class LiveCheckError(
    RuntimeError
):
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
        timeout=15,
    )

    try:
        connection.request(
            method,
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


def check_frontend() -> dict[str, Any]:
    (
        status,
        headers,
        body,
    ) = request(
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
        "text/html"
        in content_type,
        "Atlas frontend is not HTML",
    )

    text = body.decode(
        "utf-8"
    )

    require(
        'id="atlas-canvas"'
        in text,
        "Atlas canvas unavailable",
    )

    require(
        'id="atlas-minimap"'
        in text,
        "Atlas minimap unavailable",
    )

    require(
        'id="atlas-inspector"'
        in text,
        "Atlas inspector unavailable",
    )

    require(
        "<style>"
        in text,
        "Atlas stylesheet was not bundled",
    )

    require(
        "<script>"
        in text,
        "Atlas JavaScript was not bundled",
    )

    require(
        'href="/atlas/assets/atlas.css"'
        not in text,
        "Atlas still depends on external stylesheet routing",
    )

    require(
        'src="/atlas/assets/atlas.js"'
        not in text,
        "Atlas still depends on external JavaScript routing",
    )

    require(
        'fetch("/api/atlas"'
        in text,
        "Atlas projection client unavailable",
    )

    csp = headers.get(
        "content-security-policy",
        "",
    )

    require(
        "sha256-"
        in csp,
        "Atlas bundled frontend lacks hashed CSP authorization",
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
            "single-document-bundle",
        "hashed_csp":
            True,
    }


def check_json(
    path: str,
) -> dict[str, Any]:
    (
        status,
        headers,
        body,
    ) = request(
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
        isinstance(
            payload,
            dict,
        ),
        f"{path} payload is not an object",
    )

    require(
        payload.get(
            "authority_effect"
        )
        in (
            None,
            "none",
        ),
        f"{path} acquired authority effect",
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


def check_mutation_boundary() -> dict[str, Any]:
    status, _, body = request(
        "POST",
        "/api/atlas",
    )

    require(
        status == 405,
        "Atlas POST mutation boundary "
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
        "Atlas mutation rejection lost authority boundary",
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
            "/api/atlas/health"
        ] = check_json(
            "/api/atlas/health"
        )

        checks[
            "/api/atlas/summary"
        ] = check_json(
            "/api/atlas/summary"
        )

        checks[
            "mutation_boundary"
        ] = check_mutation_boundary()

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
                "delivery":
                    "single-document-bundle",
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
