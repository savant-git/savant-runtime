#!/usr/bin/env python3

from __future__ import annotations

import json
import urllib.error
import urllib.request


schema = "savant.assurance.atlas-frontdoor-check.v1"
authority_effect = "none"
owner = "exile:niche"

base = "http://127.0.0.1:8765"


class AtlasFrontdoorCheckError(
    RuntimeError
):
    pass


def fetch(
    path: str,
    expected_type: str,
) -> dict:
    request = urllib.request.Request(
        base + path,
        method="GET",
        headers={
            "Cache-Control":
                "no-cache",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            status = response.status
            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )
            body = response.read()

    except urllib.error.HTTPError as exc:
        raise AtlasFrontdoorCheckError(
            f"{path} returned HTTP {exc.code}"
        ) from exc

    except urllib.error.URLError as exc:
        raise AtlasFrontdoorCheckError(
            f"{path} failed: {exc}"
        ) from exc

    if status != 200:
        raise AtlasFrontdoorCheckError(
            f"{path} returned HTTP {status}"
        )

    if expected_type not in content_type:
        raise AtlasFrontdoorCheckError(
            f"{path} returned unexpected "
            f"content type {content_type!r}"
        )

    if not body:
        raise AtlasFrontdoorCheckError(
            f"{path} returned empty body"
        )

    return {
        "status":
            status,
        "content_type":
            content_type,
        "bytes":
            len(body),
    }


def main() -> int:
    try:
        checks = {
            "index":
                fetch(
                    "/atlas/",
                    "text/html",
                ),
            "css":
                fetch(
                    "/atlas/atlas.css",
                    "text/css",
                ),
            "javascript":
                fetch(
                    "/atlas/atlas.js",
                    "javascript",
                ),
            "bridge":
                fetch(
                    "/atlas/atlas-static-bridge.js",
                    "javascript",
                ),
            "projection":
                fetch(
                    "/atlas/atlas.json",
                    "application/json",
                ),
        }

        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "owner":
                        owner,
                    "status":
                        "passed",
                    "route":
                        "/atlas/",
                    "projection_only":
                        True,
                    "mutation_authority":
                        False,
                    "checks":
                        checks,
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "owner":
                        owner,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
