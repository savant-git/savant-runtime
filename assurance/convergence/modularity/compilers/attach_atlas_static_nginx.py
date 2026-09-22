#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


schema_version = "savant.assurance.attach-atlas-static-nginx.v1"
authority_effect = "none"

listen_port = 8765

target_path = Path("/etc/nginx/sites-enabled/savant-present")

atlas_assets = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets"
)

marker_begin = "    # savant-atlas-begin\n"
marker_end = "    # savant-atlas-end\n"


class AtlasStaticError(RuntimeError):
    pass


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
    )


def brace_pairs(text: str) -> dict[int, int]:
    stack: list[int] = []
    pairs: dict[int, int] = {}

    quote: str | None = None
    escaped = False
    comment = False

    for index, char in enumerate(text):
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
                raise AtlasStaticError(
                    "unbalanced nginx braces"
                )

            opening = stack.pop()
            pairs[opening] = index

    if stack:
        raise AtlasStaticError(
            "unbalanced nginx braces"
        )

    return pairs


def server_blocks(
    text: str,
) -> list[tuple[int, int, str]]:
    pairs = brace_pairs(text)

    result: list[tuple[int, int, str]] = []

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
        rf"\blisten\s+\[[^\]]+\]:{listen_port}\b",
    )

    return any(
        re.search(pattern, block)
        for pattern in patterns
    )


def remove_existing_atlas_block(
    text: str,
) -> str:
    begin = text.find(marker_begin)

    if begin < 0:
        return text

    end = text.find(
        marker_end,
        begin,
    )

    if end < 0:
        raise AtlasStaticError(
            "Atlas begin marker exists without matching end marker"
        )

    end += len(marker_end)

    second = text.find(
        marker_begin,
        begin + len(marker_begin),
    )

    if second >= 0:
        raise AtlasStaticError(
            "multiple Atlas marker blocks found"
        )

    return (
        text[:begin]
        + text[end:]
    )


def locate_server(
    text: str,
) -> tuple[int, int, str]:
    candidates = [
        block
        for block in server_blocks(text)
        if listens_on_target(block[2])
    ]

    if len(candidates) != 1:
        raise AtlasStaticError(
            "expected exactly one server listening on "
            f"{listen_port}; found {len(candidates)}"
        )

    return candidates[0]


def atlas_block() -> str:
    root = str(atlas_assets)

    return (
        "    # savant-atlas-begin\n"
        "    location = /atlas {\n"
        "        return 308 /atlas/;\n"
        "    }\n"
        "\n"
        "    location = /atlas/ {\n"
        f"        alias {root}/index.html;\n"
        "        default_type text/html;\n"
        "        add_header Cache-Control \"no-store\" always;\n"
        "        add_header X-Content-Type-Options \"nosniff\" always;\n"
        "    }\n"
        "\n"
        "    location = /atlas/assets/atlas.css {\n"
        f"        alias {root}/atlas.css;\n"
        "        default_type text/css;\n"
        "        add_header Cache-Control \"no-store\" always;\n"
        "        add_header X-Content-Type-Options \"nosniff\" always;\n"
        "    }\n"
        "\n"
        "    location = /atlas/assets/atlas.js {\n"
        f"        alias {root}/atlas.js;\n"
        "        default_type application/javascript;\n"
        "        add_header Cache-Control \"no-store\" always;\n"
        "        add_header X-Content-Type-Options \"nosniff\" always;\n"
        "    }\n"
        "    # savant-atlas-end\n"
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
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
            os.fsync(handle.fileno())

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
        [
            "nginx",
            "-t",
        ]
    )

    if process.returncode != 0:
        raise AtlasStaticError(
            (
                process.stdout
                + process.stderr
            ).strip()
        )


def migrate(
    apply: bool,
) -> dict:
    if not target_path.is_file():
        raise AtlasStaticError(
            f"missing nginx target: {target_path}"
        )

    required = (
        atlas_assets / "index.html",
        atlas_assets / "atlas.css",
        atlas_assets / "atlas.js",
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise AtlasStaticError(
            "missing Atlas assets: "
            + ", ".join(missing)
        )

    original = target_path.read_text(
        encoding="utf-8"
    )

    clean = remove_existing_atlas_block(
        original
    )

    _, server_end, _ = locate_server(
        clean
    )

    insertion = server_end - 1

    migrated = (
        clean[:insertion]
        + "\n"
        + atlas_block()
        + clean[insertion:]
    )

    changed = migrated != original

    if apply and changed:
        atomic_write(
            target_path,
            migrated,
        )

        try:
            validate_nginx()

            reload_process = run(
                [
                    "nginx",
                    "-s",
                    "reload",
                ]
            )

            if reload_process.returncode != 0:
                raise AtlasStaticError(
                    (
                        reload_process.stdout
                        + reload_process.stderr
                    ).strip()
                )

        except Exception:
            atomic_write(
                target_path,
                original,
            )

            validate_nginx()

            run(
                [
                    "nginx",
                    "-s",
                    "reload",
                ]
            )

            raise

    return {
        "schema": schema_version,
        "authority_effect": authority_effect,
        "status": "passed",
        "apply": apply,
        "changed": changed,
        "target": str(target_path),
        "listen_port": listen_port,
        "delivery": "nginx-static-exact-locations",
        "atlas_assets": str(atlas_assets),
        "projection_only": True,
        "mutation_authority_added": False,
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
                    "schema": schema_version,
                    "authority_effect": authority_effect,
                    "status": "failed",
                    "apply": arguments.apply,
                    "error": str(exc),
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
