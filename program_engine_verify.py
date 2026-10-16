#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(
    "/root/savant-runtime"
).resolve()

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

ENGINE_PATH = (
    MODUS_RUNTIME
    / "program_engine.py"
)

SPYRAL_INIT = (
    ROOT
    / "runtime"
    / "spyral"
    / "__init__.py"
)

SPYRAL_ENGINE = (
    ROOT
    / "runtime"
    / "spyral"
    / "engine.py"
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
    if not SPYRAL_INIT.is_file():
        raise RuntimeError(
            f"missing source: {SPYRAL_INIT}"
        )

    if not SPYRAL_ENGINE.is_file():
        raise RuntimeError(
            f"missing source: {SPYRAL_ENGINE}"
        )

    composition_module = load(
        "program_composition",
        COMPOSITION_PATH,
    )

    engine_module = load(
        "program_engine",
        ENGINE_PATH,
    )

    graph = (
        composition_module
        .ProgramCompositionGraph()
    )

    init_decomposition = (
        graph.decompose_file(
            SPYRAL_INIT
        )
    )

    engine_decomposition = (
        graph.decompose_file(
            SPYRAL_ENGINE
        )
    )

    init_original = (
        SPYRAL_INIT.read_bytes()
    )

    engine_original = (
        SPYRAL_ENGINE.read_bytes()
    )

    init_projected = (
        graph.project_text(
            init_decomposition
            .script_instance_id
        )
        .encode(
            "utf-8"
        )
    )

    engine_projected = (
        graph.project_text(
            engine_decomposition
            .script_instance_id
        )
        .encode(
            "utf-8"
        )
    )

    if init_projected != init_original:
        raise RuntimeError(
            "__init__.py script "
            "round-trip failed"
        )

    if engine_projected != engine_original:
        raise RuntimeError(
            "engine.py script "
            "round-trip failed"
        )

    composer = (
        engine_module
        .ProgramEngineComposer(
            graph
        )
    )

    composed = (
        composer.compose(
            (
                init_decomposition,
                engine_decomposition,
            ),
            engine_name=(
                "runtime.spyral"
            ),
            lineage=(
                "living:spyral",
            ),
            provenance=(
                "verified-live-implementation",
            ),
            dependencies=(),
        )
    )

    engine_instance = (
        graph.instance(
            composed
            .engine_instance_id
        )
    )

    if engine_instance.level != "engine":
        raise RuntimeError(
            "root is not engine level"
        )

    if (
        engine_instance.children
        != (
            init_decomposition
            .script_instance_id,
            engine_decomposition
            .script_instance_id,
        )
    ):
        raise RuntimeError(
            "engine script ordering changed"
        )

    for child_id in (
        engine_instance.children
    ):
        child = graph.instance(
            child_id
        )

        if child.level != "script":
            raise RuntimeError(
                "engine contains "
                "non-script child"
            )

    manifest = (
        composer.manifest(
            composed
        )
    )

    validation = (
        graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "composed graph invalid"
        )

    result = {
        "engine_instance_id": (
            composed
            .engine_instance_id
        ),
        "engine_name": (
            "runtime.spyral"
        ),
        "engine_level": (
            engine_instance.level
        ),
        "script_count": len(
            engine_instance.children
        ),
        "script_order": [
            str(
                SPYRAL_INIT
                .relative_to(
                    ROOT
                )
            ),
            str(
                SPYRAL_ENGINE
                .relative_to(
                    ROOT
                )
            ),
        ],
        "init_sha256": (
            sha256(
                init_original
            )
        ),
        "init_projection_sha256": (
            sha256(
                init_projected
            )
        ),
        "init_byte_equal": (
            init_original
            == init_projected
        ),
        "engine_sha256": (
            sha256(
                engine_original
            )
        ),
        "engine_projection_sha256": (
            sha256(
                engine_projected
            )
        ),
        "engine_byte_equal": (
            engine_original
            == engine_projected
        ),
        "composition_segues": len(
            composed.segue_ids
        ),
        "graph_valid": (
            validation["valid"]
        ),
        "manifest_rebuildable": (
            manifest[
                "rebuildable"
            ]
        ),
        "live_sources_modified": False,
        "authoritative": False,
        "mutation_authorized": False,
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
