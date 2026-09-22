#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request


schema = "savant.assurance.diagnose-atlas-frontdoor-500.v1"
authority_effect = "none"
owner = "exile:niche"

frontdoor = "http://127.0.0.1:8765"
upstream = "http://127.0.0.1:8777"


def run(
    *command: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
    )


def fetch(
    url: str,
) -> dict:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Cache-Control": "no-cache",
            "User-Agent": "savant-atlas-diagnostic/1",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            body = response.read(
                4096
            ).decode(
                "utf-8",
                errors="replace",
            )

            return {
                "status":
                    response.status,
                "content_type":
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),
                "server":
                    response.headers.get(
                        "Server",
                        "",
                    ),
                "location":
                    response.headers.get(
                        "Location",
                        "",
                    ),
                "body_prefix":
                    body,
            }

    except urllib.error.HTTPError as exc:
        body = exc.read(
            4096
        ).decode(
            "utf-8",
            errors="replace",
        )

        return {
            "status":
                exc.code,
            "content_type":
                exc.headers.get(
                    "Content-Type",
                    "",
                ),
            "server":
                exc.headers.get(
                    "Server",
                    "",
                ),
            "location":
                exc.headers.get(
                    "Location",
                    "",
                ),
            "body_prefix":
                body,
        }

    except Exception as exc:
        return {
            "status": None,
            "error": repr(exc),
        }


def nginx_atlas_context() -> list[dict]:
    process = run(
        "nginx",
        "-T",
    )

    combined = (
        process.stdout
        + "\n"
        + process.stderr
    )

    lines = combined.splitlines()

    results = []

    for index, line in enumerate(
        lines
    ):
        if (
            "atlas"
            not in line.lower()
            and "8765"
            not in line
        ):
            continue

        start = max(
            0,
            index - 6,
        )

        end = min(
            len(lines),
            index + 12,
        )

        context = "\n".join(
            lines[start:end]
        )

        if any(
            context
            == existing[
                "context"
            ]
            for existing in results
        ):
            continue

        results.append(
            {
                "line":
                    index + 1,
                "context":
                    context,
            }
        )

    return results


def nginx_error_log() -> dict:
    candidates = (
        "/var/log/nginx/error.log",
        "/var/log/nginx/savant-error.log",
    )

    result = {}

    for path in candidates:
        process = run(
            "tail",
            "-n",
            "80",
            path,
        )

        if process.returncode != 0:
            continue

        relevant = []

        for line in process.stdout.splitlines():
            lowered = line.lower()

            if (
                "atlas"
                in lowered
                or "8777"
                in lowered
                or "8765"
                in lowered
                or "rewrite"
                in lowered
                or "internal redirection"
                in lowered
                or "upstream"
                in lowered
            ):
                relevant.append(
                    line
                )

        result[
            path
        ] = relevant[-30:]

    journal = run(
        "journalctl",
        "-u",
        "nginx.service",
        "-n",
        "80",
        "--no-pager",
        "-o",
        "cat",
    )

    if journal.returncode == 0:
        result[
            "journal"
        ] = [
            line
            for line
            in journal.stdout.splitlines()
            if (
                "atlas"
                in line.lower()
                or "8777"
                in line
                or "8765"
                in line
                or "rewrite"
                in line.lower()
                or "upstream"
                in line.lower()
                or "error"
                in line.lower()
            )
        ][-30:]

    return result


def main() -> int:
    upstream_checks = {
        "/":
            fetch(
                upstream + "/"
            ),
        "/atlas.css":
            fetch(
                upstream
                + "/atlas.css"
            ),
        "/atlas.js":
            fetch(
                upstream
                + "/atlas.js"
            ),
        "/atlas.json":
            fetch(
                upstream
                + "/atlas.json"
            ),
    }

    frontdoor_checks = {
        "/atlas":
            fetch(
                frontdoor
                + "/atlas"
            ),
        "/atlas/":
            fetch(
                frontdoor
                + "/atlas/"
            ),
        "/atlas/atlas.css":
            fetch(
                frontdoor
                + "/atlas/atlas.css"
            ),
        "/atlas/atlas.js":
            fetch(
                frontdoor
                + "/atlas/atlas.js"
            ),
        "/atlas/atlas.json":
            fetch(
                frontdoor
                + "/atlas/atlas.json"
            ),
    }

    result = {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "status":
            "diagnosed",
        "upstream":
            upstream_checks,
        "frontdoor":
            frontdoor_checks,
        "nginx_context":
            nginx_atlas_context(),
        "nginx_errors":
            nginx_error_log(),
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
