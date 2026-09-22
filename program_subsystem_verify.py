#!/usr/bin/env python3

from __future__ import annotations

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

SUBSYSTEM_PATH = (
    MODUS_RUNTIME
    / "program_subsystem.py"
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

CYPHER_INIT = (
    ROOT
    / "runtime"
    / "cypher"
    / "__init__.py"
)

CYPHER_ENGINE = (
    ROOT
    / "runtime"
    / "cypher"
    / "engine.py"
)


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


def require_files(
    *paths: Path,
) -> None:
    missing = [
        str(path)
        for path in paths
        if not path.is_file()
    ]

    if missing:
        raise RuntimeError(
            "missing source files: "
            + ", ".join(missing)
        )


def main() -> int:
    require_files(
        SPYRAL_INIT,
        SPYRAL_ENGINE,
        CYPHER_INIT,
        CYPHER_ENGINE,
    )

    composition_module = load(
        "program_composition",
        COMPOSITION_PATH,
    )

    engine_module = load(
        "program_engine",
        ENGINE_PATH,
    )

    subsystem_module = load(
        "program_subsystem",
        SUBSYSTEM_PATH,
    )

    graph = (
        composition_module
        .ProgramCompositionGraph()
    )

    spyral_init = (
        graph.decompose_file(
            SPYRAL_INIT
        )
    )

    spyral_engine = (
        graph.decompose_file(
            SPYRAL_ENGINE
        )
    )

    cypher_init = (
        graph.decompose_file(
            CYPHER_INIT
        )
    )

    cypher_engine = (
        graph.decompose_file(
            CYPHER_ENGINE
        )
    )

    engine_composer = (
        engine_module
        .ProgramEngineComposer(
            graph
        )
    )

    spyral = engine_composer.compose(
        (
            spyral_init,
            spyral_engine,
        ),
        engine_name="runtime.spyral",
        lineage=(
            "living:spyral",
        ),
        provenance=(
            "verified-live-implementation",
        ),
    )

    cypher = engine_composer.compose(
        (
            cypher_init,
            cypher_engine,
        ),
        engine_name="runtime.cypher",
        lineage=(
            "living:cypher",
        ),
        provenance=(
            "verified-live-implementation",
        ),
    )

    subsystem_composer = (
        subsystem_module
        .ProgramSubsystemComposer(
            graph
        )
    )

    subsystem = (
        subsystem_composer.compose(
            (
                spyral,
                cypher,
            ),
            subsystem_name=(
                "runtime.substrates"
            ),
            lineage=(
                "savant:runtime",
            ),
            provenance=(
                "live-runtime-substrates",
            ),
        )
    )

    subsystem_instance = (
        graph.instance(
            subsystem
            .subsystem_instance_id
        )
    )

    if (
        subsystem_instance.level
        != "subsystem"
    ):
        raise RuntimeError(
            "root is not subsystem"
        )

    if len(
        subsystem_instance.children
    ) != 2:
        raise RuntimeError(
            "expected two engines"
        )

    for engine_id in (
        subsystem_instance.children
    ):
        if (
            graph.instance(
                engine_id
            ).level
            != "engine"
        ):
            raise RuntimeError(
                "subsystem contains "
                "non-engine child"
            )

    for decomposition, source in (
        (
            spyral_init,
            SPYRAL_INIT,
        ),
        (
            spyral_engine,
            SPYRAL_ENGINE,
        ),
        (
            cypher_init,
            CYPHER_INIT,
        ),
        (
            cypher_engine,
            CYPHER_ENGINE,
        ),
    ):
        projected = (
            graph.project_text(
                decomposition
                .script_instance_id
            )
            .encode(
                "utf-8"
            )
        )

        if projected != source.read_bytes():
            raise RuntimeError(
                "script projection changed: "
                + str(source)
            )

    manifest = (
        subsystem_composer.manifest(
            subsystem
        )
    )

    validation = (
        graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "subsystem graph invalid"
        )

    result = {
        "subsystem_name": (
            "runtime.substrates"
        ),
        "subsystem_instance_id": (
            subsystem
            .subsystem_instance_id
        ),
        "subsystem_level": (
            subsystem_instance.level
        ),
        "engine_count": len(
            subsystem
            .engine_instance_ids
        ),
        "engines": [
            "runtime.spyral",
            "runtime.cypher",
        ],
        "composition_segues": len(
            subsystem.segue_ids
        ),
        "script_roundtrips": 4,
        "all_script_roundtrips_equal": (
            True
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
