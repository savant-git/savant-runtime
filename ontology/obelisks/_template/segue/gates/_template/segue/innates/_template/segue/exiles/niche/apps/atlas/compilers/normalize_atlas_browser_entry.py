#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path


SCHEMA = "savant.niche.atlas-browser-entry-normalization.v2"

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


def asset_basename(
    value: str,
) -> str:
    clean = value.split("?", 1)[0].split("#", 1)[0]

    return clean.rstrip("/").rsplit("/", 1)[-1]


def normalize_stylesheet(
    text: str,
) -> tuple[str, bool]:
    pattern = re.compile(
        r"<link\b[^>]*>",
        re.IGNORECASE,
    )

    matches: list[str] = []

    for match in pattern.finditer(text):
        tag = match.group(0)

        href_match = re.search(
            r"""href\s*=\s*(['"])(.*?)\1""",
            tag,
            re.IGNORECASE,
        )

        if not href_match:
            continue

        if asset_basename(
            href_match.group(2)
        ) == "atlas.css":
            matches.append(tag)

    if len(matches) != 1:
        raise NormalizeError(
            "atlas stylesheet: expected exactly one "
            f"atlas.css link tag, found {len(matches)}"
        )

    current = matches[0]

    if current == CANONICAL_STYLESHEET:
        return text, False

    return (
        text.replace(
            current,
            CANONICAL_STYLESHEET,
            1,
        ),
        True,
    )


def find_script(
    text: str,
    basename: str,
) -> list[str]:
    pattern = re.compile(
        r"<script\b[^>]*>.*?</script\s*>",
        re.IGNORECASE | re.DOTALL,
    )

    matches: list[str] = []

    for match in pattern.finditer(text):
        tag = match.group(0)

        src_match = re.search(
            r"""src\s*=\s*(['"])(.*?)\1""",
            tag,
            re.IGNORECASE,
        )

        if not src_match:
            continue

        if asset_basename(
            src_match.group(2)
        ) == basename:
            matches.append(tag)

    return matches


def normalize_script(
    text: str,
    basename: str,
    canonical: str,
) -> tuple[str, bool]:
    matches = find_script(
        text,
        basename,
    )

    if len(matches) != 1:
        raise NormalizeError(
            f"{basename}: expected exactly one script tag, "
            f"found {len(matches)}"
        )

    current = matches[0]

    if current == canonical:
        return text, False

    return (
        text.replace(
            current,
            canonical,
            1,
        ),
        True,
    )


def normalize_order(
    text: str,
) -> tuple[str, bool]:
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
            "canonical atlas scripts missing "
            "before order normalization"
        )

    if bridge_index < application_index:
        return text, False

    without_bridge = text.replace(
        CANONICAL_BRIDGE,
        "",
        1,
    )

    application_index = without_bridge.find(
        CANONICAL_APPLICATION
    )

    if application_index < 0:
        raise NormalizeError(
            "atlas application script disappeared "
            "during ordering normalization"
        )

    repaired = (
        without_bridge[:application_index]
        + CANONICAL_BRIDGE
        + "\n"
        + without_bridge[application_index:]
    )

    return repaired, True


def validate(
    text: str,
) -> None:
    if text.count(
        CANONICAL_STYLESHEET
    ) != 1:
        raise NormalizeError(
            "canonical atlas stylesheet count is not one"
        )

    if text.count(
        CANONICAL_BRIDGE
    ) != 1:
        raise NormalizeError(
            "canonical atlas bridge count is not one"
        )

    if text.count(
        CANONICAL_APPLICATION
    ) != 1:
        raise NormalizeError(
            "canonical atlas application count is not one"
        )

    bridge_index = text.find(
        CANONICAL_BRIDGE
    )

    application_index = text.find(
        CANONICAL_APPLICATION
    )

    if bridge_index > application_index:
        raise NormalizeError(
            "atlas static bridge does not precede atlas application"
        )

    forbidden = (
        'href="/assets/atlas.css"',
        "href='/assets/atlas.css'",
        'src="/assets/atlas.js"',
        "src='/assets/atlas.js'",
        'src="/assets/atlas-static-bridge.js"',
        "src='/assets/atlas-static-bridge.js'",
    )

    residue = [
        value
        for value in forbidden
        if value in text
    ]

    if residue:
        raise NormalizeError(
            "absolute atlas browser references remain: "
            + ", ".join(residue)
        )


def normalize() -> dict[str, bool]:
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

    changed = {
        "stylesheet": False,
        "bridge": False,
        "application": False,
        "order": False,
    }

    text, changed["stylesheet"] = (
        normalize_stylesheet(text)
    )

    text, changed["bridge"] = (
        normalize_script(
            text,
            "atlas-static-bridge.js",
            CANONICAL_BRIDGE,
        )
    )

    text, changed["application"] = (
        normalize_script(
            text,
            "atlas.js",
            CANONICAL_APPLICATION,
        )
    )

    text, changed["order"] = (
        normalize_order(text)
    )

    validate(text)

    if any(changed.values()):
        atomic_write(
            TARGET,
            text,
        )

    return changed


def main() -> int:
    changed = normalize()

    final = TARGET.read_text(
        encoding="utf-8"
    )

    validate(final)

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
