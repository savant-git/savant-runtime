#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(
    "/root/savant-runtime"
)

SEARCH_FABRIC = (
    ROOT
    / "runtime"
    / "palaver"
    / "search"
    / "search_fabric.py"
)


class PalaverDirectCommandError(
    RuntimeError
):
    pass


def _json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _search(
    query: str,
) -> dict[str, Any]:
    query = str(
        query
    ).strip()

    if not query:
        return {
            "query": "",
            "count": 0,
            "results": [],
        }

    if not SEARCH_FABRIC.is_file():
        raise PalaverDirectCommandError(
            "Palaver search fabric missing: "
            + str(
                SEARCH_FABRIC
            )
        )

    result = subprocess.run(
        [
            sys.executable,
            str(
                SEARCH_FABRIC
            ),
            query,
        ],
        cwd=str(
            ROOT
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )

    if result.returncode != 0:
        raise PalaverDirectCommandError(
            "Palaver search fabric failed: "
            + result.stderr[
                -2000:
            ].strip()
        )

    output = result.stdout.strip()

    if not output:
        return {
            "query": query,
            "count": 0,
            "results": [],
        }

    try:
        payload = json.loads(
            output
        )
    except json.JSONDecodeError as exc:
        raise PalaverDirectCommandError(
            "Palaver search fabric returned "
            "invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise PalaverDirectCommandError(
            "Palaver search fabric returned "
            "non-object payload"
        )

    return payload


def _retrieve(
    query: str,
) -> dict[str, Any]:
    from scrybe_bridge import (
        hydrate,
    )

    query = str(
        query
    ).strip()

    if not query:
        return {
            "query": "",
            "memories": [],
            "memory_count": 0,
            "owner": "scrybe",
            "authoritative": False,
        }

    packet = hydrate(
        query,
        limit=30,
    )

    if not isinstance(
        packet,
        dict,
    ):
        raise PalaverDirectCommandError(
            "Scrybe returned invalid "
            "retrieval packet"
        )

    return packet


def install(
    legacy: ModuleType,
) -> None:
    original = getattr(
        legacy,
        "direct_command",
        None,
    )

    if not callable(
        original
    ):
        raise PalaverDirectCommandError(
            "legacy Palaver direct_command "
            "is unavailable"
        )

    from tool_broker import bind

    bind(
        legacy
    )

    def direct_command_through_palaver(
        message: str,
    ):
        text = str(
            message
        )

        low = (
            text.lower()
            .strip()
        )

        if low == "files":
            payload = (
                legacy
                .list_directory_payload(
                    ""
                )
            )

            return {
                "answer": _json(
                    payload
                ),
                "trace": (
                    "palaver bounded "
                    "filesystem list"
                ),
            }

        if low.startswith(
            "file read "
        ):
            target = text[
                len(
                    "file read "
                ):
            ].strip()

            payload = (
                legacy
                .read_file_payload(
                    target
                )
            )

            return {
                "answer": _json(
                    payload
                ),
                "trace": (
                    "palaver bounded "
                    "filesystem read"
                ),
            }

        if low.startswith(
            "search "
        ):
            query = text[
                len(
                    "search "
                ):
            ].strip()

            return {
                "answer": _json(
                    _search(
                        query
                    )
                ),
                "trace": (
                    "palaver search fabric"
                ),
            }

        if low.startswith(
            "retrieve "
        ):
            query = text[
                len(
                    "retrieve "
                ):
            ].strip()

            return {
                "answer": _json(
                    _retrieve(
                        query
                    )
                ),
                "trace": (
                    "scrybe retrieval"
                ),
            }

        if low == "graph":
            payload = (
                legacy
                .graph_snapshot()
            )

            return {
                "answer": _json(
                    payload
                ),
                "trace": (
                    "palaver graph snapshot"
                ),
            }

        if low == "patches":
            payload = (
                legacy
                .patch_review_pending_payload()
            )

            return {
                "answer": _json(
                    payload
                ),
                "trace": (
                    "palaver patch-review "
                    "pending"
                ),
            }

        return original(
            message
        )

    legacy.direct_command = (
        direct_command_through_palaver
    )


def status() -> dict[str, Any]:
    from tool_broker import (
        status as broker_status,
    )

    return {
        "schema": (
            "savant://palaver/"
            "direct-command-bridge/1.1.0"
        ),
        "owner": "palaver",
        "filesystem_owner": "palaver",
        "search_owner": "palaver",
        "retrieval_owner": "scrybe",
        "mutation_owner": "coda",
        "patch_review_owner": "palaver",
        "bounded_filesystem": True,
        "unrestricted_shell": False,
        "legacy_root_tool_binaries": False,
        "search_fabric": str(
            SEARCH_FABRIC
        ),
        "search_fabric_present": (
            SEARCH_FABRIC.is_file()
        ),
        "tool_broker": (
            broker_status()
        ),
        "authority_effect": "none",
    }


def main() -> int:
    print(
        _json(
            status()
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
