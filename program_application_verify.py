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

SYSTEM_PATH = (
    MODUS_RUNTIME
    / "program_system.py"
)

APPLICATION_PATH = (
    MODUS_RUNTIME
    / "program_application.py"
)

SOURCES = {
    "spyral_init": (
        ROOT
        / "runtime"
        / "spyral"
        / "__init__.py"
    ),
    "spyral_engine": (
        ROOT
        / "runtime"
        / "spyral"
        / "engine.py"
    ),
    "cypher_init": (
        ROOT
        / "runtime"
        / "cypher"
        / "__init__.py"
    ),
    "cypher_engine": (
        ROOT
        / "runtime"
        / "cypher"
        / "engine.py"
    ),
}

EXPECTED_LEVELS = (
    "character",
    "line",
    "segment",
    "snippet",
    "script",
    "engine",
    "subsystem",
    "system",
    "application",
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


def main() -> int:
    missing = [
        str(path)
        for path in SOURCES.values()
        if not path.is_file()
    ]

    if missing:
        raise RuntimeError(
            "missing live source: "
            + ", ".join(missing)
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

    system_module = load(
        "program_system",
        SYSTEM_PATH,
    )

    application_module = load(
        "program_application",
        APPLICATION_PATH,
    )

    if tuple(
        composition_module
        .PROGRAM_LEVELS
    ) != EXPECTED_LEVELS:
        raise RuntimeError(
            "program edifice mismatch"
        )

    graph = (
        composition_module
        .ProgramCompositionGraph()
    )

    decompositions = {
        name: graph.decompose_file(
            path
        )
        for name, path
        in SOURCES.items()
    }

    engine_composer = (
        engine_module
        .ProgramEngineComposer(
            graph
        )
    )

    spyral = engine_composer.compose(
        (
            decompositions[
                "spyral_init"
            ],
            decompositions[
                "spyral_engine"
            ],
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
            decompositions[
                "cypher_init"
            ],
            decompositions[
                "cypher_engine"
            ],
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

    runtime_substrates = (
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
                "verified-runtime-substrates",
            ),
        )
    )

    system_composer = (
        system_module
        .ProgramSystemComposer(
            graph
        )
    )

    runtime_system = (
        system_composer.compose(
            (
                runtime_substrates,
            ),
            system_name=(
                "savant.runtime"
            ),
            lineage=(
                "savant",
            ),
            provenance=(
                "verified-live-runtime",
            ),
        )
    )

    application_composer = (
        application_module
        .ProgramApplicationComposer(
            graph
        )
    )

    application = (
        application_composer.compose(
            (
                runtime_system,
            ),
            application_name=(
                "savant"
            ),
            lineage=(
                "reality",
            ),
            provenance=(
                "verified-compositional-projection",
            ),
        )
    )

    root = graph.instance(
        application
        .application_instance_id
    )

    if root.level != "application":
        raise RuntimeError(
            "root is not application"
        )

    if len(root.children) != 1:
        raise RuntimeError(
            "expected one system child"
        )

    system = graph.instance(
        root.children[0]
    )

    if system.level != "system":
        raise RuntimeError(
            "application child "
            "is not system"
        )

    roundtrip_count = 0

    for name, decomposition in (
        decompositions.items()
    ):
        source = SOURCES[
            name
        ]

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
                "source round-trip changed: "
                + str(source)
            )

        roundtrip_count += 1

    validation = (
        graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "application graph invalid"
        )

    manifest = (
        application_composer.manifest(
            application
        )
    )

    descendant_levels = {
        graph.instance(
            instance_id
        ).level
        for instance_id
        in graph.descendants(
            application
            .application_instance_id
        )
    }

    required_composite_levels = {
        "script",
        "engine",
        "subsystem",
        "system",
    }

    missing_composite_levels = sorted(
        required_composite_levels
        - descendant_levels
    )

    if missing_composite_levels:
        raise RuntimeError(
            "missing composite levels: "
            + ", ".join(
                missing_composite_levels
            )
        )

    result = {
        "application_name": "savant",
        "application_instance_id": (
            application
            .application_instance_id
        ),
        "root_level": root.level,
        "program_levels": list(
            EXPECTED_LEVELS
        ),
        "program_level_count": len(
            EXPECTED_LEVELS
        ),
        "engine_count": 2,
        "subsystem_count": 1,
        "system_count": 1,
        "application_count": 1,
        "script_roundtrips": (
            roundtrip_count
        ),
        "all_script_roundtrips_equal": (
            True
        ),
        "composite_levels_present": (
            True
        ),
        "missing_composite_levels": (
            missing_composite_levels
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
        "projection_authoritative": False,
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
