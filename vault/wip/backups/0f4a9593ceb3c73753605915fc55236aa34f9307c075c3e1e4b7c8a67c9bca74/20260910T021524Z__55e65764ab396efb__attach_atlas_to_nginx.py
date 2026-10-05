#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "attach-atlas-to-nginx.v3"
)

authority_effect = "none"
listen_port = 8765

atlas_marker_begin = (
    "    # savant-atlas-begin\n"
)

atlas_marker_end = (
    "    # savant-atlas-end\n"
)

atlas_locations = (
    "    # savant-atlas-begin\n"
    "    location = /atlas {\n"
    "        return 308 /atlas/;\n"
    "    }\n"
    "\n"
    "    location ^~ /atlas/ {\n"
    "        proxy_pass http://127.0.0.1:8766/;\n"
    "        proxy_http_version 1.1;\n"
    "        proxy_set_header Host $host;\n"
    "        proxy_set_header X-Real-IP $remote_addr;\n"
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    "    }\n"
    "\n"
    "    location ^~ /api/atlas {\n"
    "        proxy_pass http://127.0.0.1:8766;\n"
    "        proxy_http_version 1.1;\n"
    "        proxy_set_header Host $host;\n"
    "        proxy_set_header X-Real-IP $remote_addr;\n"
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    "    }\n"
    "    # savant-atlas-end\n"
)


class MigrationError(RuntimeError):
    pass


def nginx_dump() -> str:
    process = subprocess.run(
        ["nginx", "-T"],
        capture_output=True,
        text=True,
    )

    output = (
        process.stdout
        + process.stderr
    )

    if process.returncode != 0:
        raise MigrationError(
            "nginx -T failed: "
            + output.strip()
        )

    return output


def configuration_sections(
    dump: str,
) -> list[tuple[Path, str]]:
    marker = re.compile(
        r"^# configuration file (.+?):\n",
        re.MULTILINE,
    )

    matches = list(
        marker.finditer(dump)
    )

    sections: list[
        tuple[Path, str]
    ] = []

    for index, match in enumerate(
        matches
    ):
        start = match.end()

        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(dump)
        )

        sections.append(
            (
                Path(match.group(1)),
                dump[start:end],
            )
        )

    return sections


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

        if char in ('"', "'"):
            quote = char
            continue

        if char == "{":
            stack.append(index)
            continue

        if char == "}":
            if not stack:
                raise MigrationError(
                    "unbalanced nginx braces"
                )

            opening = stack.pop()
            pairs[opening] = index

    if stack:
        raise MigrationError(
            "unbalanced nginx braces"
        )

    return pairs


def server_blocks(
    text: str,
) -> list[tuple[int, int, str]]:
    pairs = brace_pairs(text)

    blocks = []

    for match in re.finditer(
        r"\bserver\s*\{",
        text,
    ):
        opening = text.find(
            "{",
            match.start(),
            match.end(),
        )

        closing = pairs.get(opening)

        if closing is None:
            continue

        blocks.append(
            (
                match.start(),
                closing + 1,
                text[
                    match.start():
                    closing + 1
                ],
            )
        )

    return blocks


def listens_on_target(
    block: str,
) -> bool:
    patterns = (
        rf"\blisten\s+{listen_port}\b",
        rf"\blisten\s+[^;:\s]+:{listen_port}\b",
        rf"\blisten\s+\[[^\]]+\]:{listen_port}\b",
    )

    return any(
        re.search(pattern, block)
        for pattern in patterns
    )


def locate_target() -> tuple[
    Path,
    str,
    int,
    int,
]:
    candidates = []

    for path, _ in configuration_sections(
        nginx_dump()
    ):
        if not path.is_file():
            continue

        text = path.read_text(
            encoding="utf-8"
        )

        for start, end, block in server_blocks(
            text
        ):
            if listens_on_target(block):
                candidates.append(
                    (
                        path,
                        text,
                        start,
                        end,
                    )
                )

    unique = []
    seen = set()

    for candidate in candidates:
        key = (
            str(candidate[0]),
            candidate[2],
            candidate[3],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    if len(unique) != 1:
        raise MigrationError(
            "expected exactly one nginx server "
            f"listening on {listen_port}; "
            f"found {len(unique)}"
        )

    return unique[0]


def atlas_block_bounds(
    text: str,
) -> tuple[int, int] | None:
    begin = text.find(
        atlas_marker_begin
    )

    if begin < 0:
        return None

    end = text.find(
        atlas_marker_end,
        begin,
    )

    if end < 0:
        raise MigrationError(
            "Atlas nginx begin marker exists "
            "without matching end marker"
        )

    end += len(atlas_marker_end)

    if text.find(
        atlas_marker_begin,
        begin + len(
            atlas_marker_begin
        ),
    ) >= 0:
        raise MigrationError(
            "duplicate Atlas nginx blocks found"
        )

    return begin, end


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
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
            handle.write(text)
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


def nginx_validate() -> None:
    process = subprocess.run(
        ["nginx", "-t"],
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        raise MigrationError(
            "nginx validation failed: "
            + (
                process.stdout
                + process.stderr
            ).strip()
        )


def build_migration(
    original: str,
    server_end: int,
) -> str:
    bounds = atlas_block_bounds(
        original
    )

    if bounds is not None:
        begin, end = bounds

        return (
            original[:begin]
            + atlas_locations
            + original[end:]
        )

    insertion = server_end - 1

    return (
        original[:insertion]
        + "\n"
        + atlas_locations
        + original[insertion:]
    )


def validate_atlas_block(
    text: str,
) -> None:
    bounds = atlas_block_bounds(
        text
    )

    if bounds is None:
        raise MigrationError(
            "Atlas nginx block unavailable"
        )

    begin, end = bounds
    block = text[begin:end]

    required = (
        "location = /atlas {",
        "return 308 /atlas/;",
        "location ^~ /atlas/ {",
        "proxy_pass http://127.0.0.1:8766/;",
        "location ^~ /api/atlas {",
        "proxy_pass http://127.0.0.1:8766;",
    )

    missing = [
        item
        for item in required
        if item not in block
    ]

    if missing:
        raise MigrationError(
            "Atlas nginx block missing: "
            + ", ".join(missing)
        )


def migrate(
    apply: bool,
) -> dict[str, Any]:
    (
        target,
        original,
        _server_start,
        server_end,
    ) = locate_target()

    migrated = build_migration(
        original,
        server_end,
    )

    validate_atlas_block(
        migrated
    )

    changed = migrated != original

    if apply and changed:
        atomic_write(
            target,
            migrated,
        )

        try:
            nginx_validate()

        except Exception:
            atomic_write(
                target,
                original,
            )
            raise

        reload_process = subprocess.run(
            ["nginx", "-s", "reload"],
            capture_output=True,
            text=True,
        )

        if reload_process.returncode != 0:
            atomic_write(
                target,
                original,
            )

            nginx_validate()

            subprocess.run(
                ["nginx", "-s", "reload"],
                check=False,
                capture_output=True,
                text=True,
            )

            raise MigrationError(
                "nginx reload failed: "
                + (
                    reload_process.stdout
                    + reload_process.stderr
                ).strip()
            )

    return {
        "schema":
            schema_version,
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
        "atlas_location_precedence":
            "prefix-terminal",
        "atlas_frontend_upstream":
            "http://127.0.0.1:8766/",
        "atlas_api_upstream":
            "http://127.0.0.1:8766",
        "atlas_prefix_stripped":
            True,
        "projection_only":
            True,
        "mutation_authority_added":
            False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        result = migrate(
            arguments.apply
        )

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
                    "apply":
                        arguments.apply,
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
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
