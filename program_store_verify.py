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

COMPOSITION = (
    MODUS_RUNTIME
    / "program_composition.py"
)

STORE_MODULE = (
    MODUS_RUNTIME
    / "program_store.py"
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
            f"unable to load {path}"
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
        COMPOSITION,
    )

    store_module = load(
        "program_store",
        STORE_MODULE,
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

    receipt = store.save(
        graph,
        decomposition,
    )

    store_path = Path(
        receipt["path"]
    )

    if not store_path.is_file():
        raise RuntimeError(
            "durable store was not created"
        )

    reloaded_graph, reloaded = (
        store.load(
            store_path
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

    regenerated_digest = sha256(
        regenerated
    )

    if regenerated != source_bytes:
        raise RuntimeError(
            "durable reload is not "
            "byte-for-byte reversible"
        )

    if regenerated_digest != source_digest:
        raise RuntimeError(
            "durable reload digest mismatch"
        )

    validation = (
        reloaded_graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "reloaded graph invalid"
        )

    result = {
        "subject": str(
            SUBJECT
        ),
        "store": str(
            store_path
        ),
        "source_sha256": (
            source_digest
        ),
        "regenerated_sha256": (
            regenerated_digest
        ),
        "byte_for_byte_equal": (
            regenerated
            == source_bytes
        ),
        "atomic_store": (
            receipt["atomic"]
        ),
        "stored_verified": (
            receipt["verified"]
        ),
        "reload_valid": (
            validation["valid"]
        ),
        "script_instance_id": (
            reloaded
            .script_instance_id
        ),
        "instance_count": len(
            reloaded_graph.instances
        ),
        "segue_count": len(
            reloaded_graph.segues
        ),
        "authoritative": False,
        "authority_effect": "none",
        "owner": "exile:modus",
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
