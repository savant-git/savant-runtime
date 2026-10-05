#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

MODUS_RUNTIME = (
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

COMPOSITION_PATH = (
    MODUS_RUNTIME
    / "program_composition.py"
)

STORE_PATH = (
    MODUS_RUNTIME
    / "program_store.py"
)

REGISTRY_PATH = (
    MODUS_RUNTIME
    / "program_registry.py"
)

SUBJECT = (
    ROOT
    / "runtime"
    / "spyral"
    / "__init__.py"
)

EXPECTED_SHA256 = (
    "6569b5e802c556ef6b371358ab770eb7"
    "ad6c6c54250f870ad75880e19687c125"
)


def sha256(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def load(
    name: str,
    path: Path,
):
    specification = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            f"unable to load: {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def main() -> int:
    composition = load(
        "program_composition",
        COMPOSITION_PATH,
    )

    store_module = load(
        "program_store",
        STORE_PATH,
    )

    registry_module = load(
        "program_registry",
        REGISTRY_PATH,
    )

    source_bytes = (
        SUBJECT.read_bytes()
    )

    source_digest = sha256(
        source_bytes
    )

    if source_digest != EXPECTED_SHA256:
        raise RuntimeError(
            "Spyral baseline drift: "
            + source_digest
        )

    graph = (
        composition
        .ProgramCompositionGraph()
    )

    decomposition = (
        graph.decompose_file(
            SUBJECT
        )
    )

    store = (
        store_module
        .ProgramCompositionStore()
    )

    store_receipt = (
        store.save(
            graph,
            decomposition,
        )
    )

    registry = (
        registry_module
        .ProgramProjectionRegistry()
    )

    entry = (
        registry.register(
            source_path=SUBJECT,
            store_path=Path(
                store_receipt[
                    "path"
                ]
            ),
            decomposition=decomposition,
        )
    )

    verification = (
        registry.verify_entry(
            SUBJECT
        )
    )

    if (
        verification["passed"]
        is not True
    ):
        raise RuntimeError(
            "registered projection verification failed"
        )

    if (
        verification[
            "source_matches"
        ]
        is not True
    ):
        raise RuntimeError(
            "source unexpectedly drifted"
        )

    if (
        verification[
            "projection_matches"
        ]
        is not True
    ):
        raise RuntimeError(
            "registered projection differs"
        )

    status = (
        registry.status()
    )

    result = {
        "subject": str(
            SUBJECT
        ),
        "registered_source": (
            entry[
                "source_path"
            ]
        ),
        "source_sha256": (
            source_digest
        ),
        "registered_sha256": (
            entry[
                "source_digest"
            ]
        ),
        "current_source_matches": (
            verification[
                "source_matches"
            ]
        ),
        "projection_matches": (
            verification[
                "projection_matches"
            ]
        ),
        "drift_detected": (
            verification[
                "drift_detected"
            ]
        ),
        "source_remains_live": (
            verification[
                "source_remains_live"
            ]
        ),
        "projection_authoritative": (
            verification[
                "projection_authoritative"
            ]
        ),
        "mutation_authorized": (
            verification[
                "mutation_authorized"
            ]
        ),
        "registry_entries": (
            status[
                "entry_count"
            ]
        ),
        "owner": (
            status["owner"]
        ),
        "authority_effect": (
            status[
                "authority_effect"
            ]
        ),
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
