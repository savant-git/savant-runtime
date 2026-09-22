#!/usr/bin/env python3

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


SCHEMA = "savant.niche.atlas-browser-entry-normalization.v1"

ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "niche/apps/atlas"
)

TARGET = ROOT / "assets/index.html"

REQUIRED_ASSETS = (
    ROOT / "assets/atlas.css",
    ROOT / "assets/atlas-static-bridge.js",
    ROOT / "assets/atlas.js",
)

CANONICAL_STYLESHEET = (
    '<link rel="stylesheet" href="atlas.css">'
)

CANONICAL_BRIDGE = (
    '<script src="atlas-static-bridge.js"></script>'
)

CANONICAL_APPLICATION = (
    '<script src="atlas.js"></script>'
)


class NormalizeError(RuntimeError):
    pass


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    temporary = path.with_name(
        f".{path.name}.atlas-entry.tmp"
    )

    temporary.write_text(
        text,
        encoding="utf-8",
    )

    os.chmod(
        temporary,
        mode,
    )

    os.replace(
        temporary,
        path,
    )


def replace_known(
    text: str,
    candidates: tuple[str, ...],
    canonical: str,
    label: str,
) -> tuple[str, bool]:
    if canonical in text:
        return text, False

    matches = [
        candidate
        for candidate in candidates
        if candidate in text
    ]

    if len(matches) != 1:
        raise NormalizeError(
            f"{label}: expected one known source form, "
            f"found {len(matches)}"
        )

    return (
        text.replace(
            matches[0],
            canonical,
            1,
        ),
        True,
    )


def normalize() -> bool:
    if not TARGET.is_file():
        raise NormalizeError(
            f"missing atlas entry: {TARGET}"
        )

    missing = [
        str(path)
        for path in REQUIRED_ASSETS
        if not path.is_file()
    ]

    if missing:
        raise NormalizeError(
            "required atlas browser asset missing: "
            + ", ".join(missing)
        )

    text = TARGET.read_text(
        encoding="utf-8"
    )

    original = text

    text, _ = replace_known(
        text,
        (
            '<link rel="stylesheet" href="/assets/atlas.css">',
            '<link rel="stylesheet" href="./atlas.css">',
            '<link href="/assets/atlas.css" rel="stylesheet">',
            '<link href="./atlas.css" rel="stylesheet">',
        ),
        CANONICAL_STYLESHEET,
        "atlas stylesheet",
    )

    text, _ = replace_known(
        text,
        (
            '<script src="/assets/atlas-static-bridge.js"></script>',
            '<script src="./atlas-static-bridge.js"></script>',
        ),
        CANONICAL_BRIDGE,
        "atlas static bridge",
    )

    text, _ = replace_known(
        text,
        (
            '<script src="/assets/atlas.js"></script>',
            '<script src="./atlas.js"></script>',
        ),
        CANONICAL_APPLICATION,
        "atlas application",
    )

    bridge_index = text.find(
        CANONICAL_BRIDGE
    )

    application_index = text.find(
        CANONICAL_APPLICATION
    )

    if (
        bridge_index < 0
        or application_index < 0
    ):
        raise NormalizeError(
            "canonical atlas scripts are missing"
        )

    if bridge_index > application_index:
        text = text.replace(
            CANONICAL_BRIDGE,
            "",
            1,
        )

        application_index = text.find(
            CANONICAL_APPLICATION
        )

        if application_index < 0:
            raise NormalizeError(
                "atlas application script disappeared "
                "during ordering normalization"
            )

        text = (
            text[:application_index]
            + CANONICAL_BRIDGE
            + "\n"
            + text[application_index:]
        )

    forbidden = (
        'href="/assets/atlas.css"',
        'src="/assets/atlas.js"',
        'src="/assets/atlas-static-bridge.js"',
    )

    residue = [
        value
        for value in forbidden
        if value in text
    ]

    if residue:
        raise NormalizeError(
            "absolute browser asset references remain: "
            + ", ".join(residue)
        )

    if text == original:
        return False

    atomic_write(
        TARGET,
        text,
    )

    return True


def main() -> int:
    changed = normalize()

    final = TARGET.read_text(
        encoding="utf-8"
    )

    bridge_index = final.find(
        CANONICAL_BRIDGE
    )

    application_index = final.find(
        CANONICAL_APPLICATION
    )

    valid = (
        CANONICAL_STYLESHEET in final
        and bridge_index >= 0
        and application_index >= 0
        and bridge_index < application_index
    )

    if not valid:
        raise NormalizeError(
            "atlas browser entry did not reach "
            "the canonical transport order"
        )

    print(
        {
            "schema": SCHEMA,
            "target": str(TARGET),
            "changed": changed,
            "stylesheet": "atlas.css",
            "bridge": "atlas-static-bridge.js",
            "application": "atlas.js",
            "bridge_precedes_application": True,
            "projection_only": True,
            "mutation_authority": False,
        }
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NormalizeError as exc:
        print(
            f"{SCHEMA}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
