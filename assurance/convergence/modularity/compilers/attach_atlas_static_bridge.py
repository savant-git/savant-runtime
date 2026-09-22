#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


schema = "savant.assurance.attach-atlas-static-bridge.v1"
authority_effect = "none"

index_path = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas/assets/"
    "index.html"
)

bridge_name = "atlas-static-bridge.js"

bridge_tag = (
    '<script src="atlas-static-bridge.js"></script>'
)


class AtlasBridgeError(RuntimeError):
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


def transform(
    source: str,
) -> tuple[str, bool]:
    if bridge_tag in source:
        return source, False

    atlas_script_candidates = (
        '<script src="atlas.js"></script>',
        '<script defer src="atlas.js"></script>',
        '<script src="/atlas.js"></script>',
        '<script defer src="/atlas.js"></script>',
        '<script src="/atlas/assets/atlas.js"></script>',
        '<script defer src="/atlas/assets/atlas.js"></script>',
    )

    for candidate in atlas_script_candidates:
        if candidate in source:
            return (
                source.replace(
                    candidate,
                    bridge_tag
                    + "\n"
                    + candidate,
                    1,
                ),
                True,
            )

    closing_body = "</body>"

    if closing_body in source:
        return (
            source.replace(
                closing_body,
                bridge_tag
                + "\n"
                + closing_body,
                1,
            ),
            True,
        )

    raise AtlasBridgeError(
        "index.html contains neither a recognized "
        "Atlas script tag nor </body>"
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        bridge_path = (
            index_path.parent
            / bridge_name
        )

        if not index_path.is_file():
            raise AtlasBridgeError(
                f"missing Atlas index: {index_path}"
            )

        if not bridge_path.is_file():
            raise AtlasBridgeError(
                f"missing Atlas bridge: {bridge_path}"
            )

        source = index_path.read_text(
            encoding="utf-8"
        )

        transformed, changed = transform(
            source
        )

        if arguments.apply and changed:
            atomic_write(
                index_path,
                transformed,
            )

        result = {
            "schema": schema,
            "authority_effect":
                authority_effect,
            "status": "passed",
            "apply": arguments.apply,
            "changed": changed,
            "index": str(index_path),
            "bridge": str(bridge_path),
            "projection_source":
                "/atlas.json",
            "existing_atlas_javascript_preserved":
                True,
            "network_api_dependency_for_primary_projection":
                False,
            "projection_only":
                True,
            "mutation_authority_added":
                False,
        }

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": schema,
                    "authority_effect":
                        authority_effect,
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
    raise SystemExit(main())
