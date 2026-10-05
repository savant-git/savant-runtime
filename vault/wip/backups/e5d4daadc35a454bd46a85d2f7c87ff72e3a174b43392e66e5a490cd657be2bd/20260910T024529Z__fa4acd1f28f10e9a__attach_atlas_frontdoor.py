#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


schema = "savant.assurance.attach-atlas-frontdoor.v1"
authority_effect = "none"

target = Path(
    "/etc/nginx/sites-enabled/savant-present"
)

listen_port = 8765

marker_begin = (
    "    # savant-atlas-begin\n"
)

marker_end = (
    "    # savant-atlas-end\n"
)

atlas_upstream = (
    "http://127.0.0.1:8777"
)


class AtlasFrontdoorError(
    RuntimeError
):
    pass


def run(
    *command: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
    )


def brace_pairs(
    text: str,
) -> dict[int, int]:
    stack: list[int] = []
    pairs: dict[int, int] = {}

    quote: str | None = None
    escaped = False
    comment = False

    for index, char in enumerate(
        text
    ):
        if comment:
            if char == "\n":
                comment = False
            continue

        if quote is not None:
            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char == quote:
                quote = None

            continue

        if char == "#":
            comment = True
            continue

        if char in (
            '"',
            "'",
        ):
            quote = char
            continue

        if char == "{":
            stack.append(
                index
            )
            continue

        if char == "}":
            if not stack:
                raise AtlasFrontdoorError(
                    "unbalanced nginx braces"
                )

            opening = stack.pop()

            pairs[
                opening
            ] = index

    if stack:
        raise AtlasFrontdoorError(
            "unbalanced nginx braces"
        )

    return pairs


def server_blocks(
    text: str,
) -> list[
    tuple[
        int,
        int,
        str,
    ]
]:
    pairs = brace_pairs(
        text
    )

    result = []

    for match in re.finditer(
        r"\bserver\s*\{",
        text,
    ):
        opening = text.find(
            "{",
            match.start(),
            match.end(),
        )

        closing = pairs.get(
            opening
        )

        if closing is None:
            continue

        result.append(
            (
                match.start(),
                closing + 1,
                text[
                    match.start():
                    closing + 1
                ],
            )
        )

    return result


def listens_on_target(
    block: str,
) -> bool:
    patterns = (
        rf"\blisten\s+{listen_port}\b",
        rf"\blisten\s+[^;:\s]+:{listen_port}\b",
        rf"\blisten\s+[^]+\]:{listen_port}\b",
    )

    return any(
        re.search(
            pattern,
            block,
        )
        for pattern in patterns
    )


def remove_existing_atlas(
    text: str,
) -> str:
    while marker_begin in text:
        begin = text.find(
            marker_begin
        )

        end = text.find(
            marker_end,
            begin,
        )

        if end < 0:
            raise AtlasFrontdoorError(
                "Atlas begin marker exists "
                "without matching end marker"
            )

        end += len(
            marker_end
        )

        text = (
            text[:begin]
            + text[end:]
        )

    return text


def locate_server(
    text: str,
) -> tuple[
    int,
    int,
    str,
]:
    candidates = [
        block
        for block in server_blocks(
            text
        )
        if listens_on_target(
            block[2]
        )
    ]

    if len(candidates) != 1:
        raise AtlasFrontdoorError(
            "expected exactly one nginx "
            f"server listening on {listen_port}; "
            f"found {len(candidates)}"
        )

    return candidates[0]


def atlas_block() -> str:
    return (
        "    # savant-atlas-begin\n"
        "    location = /atlas {\n"
        "        return 308 /atlas/;\n"
        "    }\n"
        "\n"
        "    location ^~ /atlas/ {\n"
        f"        proxy_pass {atlas_upstream}/;\n"
        "        proxy_http_version 1.1;\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For "
        "$proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "        proxy_set_header Connection \"\";\n"
        "        proxy_buffering off;\n"
        "        proxy_read_timeout 30s;\n"
        "        add_header Cache-Control "
        "\"no-store\" always;\n"
        "        add_header X-Content-Type-Options "
        "\"nosniff\" always;\n"
        "    }\n"
        "    # savant-atlas-end\n"
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=(
                path.name
                + "."
            ),
            suffix=".tmp",
            dir=str(
                path.parent
            ),
        )
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def validate_nginx() -> None:
    process = run(
        "nginx",
        "-t",
    )

    if process.returncode != 0:
        raise AtlasFrontdoorError(
            (
                process.stdout
                + process.stderr
            ).strip()
        )


def require_atlas_upstream() -> None:
    process = run(
        "curl",
        "-fsS",
        "--max-time",
        "5",
        f"{atlas_upstream}/atlas.json",
        "-o",
        "/dev/null",
    )

    if process.returncode != 0:
        raise AtlasFrontdoorError(
            "verified Atlas upstream "
            "127.0.0.1:8777 is not reachable"
        )


def migrate(
    apply: bool,
) -> dict:
    if not target.is_file():
        raise AtlasFrontdoorError(
            f"missing nginx target: {target}"
        )

    require_atlas_upstream()

    original = target.read_text(
        encoding="utf-8"
    )

    clean = remove_existing_atlas(
        original
    )

    _, end, _ = locate_server(
        clean
    )

    insertion = end - 1

    transformed = (
        clean[:insertion]
        + "\n"
        + atlas_block()
        + clean[insertion:]
    )

    changed = (
        transformed
        != original
    )

    if apply and changed:
        atomic_write(
            target,
            transformed,
        )

        try:
            validate_nginx()

            reload_process = run(
                "nginx",
                "-s",
                "reload",
            )

            if (
                reload_process.returncode
                != 0
            ):
                raise AtlasFrontdoorError(
                    (
                        reload_process.stdout
                        + reload_process.stderr
                    ).strip()
                )

        except Exception:
            atomic_write(
                target,
                original,
            )

            validate_nginx()

            run(
                "nginx",
                "-s",
                "reload",
            )

            raise

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "apply":
            apply,
        "changed":
            changed,
        "target":
            str(target),
        "listen_port":
            listen_port,
        "route":
            "/atlas/",
        "upstream":
            atlas_upstream,
        "projection_source":
            "/atlas/atlas
