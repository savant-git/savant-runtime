#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
)

EXILE_ROOT = (
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


def main() -> int:
    sys.path.insert(
        0,
        str(EXILE_ROOT),
    )

    runtime = importlib.import_module(
        "modus.runtime"
    )

    required = {
        "PROGRAM_LEVELS",
        "CODE_SEGUE_TYPES",
        "ProgramInstance",
        "CodeSegue",
        "ProgramCompositionGraph",
        "ProgramCompositionStore",
        "SourceDecomposition",
    }

    missing = sorted(
        name
        for name in required
        if not hasattr(
            runtime,
            name,
        )
    )

    if missing:
        raise RuntimeError(
            "missing Modus runtime exports: "
            + ", ".join(missing)
        )

    if tuple(
        runtime.PROGRAM_LEVELS
    ) != (
        "character",
        "line",
        "segment",
        "snippet",
        "script",
        "engine",
        "subsystem",
        "system",
        "application",
    ):
        raise RuntimeError(
            "program edifice mismatch"
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
        runtime
        .ProgramCompositionGraph()
    )

    decomposition = (
        graph.decompose_file(
            SUBJECT
        )
    )

    store = (
        runtime
        .ProgramCompositionStore()
    )

    receipt = store.save(
        graph,
        decomposition,
    )

    reloaded_graph, reloaded = (
        store.load(
            Path(
                receipt["path"]
            )
        )
    )

    regenerated = (
        reloaded_graph
        .project_text(
            reloaded
            .script_instance_id
        )
        .encode(
            "utf-8"
        )
    )

    if regenerated != source_bytes:
        raise RuntimeError(
            "package-loaded projection "
            "is not byte-for-byte equal"
        )

    validation = (
        reloaded_graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "package-loaded graph invalid"
        )

    result = {
        "package": "modus.runtime",
        "required_exports": (
            len(required)
        ),
        "missing_exports": (
            missing
        ),
        "program_levels": len(
            runtime.PROGRAM_LEVELS
        ),
        "segment_present": (
            runtime.PROGRAM_LEVELS[2]
            == "segment"
        ),
        "subject": str(
            SUBJECT
        ),
        "source_sha256": (
            source_digest
        ),
        "regenerated_sha256": (
            sha256(
                regenerated
            )
        ),
        "byte_for_byte_equal": (
            regenerated
            == source_bytes
        ),
        "reload_valid": (
            validation["valid"]
        ),
        "store_verified": (
            receipt["verified"]
        ),
        "owner": "exile:modus",
        "authority_effect": "none",
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
