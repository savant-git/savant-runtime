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

edifice_PATH = (
    RUNTIME
    / "program_edifice.py"
)

PARENT_PATH = (
    RUNTIME
    / "program_parent.py"
)


def load(
    name: str,
    path: Path,
):
    runtime_path = str(
        RUNTIME
    )

    if runtime_path not in sys.path:
        sys.path.insert(
            0,
            runtime_path,
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"cannot load {path}"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    edifice_module = load(
        "program_edifice",
        edifice_PATH,
    )

    parent_module = load(
        "program_parent",
        PARENT_PATH,
    )

    edifice = (
        edifice_module
        .Programedifice()
    )

    validation = (
        edifice.validate()
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

    segues = (
        edifice_module
        .PROGRAM_edifice_SEGUES
    )

    if len(segues) != 8:
        raise RuntimeError(
            "authoritative program segue "
            "count mismatch"
        )

    if (
        edifice_module
        .PROGRAM_edifice_LINEAGE
        != expected_lineage
    ):
        raise RuntimeError(
            "projected program lineage "
            "mismatch"
        )

    if (
        edifice_module
        .project_program_lineage(
            segues
        )
        != expected_lineage
    ):
        raise RuntimeError(
            "lineage tuple is not "
            "deterministically projected "
            "from authoritative segues"
        )

    if (
        edifice_module
        .PROGRAM_LEVELS
        != expected_levels
    ):
        raise RuntimeError(
            "projected program edifice "
            "mismatch"
        )

    if (
        edifice_module
        .project_program_levels(
            segues
        )
        != expected_levels
    ):
        raise RuntimeError(
            "program levels are not "
            "deterministically projected "
            "from authoritative segues"
        )

    if (
        validation[
            "valid"
        ]
        is not True
    ):
        raise RuntimeError(
            "program edifice invalid"
        )

    if (
        validation[
            "authority_primitive"
        ]
        != "PROGRAM_edifice_SEGUES"
    ):
        raise RuntimeError(
            "incorrect edifice authority "
            "primitive"
        )

    if (
        validation[
            "authoritative_segue_count"
        ]
        != 8
    ):
        raise RuntimeError(
            "authoritative edifice "
            "segue count mismatch"
        )

    for key in (
        "lineage_tuple_is_projection",
        "levels_are_projection",
        "indexes_are_projection",
        "parent_child_maps_are_projection",
    ):
        if (
            validation[
                key
            ]
            is not True
        ):
            raise RuntimeError(
                f"{key} invariant failed"
            )

    if (
        edifice.path(
            "character",
            "application",
        )
        != expected_levels
    ):
        raise RuntimeError(
            "forward edifice path invalid"
        )

    if (
        edifice.distance(
            "character",
            "application",
        )
        != 8
    ):
        raise RuntimeError(
            "edifice distance invalid"
        )

    expected_parent_levels = {
        "engine": "script",
        "subsystem": "engine",
        "system": "subsystem",
        "application": "system",
    }

    if (
        parent_module
        .PARENT_LEVELS
        != expected_parent_levels
    ):
        raise RuntimeError(
            "parent composer edifice "
            "projection mismatch"
        )

    result = {
        "levels": list(
            expected_levels
        ),
        "level_count": 9,
        "transition_count": 8,
        "authority_primitive": (
            "PROGRAM_edifice_SEGUES"
        ),
        "authoritative_segue_count": 8,
        "lineage_tuple_is_projection": True,
        "levels_are_projection": True,
        "indexes_are_projection": True,
        "parent_child_maps_are_projection": True,
        "character_root": (
            edifice.child_of(
                "character"
            )
            is None
        ),
        "application_terminal": (
            edifice.parent_of(
                "application"
            )
            is None
        ),
        "character_to_application_distance": 8,
        "parent_composer_derived": True,
        "duplicate_upper_edifice_authority": False,
        "owner": "exile:modus",
        "authoritative": False,
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
