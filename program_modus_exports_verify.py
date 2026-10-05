#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
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


def load_runtime():
    parent = (
        RUNTIME.parent
    )

    parent_text = str(
        parent
    )

    if parent_text not in sys.path:
        sys.path.insert(
            0,
            parent_text,
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            "modus_runtime_verify",
            RUNTIME
            / "__init__.py",
            submodule_search_locations=[
                str(
                    RUNTIME
                )
            ],
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "cannot load Modus runtime"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        "modus_runtime_verify"
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    module = load_runtime()

    required = (
        "PROGRAM_edifice_SEGUES",
        "PROGRAM_edifice_LINEAGE",
        "PROGRAM_LEVELS",
        "PROGRAM_LEVEL_INDEX",
        "PROGRAM_CHILD_LEVEL",
        "PROGRAM_PARENT_LEVEL",
        "ProgramedificeSegue",
        "Programedifice",
        "ProgramLevel",
        "make_program_edifice_segue",
        "project_program_levels",
        "project_program_lineage",
        "ProgramCompositionGraph",
        "ProgramInstance",
        "CodeSegue",
        "ProgramCompositionStore",
        "ProgramProjectionRegistry",
        "ProgramParentComposer",
        "ProgramEngineComposer",
        "ProgramSubsystemComposer",
        "ProgramSystemComposer",
        "ProgramApplicationComposer",
    )

    missing = tuple(
        name
        for name in required
        if not hasattr(
            module,
            name,
        )
    )

    if missing:
        raise RuntimeError(
            "missing Modus exports: "
            + ", ".join(
                missing
            )
        )

    missing_all = tuple(
        name
        for name in required
        if name not in module.__all__
    )

    if missing_all:
        raise RuntimeError(
            "missing Modus __all__ exports: "
            + ", ".join(
                missing_all
            )
        )

    segues = (
        module
        .PROGRAM_edifice_SEGUES
    )

    if len(segues) != 8:
        raise RuntimeError(
            "public edifice segue "
            "count must be 8"
        )

    expected_levels = (
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

    if (
        module.project_program_levels(
            segues
        )
        != expected_levels
    ):
        raise RuntimeError(
            "public level projection "
            "mismatch"
        )

    expected_lineage = (
        ("line", "character"),
        ("segment", "line"),
        ("snippet", "segment"),
        ("script", "snippet"),
        ("engine", "script"),
        ("subsystem", "engine"),
        ("system", "subsystem"),
        ("application", "system"),
    )

    if (
        module.project_program_lineage(
            segues
        )
        != expected_lineage
    ):
        raise RuntimeError(
            "public lineage projection "
            "mismatch"
        )

    if (
        module.PROGRAM_LEVELS
        != expected_levels
    ):
        raise RuntimeError(
            "PROGRAM_LEVELS projection "
            "mismatch"
        )

    if (
        module.PROGRAM_edifice_LINEAGE
        != expected_lineage
    ):
        raise RuntimeError(
            "PROGRAM_edifice_LINEAGE "
            "projection mismatch"
        )

    edifice = (
        module.Programedifice()
    )

    validation = (
        edifice.validate()
    )

    if (
        validation["valid"]
        is not True
    ):
        raise RuntimeError(
            "exported edifice invalid"
        )

    if (
        validation[
            "authority_primitive"
        ]
        != "PROGRAM_edifice_SEGUES"
    ):
        raise RuntimeError(
            "exported edifice authority "
            "primitive mismatch"
        )

    result = {
        "owner": "exile:modus",
        "required_exports": len(
            required
        ),
        "missing_exports": [],
        "edifice_authority_exported": True,
        "edifice_authority_primitive": (
            "PROGRAM_edifice_SEGUES"
        ),
        "authoritative_segue_count": 8,
        "projected_level_count": 9,
        "projected_transition_count": 8,
        "compatibility_lineage_exported": True,
        "compatibility_maps_exported": True,
        "composition_surfaces_exported": True,
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
