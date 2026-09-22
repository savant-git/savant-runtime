#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


schema = (
    "savant.assurance."
    "attach-atlas-static-projection.v1"
)

authority_effect = "none"

target = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets/"
    "atlas.js"
)


class AtlasStaticProjectionError(
    RuntimeError
):
    pass


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


def transform(
    source: str,
) -> tuple[str, bool]:
    desired = (
        'fetch("/atlas.json", '
        '{ cache: "no-store" })'
    )

    variants = (
        'fetch("/api/atlas")',
        "fetch('/api/atlas')",
        'fetch("/api/atlas", { cache: "no-store" })',
        "fetch('/api/atlas', { cache: 'no-store' })",
        'fetch("/api/atlas", {cache:"no-store"})',
    )

    if desired in source:
        return (
            source,
            False,
        )

    matches = [
        variant
        for variant in variants
        if variant in source
    ]

    if len(matches) != 1:
        raise AtlasStaticProjectionError(
            "expected exactly one recognized "
            "Atlas projection fetch expression; "
            f"found {len(matches)}"
        )

    transformed = source.replace(
        matches[0],
        desired,
        1,
    )

    return (
        transformed,
        transformed != source,
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        if not target.is_file():
            raise AtlasStaticProjectionError(
                f"missing Atlas frontend: {target}"
            )

        source = target.read_text(
            encoding="utf-8"
        )

        transformed, changed = transform(
            source
        )

        if arguments.apply and changed:
            atomic_write(
                target,
                transformed,
            )

        result = {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "status":
                "passed",
            "apply":
                arguments.apply,
            "changed":
                changed,
            "target":
                str(target),
            "projection_source":
                "/atlas.json",
            "network_api_dependency":
                False,
            "projection_only":
                True,
            "mutation_authority_added":
                False,
        }

    except Exception as exc:
        result = {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "status":
                "failed",
            "apply":
                arguments.apply,
            "error":
                str(exc),
        }

        print(
            json.dumps(
                result,
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
