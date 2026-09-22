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
    "attach-atlas-native-nginx.v1"
)

authority_effect = "none"
listen_port = 8765

atlas_assets = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets"
)

marker_begin = (
    "    # savant-atlas-begin\n"
)

marker_end = (
    "    # savant-atlas-end\n"
)


class AtlasBridgeError(
    RuntimeError
):
    pass


def run(
    command: list[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
    )


def nginx_dump() -> str:
    process = run(
        [
            "nginx",
            "-T",
        ]
    )

    output = (
        process.stdout
        + process.stderr
    )

    if process.returncode != 0:
        raise AtlasBridgeError(
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
        marker.finditer(
            dump
        )
    )

    sections: list[
        tuple[Path, str]
    ] = []

    for index, match in enumerate(
        matches
    ):
        start = match.end()

        end = (
            matches[
                index + 1
            ].start()
            if index + 1
            < len(matches)
            else len(dump)
        )

        sections.append(
            (
                Path(
                    match.group(1)
                ),
                dump[
                    start:end
                ],
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
                raise AtlasBridgeError(
                    "unbalanced nginx braces"
                )

            opening = stack.pop()
            pairs[
                opening
            ] = index

    if stack:
        raise AtlasBridgeError(
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

        closing = pairs.get(
            opening
        )

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
        re.search(
            pattern,
            block,
        )
        for pattern in patterns
    )


def locate_target() -> tuple[
    Path,
    str,
    int,
    int,
    str,
]:
    candidates = []

    dump = nginx_dump()

    for path, _ in configuration_sections(
        dump
    ):
        if not path.is_file():
            continue

        text = path.read_text(
            encoding="utf-8"
        )

        for (
            start,
            end,
            block,
        ) in server_blocks(
            text
        ):
            if listens_on_target(
                block
            ):
                candidates.append(
                    (
                        path,
                        text,
                        start,
                        end,
                        block,
                    )
                )

    unique = []
    seen = set()

    for candidate in candidates:
        key = (
            str(
                candidate[0]
            ),
            candidate[2],
            candidate[3],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            candidate
        )

    if len(unique) != 1:
        raise AtlasBridgeError(
            "expected exactly one nginx "
            f"server listening on {listen_port}; "
            f"found {len(unique)}"
        )

    return unique[0]


def remove_atlas_marker_block(
    text: str,
) -> str:
    begin = text.find(
        marker_begin
    )

    if begin < 0:
        return text

    end = text.find(
        marker_end,
        begin,
    )

    if end < 0:
        raise AtlasBridgeError(
            "Atlas begin marker exists "
            "without matching end marker"
        )

    end += len(
        marker_end
    )

    if text.find(
        marker_begin,
        begin + len(
            marker_begin
        ),
    ) >= 0:
        raise AtlasBridgeError(
            "duplicate Atlas marker "
            "blocks found"
        )

    return (
        text[:begin]
        + text[end:]
    )


def upstream_candidates(
    server_block: str,
) -> list[str]:
    clean = remove_atlas_marker_block(
        server_block
    )

    candidates = []

    for match in re.finditer(
        r"\bproxy_pass\s+"
        r"(https?://[^;\s]+)\s*;",
        clean,
    ):
        upstream = (
            match.group(1)
        )

        if (
            "127.0.0.1:8766"
            in upstream
            or "127.0.0.1:8776"
            in upstream
        ):
            continue

        candidates.append(
            upstream
        )

    normalized = []

    seen = set()

    for upstream in candidates:
        base = upstream.rstrip(
            "/"
        )

        if base in seen:
            continue

        seen.add(
            base
        )

        normalized.append(
            base
        )

    return normalized


def choose_niche_upstream(
    server_block: str,
) -> str:
    candidates = upstream_candidates(
        server_block
    )

    if not candidates:
        raise AtlasBridgeError(
            "no existing non-Atlas "
            "proxy upstream found in "
            "the Nginx 8765 server"
        )

    if len(candidates) == 1:
        return candidates[0]

    api_candidates = []

    pairs = brace_pairs(
        server_block
    )

    for match in re.finditer(
        r"\blocation\b[^{]*\{",
        server_block,
    ):
        opening = server_block.find(
            "{",
            match.start(),
            match.end(),
        )

        closing = pairs.get(
            opening
        )

        if closing is None:
            continue

        header = server_block[
            match.start():
            opening
        ]

        body = server_block[
            opening + 1:
            closing
        ]

        if (
            "/api"
            not in header
            and header.strip()
            not in (
                "location / ",
                "location /",
            )
        ):
            continue

        found = re.findall(
            r"\bproxy_pass\s+"
            r"(https?://[^;\s]+)\s*;",
            body,
        )

        for upstream in found:
            base = upstream.rstrip(
                "/"
            )

            if (
                "127.0.0.1:8766"
                in base
                or "127.0.0.1:8776"
                in base
            ):
                continue

            api_candidates.append(
                base
            )

    unique_api = []

    seen = set()

    for upstream in api_candidates:
        if upstream in seen:
            continue

        seen.add(
            upstream
        )

        unique_api.append(
            upstream
        )

    if len(unique_api) == 1:
        return unique_api[0]

    raise AtlasBridgeError(
        "multiple existing Niche upstreams "
        "found and ownership cannot be "
        "determined without guessing: "
        + ", ".join(
            candidates
        )
    )


def atlas_block(
    niche_upstream: str,
) -> str:
    root = str(
        atlas_assets
    )

    return (
        "    # savant-atlas-begin\n"
        "    location = /atlas {\n"
        "        return 308 /atlas/;\n"
        "    }\n"
        "\n"
        "    location = /atlas/ {\n"
        f"        root {root};\n"
        "        try_files /index.html =404;\n"
        "        default_type text/html;\n"
        "        add_header Cache-Control "
        "\"no-store\" always;\n"
        "        add_header X-Content-Type-Options "
        "\"nosniff\" always;\n"
        "    }\n"
        "\n"
        "    location ^~ /atlas/assets/ {\n"
        f"        alias {root}/;\n"
        "        try_files $uri =404;\n"
        "        add_header Cache-Control "
        "\"no-store\" always;\n"
        "        add_header X-Content-Type-Options "
        "\"nosniff\" always;\n"
        "    }\n"
        "\n"
        "    location ^~ /api/atlas {\n"
        f"        proxy_pass {niche_upstream};\n"
        "        proxy_http_version 1.1;\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For "
        "$proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "    }\n"
        "    # savant-atlas-end\n"
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = (
        path.stat().st_mode
    )

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


def nginx_validate() -> None:
    process = run(
        [
            "nginx",
            "-t",
        ]
    )

    if process.returncode != 0:
        raise AtlasBridgeError(
            "nginx validation failed: "
            + (
                process.stdout
                + process.stderr
            ).strip()
        )


def migrate(
    apply: bool,
) -> dict[str, Any]:
    required = (
        atlas_assets
        / "index.html",
        atlas_assets
        / "atlas.css",
        atlas_assets
        / "atlas.js",
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise AtlasBridgeError(
            "Atlas frontend source missing: "
            + ", ".join(
                missing
            )
        )

    (
        target,
        original,
        server_start,
        server_end,
        server_block,
    ) = locate_target()

    niche_upstream = (
        choose_niche_upstream(
            server_block
        )
    )

    clean = (
        remove_atlas_marker_block(
            original
        )
    )

    removed_length = (
        len(original)
        - len(clean)
    )

    if removed_length:
        (
            target,
            clean,
            server_start,
            server_end,
            server_block,
        ) = locate_target_from_text(
            target,
            clean,
        )

    insertion = (
        server_end - 1
    )

    block = atlas_block(
        niche_upstream
    )

    migrated = (
        clean[:insertion]
        + "\n"
        + block
        + clean[insertion:]
    )

    changed = (
        migrated
        != original
    )

    if apply and changed:
        atomic_write(
            target,
            migrated,
        )

        try:
            nginx_validate()

            reload_process = run(
                [
                    "nginx",
                    "-s",
                    "reload",
                ]
            )

            if (
                reload_process.returncode
                != 0
            ):
                raise AtlasBridgeError(
                    "nginx reload failed: "
                    + (
                        reload_process.stdout
                        + reload_process.stderr
                    ).strip()
                )

        except Exception:
            atomic_write(
                target,
                original,
            )

            nginx_validate()

            run(
                [
                    "nginx",
                    "-s",
                    "reload",
                ]
            )

            raise

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
        "frontend_delivery":
            "nginx-direct-filesystem",
        "api_delivery":
            "existing-niche-upstream",
        "niche_upstream":
            niche_upstream,
        "atlas_assets":
            str(atlas_assets),
        "standalone_atlas_service_required":
            False,
        "projection_only":
            True,
        "mutation_authority_added":
            False,
    }


def locate_target_from_text(
    target: Path,
    text: str,
) -> tuple[
    Path,
    str,
    int,
    int,
    str,
]:
    matches = [
        item
        for item in server_blocks(
            text
        )
        if listens_on_target(
            item[2]
        )
    ]

    if len(matches) != 1:
        raise AtlasBridgeError(
            "target configuration stopped "
            "containing exactly one 8765 "
            "server during migration"
        )

    (
        start,
        end,
        block,
    ) = matches[0]

    return (
        target,
        text,
        start,
        end,
        block,
    )


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = (
        parser.parse_args()
    )

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
    raise SystemExit(
        main()
    )
