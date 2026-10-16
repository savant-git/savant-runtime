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

PARENT_PATH = (
    MODUS_RUNTIME
    / "program_parent.py"
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
        for path
        in SOURCES.values()
        if not path.is_file()
    ]

    if missing:
        raise RuntimeError(
            "missing source: "
            + ", ".join(
                missing
            )
        )

    composition_module = load(
        "program_composition",
        COMPOSITION_PATH,
    )

    parent_module = load(
        "program_parent",
        PARENT_PATH,
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

    composer = (
        parent_module
        .ProgramParentComposer(
            graph
        )
    )

    spyral = composer.compose(
        level="engine",
        name="runtime.spyral",
        child_instance_ids=(
            decompositions[
                "spyral_init"
            ].script_instance_id,
            decompositions[
                "spyral_engine"
            ].script_instance_id,
        ),
        lineage=(
            "living:spyral",
        ),
        provenance=(
            "verified-live-implementation",
        ),
    )

    cypher = composer.compose(
        level="engine",
        name="runtime.cypher",
        child_instance_ids=(
            decompositions[
                "cypher_init"
            ].script_instance_id,
            decompositions[
                "cypher_engine"
            ].script_instance_id,
        ),
        lineage=(
            "living:cypher",
        ),
        provenance=(
            "verified-live-implementation",
        ),
    )

    subsystem = composer.compose(
        level="subsystem",
        name="runtime.substrates",
        child_instance_ids=(
            spyral.instance_id,
            cypher.instance_id,
        ),
        lineage=(
            "savant:runtime",
        ),
        provenance=(
            "verified-runtime-substrates",
        ),
    )

    system = composer.compose(
        level="system",
        name="savant.runtime",
        child_instance_ids=(
            subsystem.instance_id,
        ),
        lineage=(
            "savant",
        ),
        provenance=(
            "verified-live-runtime",
        ),
    )

    application = composer.compose(
        level="application",
        name="savant",
        child_instance_ids=(
            system.instance_id,
        ),
        lineage=(
            "reality",
        ),
        provenance=(
            "verified-compositional-projection",
        ),
    )

    expected_levels = {
        spyral.instance_id: (
            "engine"
        ),
        cypher.instance_id: (
            "engine"
        ),
        subsystem.instance_id: (
            "subsystem"
        ),
        system.instance_id: (
            "system"
        ),
        application.instance_id: (
            "application"
        ),
    }

    for instance_id, level in (
        expected_levels.items()
    ):
        if (
            graph.instance(
                instance_id
            ).level
            != level
        ):
            raise RuntimeError(
                "level mismatch: "
                + instance_id
            )

    roundtrips = 0

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

        if (
            projected
            != source.read_bytes()
        ):
            raise RuntimeError(
                "source projection "
                "changed: "
                + str(source)
            )

        roundtrips += 1

    validation = (
        graph.validate()
    )

    if validation[
        "valid"
    ] is not True:
        raise RuntimeError(
            "generic edifice graph invalid"
        )

    manifest = composer.manifest(
        application
    )

    result = {
        "generic_parent_levels": (
            parent_module
            .PARENT_LEVELS
        ),
        "engine_count": 2,
        "subsystem_count": 1,
        "system_count": 1,
        "application_count": 1,
        "script_roundtrips": (
            roundtrips
        ),
        "all_script_roundtrips_equal": (
            True
        ),
        "engine_segues": (
            len(spyral.segue_ids)
            + len(cypher.segue_ids)
        ),
        "subsystem_segues": len(
            subsystem.segue_ids
        ),
        "system_segues": len(
            system.segue_ids
        ),
        "application_segues": len(
            application.segue_ids
        ),
        "graph_valid": (
            validation["valid"]
        ),
        "manifest_rebuildable": (
            manifest[
                "rebuildable"
            ]
        ),
        "duplicate_parent_mechanism": (
            False
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
