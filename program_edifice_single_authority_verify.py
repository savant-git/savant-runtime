#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "modus"
    / "runtime"
)

AUTHORITY_FILE = (
    RUNTIME
    / "program_edifice.py"
)

AUTHORITY_SYMBOL = (
    "PROGRAM_edifice_SEGUES"
)

DERIVED_SYMBOLS = (
    "PROGRAM_edifice_LINEAGE",
    "PROGRAM_LEVELS",
    "PROGRAM_LEVEL_INDEX",
    "PROGRAM_CHILD_LEVEL",
    "PROGRAM_PARENT_LEVEL",
)

DEFINITION_PATTERN = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<name>"
    r"PROGRAM_edifice_SEGUES|"
    r"PROGRAM_edifice_LINEAGE|"
    r"PROGRAM_LEVELS|"
    r"PROGRAM_LEVEL_INDEX|"
    r"PROGRAM_CHILD_LEVEL|"
    r"PROGRAM_PARENT_LEVEL"
    r")\s*=",
    re.MULTILINE,
)


def definitions(
    path: Path,
) -> tuple[str, ...]:
    text = path.read_text(
        encoding="utf-8"
    )

    return tuple(
        match.group(
            "name"
        )
        for match
        in DEFINITION_PATTERN
        .finditer(
            text
        )
    )


def main() -> int:
    if not AUTHORITY_FILE.is_file():
        raise RuntimeError(
            "missing edifice authority file"
        )

    python_files = tuple(
        sorted(
            RUNTIME.glob(
                "*.py"
            )
        )
    )

    duplicate_authority: list[
        str
    ] = []

    authority_definitions: dict[
        str,
        list[str],
    ] = {}

    for path in python_files:
        found = definitions(
            path
        )

        for symbol in found:
            authority_definitions.setdefault(
                symbol,
                [],
            ).append(
                str(
                    path
                )
            )

            if (
                path
                != AUTHORITY_FILE
            ):
                duplicate_authority.append(
                    f"{symbol}:{path}"
                )

    if duplicate_authority:
        raise RuntimeError(
            "duplicate edifice authority "
            "definitions detected: "
            + ", ".join(
                duplicate_authority
            )
        )

    authority_symbols = set(
        definitions(
            AUTHORITY_FILE
        )
    )

    required = {
        AUTHORITY_SYMBOL,
        *DERIVED_SYMBOLS,
    }

    missing = (
        required
        - authority_symbols
    )

    if missing:
        raise RuntimeError(
            "edifice authority file "
            "missing required symbols: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    primary_locations = (
        authority_definitions.get(
            AUTHORITY_SYMBOL,
            [],
        )
    )

    if primary_locations != [
        str(
            AUTHORITY_FILE
        )
    ]:
        raise RuntimeError(
            "PROGRAM_edifice_SEGUES "
            "must be defined exactly once"
        )

    result = {
        "authority_file": str(
            AUTHORITY_FILE
        ),
        "authority_primitive": (
            AUTHORITY_SYMBOL
        ),
        "authority_definition_count": (
            len(
                primary_locations
            )
        ),
        "derived_symbols": list(
            DERIVED_SYMBOLS
        ),
        "duplicate_authority_definitions": (
            []
        ),
        "runtime_python_files_scanned": (
            len(
                python_files
            )
        ),
        "single_topology_authority": True,
        "passed": True,
    }

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
