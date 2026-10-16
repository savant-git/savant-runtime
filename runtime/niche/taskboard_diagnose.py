#!/usr/bin/env python3
"""
savant / niche
bounded taskboard failure capture

owner: exile:niche
authority_effect: none

Starts the current Niche taskboard on an isolated loopback port,
performs read-only HTTP probes, captures exactly what the current
server emits, terminates it, and prints a structured diagnostic report.

This file does not modify task state, authority, history, evidence,
receipts, or projections.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SAVANT_ROOT = Path("/root/savant-runtime")

SERVER = (
    SAVANT_ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "niche"
    / "apps"
    / "taskboard"
    / "server.py"
)

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 2001

PROBES = (
    ("health", "/api/health"),
    ("tasks", "/api/tasks?include_terminal=true"),
    ("dashboard", "/api/dashboard"),
    ("state", "/api/state"),
    ("history", "/api/history"),
    ("living", "/api/living"),
    ("fabric", "/api/living/fabric"),
    ("command", "/assets/command.html"),
)


def compact_body(
    raw: bytes,
    limit: int = 12000,
) -> str:
    text = raw.decode(
        "utf-8",
        errors="replace",
    )

    if len(text) <= limit:
        return text

    return (
        text[:limit]
        + "\n...[diagnostic body truncated]..."
    )


def probe(
    base_url: str,
    name: str,
    path: str,
    timeout: float,
) -> dict[str, Any]:
    url = base_url + path

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": (
                "application/json,"
                " text/html;q=0.9,"
                " */*;q=0.8"
            ),
            "User-Agent": (
                "savant-niche-diagnostic/1"
            ),
            "Cache-Control": "no-cache",
        },
    )

    started = time.monotonic()

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            body = response.read()

            return {
                "name": name,
                "path": path,
                "url": url,
                "ok": True,
                "status": response.status,
                "content_type": (
                    response.headers.get(
                        "Content-Type"
                    )
                ),
                "elapsed_ms": round(
                    (
                        time.monotonic()
                        - started
                    )
                    * 1000,
                    3,
                ),
                "body": compact_body(body),
            }

    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except Exception as body_exc:
            body = (
                f"<unable to read response body: "
                f"{body_exc}>"
            ).encode(
                "utf-8",
                errors="replace",
            )

        return {
            "name": name,
            "path": path,
            "url": url,
            "ok": False,
            "status": exc.code,
            "reason": str(exc.reason),
            "content_type": (
                exc.headers.get(
                    "Content-Type"
                )
                if exc.headers
                else None
            ),
            "elapsed_ms": round(
                (
                    time.monotonic()
                    - started
                )
                * 1000,
                3,
            ),
            "body": compact_body(body),
        }

    except Exception as exc:
        return {
            "name": name,
            "path": path,
            "url": url,
            "ok": False,
            "status": None,
            "error_type": (
                type(exc).__name__
            ),
            "error": str(exc),
            "elapsed_ms": round(
                (
                    time.monotonic()
                    - started
                )
                * 1000,
                3,
            ),
        }


def wait_for_server(
    process: subprocess.Popen[str],
    base_url: str,
    timeout: float,
) -> dict[str, Any]:
    deadline = (
        time.monotonic()
        + timeout
    )

    attempts = 0
    last_result: dict[str, Any] = {}

    while (
        time.monotonic()
        < deadline
    ):
        attempts += 1

        if (
            process.poll()
            is not None
        ):
            return {
                "ready": False,
                "reason": (
                    "server process exited "
                    "before readiness"
                ),
                "returncode": (
                    process.returncode
                ),
                "attempts": attempts,
                "last_probe": last_result,
            }

        last_result = probe(
            base_url,
            "readiness",
            "/api/living",
            timeout=1.0,
        )

        if (
            last_result.get("status")
            is not None
        ):
            return {
                "ready": True,
                "attempts": attempts,
                "last_probe": last_result,
            }

        time.sleep(0.15)

    return {
        "ready": False,
        "reason": (
            "readiness timeout"
        ),
        "attempts": attempts,
        "last_probe": last_result,
    }


def stop_process(
    process: subprocess.Popen[str],
) -> tuple[str, str]:
    if (
        process.poll()
        is None
    ):
        process.terminate()

    try:
        stdout, stderr = (
            process.communicate(
                timeout=4
            )
        )
    except subprocess.TimeoutExpired:
        process.kill()

        stdout, stderr = (
            process.communicate(
                timeout=4
            )
        )

    return (
        stdout or "",
        stderr or "",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture current Niche "
            "taskboard GET failures."
        )
    )

    parser.add_argument(
        "--bind",
        default=DEFAULT_BIND,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
    )

    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=8.0,
    )

    parser.add_argument(
        "--request-timeout",
        type=float,
        default=5.0,
    )

    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": (
            "savant.niche."
            "taskboard-diagnostic.v1"
        ),
        "authority_effect": "none",
        "mutation_effect": "none",
        "server": str(SERVER),
        "bind": args.bind,
        "port": args.port,
        "probes": [],
    }

    if not SERVER.is_file():
        report["ok"] = False
        report["failure"] = (
            "current taskboard server "
            "file is absent"
        )

        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )

        return 2

    command = [
        sys.executable,
        str(SERVER),
        "--bind",
        args.bind,
        "--port",
        str(args.port),
    ]

    process: subprocess.Popen[str] | None = None

    try:
        process = subprocess.Popen(
            command,
            cwd=str(SAVANT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        base_url = (
            f"http://{args.bind}:"
            f"{args.port}"
        )

        readiness = wait_for_server(
            process,
            base_url,
            args.startup_timeout,
        )

        report["readiness"] = (
            readiness
        )

        if readiness.get("ready"):
            for name, path in PROBES:
                report["probes"].append(
                    probe(
                        base_url,
                        name,
                        path,
                        args.request_timeout,
                    )
                )

        report["process_returncode_before_stop"] = (
            process.poll()
        )

    except Exception as exc:
        report["launcher_error"] = {
            "type": (
                type(exc).__name__
            ),
            "message": str(exc),
        }

    finally:
        if process is not None:
            try:
                stdout, stderr = (
                    stop_process(
                        process
                    )
                )

                report["server_stdout"] = (
                    stdout
                )

                report["server_stderr"] = (
                    stderr
                )

                report["process_returncode"] = (
                    process.returncode
                )

            except Exception as exc:
                report[
                    "termination_error"
                ] = {
                    "type": (
                        type(exc).__name__
                    ),
                    "message": str(exc),
                }

    failed = [
        item
        for item in report["probes"]
        if not item.get("ok")
    ]

    report["summary"] = {
        "probe_count": len(
            report["probes"]
        ),
        "failed_count": len(
            failed
        ),
        "failed": [
            {
                "name": item.get(
                    "name"
                ),
                "status": item.get(
                    "status"
                ),
                "error": (
                    item.get("error")
                    or item.get("reason")
                ),
            }
            for item in failed
        ],
    }

    report["ok"] = (
        bool(
            report.get(
                "readiness",
                {},
            ).get("ready")
        )
        and not failed
    )

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if report["ok"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
