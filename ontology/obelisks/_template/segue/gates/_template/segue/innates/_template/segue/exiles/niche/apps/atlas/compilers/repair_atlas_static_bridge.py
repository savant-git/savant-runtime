#!/usr/bin/env python3

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


SCHEMA = "savant.niche.atlas-static-bridge-repair.v1"

ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "niche/apps/atlas"
)

TARGET = ROOT / "assets/atlas-static-bridge.js"

BAD_FORMS = (
    'fetch("/atlas.json"',
    "fetch('/atlas.json'",
    'fetch(`/atlas.json`',
)

GOOD_FORMS = (
    'fetch(new URL("atlas.json", document.baseURI)',
    "fetch(new URL('atlas.json', document.baseURI)",
    "fetch(new URL(`atlas.json`, document.baseURI)",
)


class RepairError(RuntimeError):
    pass


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = stat.S_IMODE(
        path.stat().st_mode,
    )

    temporary = path.with_name(
        f".{path.name}.atlas-bridge.tmp"
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


def repair() -> bool:
    if not TARGET.is_file():
        raise RepairError(
            f"missing target: {TARGET}"
        )

    text = TARGET.read_text(
        encoding="utf-8",
    )

    if any(
        form in text
        for form in GOOD_FORMS
    ):
        return False

    matches = [
        form
        for form in BAD_FORMS
        if form in text
    ]

    if len(matches) != 1:
        raise RepairError(
            "expected exactly one known absolute "
            "atlas.json fetch form, found "
            f"{len(matches)}"
        )

    old = matches[0]

    if old.startswith(
        'fetch("'
    ):
        new = (
            'fetch(new URL("atlas.json", '
            "document.baseURI)"
        )
    elif old.startswith(
        "fetch('"
    ):
        new = (
            "fetch(new URL('atlas.json', "
            "document.baseURI)"
        )
    else:
        new = (
            "fetch(new URL(`atlas.json`, "
            "document.baseURI)"
        )

    repaired = text.replace(
        old,
        new,
        1,
    )

    if repaired == text:
        raise RepairError(
            "bridge repair produced no change"
        )

    atomic_write(
        TARGET,
        repaired,
    )

    return True


def main() -> int:
    changed = repair()

    print(
        {
            "schema": SCHEMA,
            "target": str(TARGET),
            "changed": changed,
            "projection_only": True,
            "mutation_authority": False,
        }
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RepairError as exc:
        print(
            f"{SCHEMA}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
