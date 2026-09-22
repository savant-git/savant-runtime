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

SOURCE = (
    RUNTIME
    / "program_edifice.py"
)


def load():
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
            "program_edifice",
            SOURCE,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "cannot load program edifice"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        "program_edifice"
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    module = load()

    edifice = (
        module.Programedifice()
    )

    validation = (
        edifice.validate()
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

    expected = (
        ("character", "line"),
        ("line", "segment"),
        ("segment", "snippet"),
        ("snippet", "script"),
        ("script", "engine"),
        ("engine", "subsystem"),
        ("subsystem", "system"),
        ("system", "application"),
    )

    segues = (
        edifice.segues()
    )

    if (
        segues
        != module.PROGRAM_edifice_SEGUES
    ):
        raise RuntimeError(
            "edifice does not expose "
            "authoritative segue instances"
        )

    observed = tuple(
        (
            segue.source_level,
            segue.target_level,
        )
        for segue
        in segues
    )

    if observed != expected:
        raise RuntimeError(
            "edifice segue topology "
            "mismatch"
        )

    if len(segues) != 8:
        raise RuntimeError(
            "edifice must contain "
            "8 adjacency segues"
        )

    if len(
        {
            segue.segue_id
            for segue
            in segues
        }
    ) != 8:
        raise RuntimeError(
            "edifice segue identities "
            "are not unique"
        )

    full_path = (
        edifice.segue_path(
            "character",
            "application",
        )
    )

    if full_path != segues:
        raise RuntimeError(
            "full edifice segue path "
            "does not equal authoritative "
            "segue sequence"
        )

    for ordinal, segue in enumerate(
        segues,
        start=1,
    ):
        if (
            segue.ordinal
            != ordinal
        ):
            raise RuntimeError(
                "edifice segue ordinal "
                "mismatch"
            )

        projection = (
            segue.projection()
        )

        authority = (
            projection.get(
                "authority",
                {},
            )
        )

        if (
            projection.get(
                "authoritative"
            )
            is not True
        ):
            raise RuntimeError(
                "edifice segue must "
                "be authoritative"
            )

        if (
            authority.get(
                "state"
            )
            != "accepted"
        ):
            raise RuntimeError(
                "edifice segue authority "
                "state must be accepted"
            )

        if not authority.get(
            "source"
        ):
            raise RuntimeError(
                "edifice segue authority "
                "source missing"
            )

        if (
            projection.get(
                "authority_effect"
            )
            != "edifice-definition"
        ):
            raise RuntimeError(
                "edifice segue authority "
                "effect mismatch"
            )

        if (
            projection.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise RuntimeError(
                "edifice segue mutation "
                "must remain forbidden"
            )

        if (
            projection.get(
                "functional_role"
            )
            != "composition"
        ):
            raise RuntimeError(
                "edifice segue role "
                "mismatch"
            )

        if (
            projection.get(
                "semantic_axis"
            )
            != "program-edifice"
        ):
            raise RuntimeError(
                "edifice segue semantic "
                "axis mismatch"
            )

        if (
            projection.get(
                "inheritance_policy"
            )
            != "none"
        ):
            raise RuntimeError(
                "edifice segue inheritance "
                "policy mismatch"
            )

        if (
            projection.get(
                "propagation_policy"
            )
            != "composition-only"
        ):
            raise RuntimeError(
                "edifice segue propagation "
                "policy mismatch"
            )

        if (
            projection.get(
                "valid"
            )
            is not True
        ):
            raise RuntimeError(
                "edifice segue invalid"
            )

        if not projection.get(
            "provenance"
        ):
            raise RuntimeError(
                "edifice segue provenance "
                "missing"
            )

        if (
            projection.get(
                "parent_instance"
            )
            != segue.target_level
        ):
            raise RuntimeError(
                "parent compatibility "
                "projection mismatch"
            )

        if (
            projection.get(
                "child_instance"
            )
            != segue.source_level
        ):
            raise RuntimeError(
                "child compatibility "
                "projection mismatch"
            )

    if (
        validation[
            "authority_primitive"
        ]
        != "PROGRAM_edifice_SEGUES"
    ):
        raise RuntimeError(
            "edifice authority primitive "
            "mismatch"
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

    result = {
        "owner": "exile:modus",
        "level_count": 9,
        "transition_count": 8,
        "segue_count": 8,
        "authority_primitive": (
            "PROGRAM_edifice_SEGUES"
        ),
        "authoritative_segue_count": 8,
        "typed_segues": True,
        "stable_segues": True,
        "unique_segue_ids": True,
        "full_path_rebuildable": True,
        "lineage_tuple_is_projection": True,
        "levels_are_projection": True,
        "indexes_are_projection": True,
        "parent_child_maps_are_projection": True,
        "segue_authoritative": True,
        "segue_authority_state": "accepted",
        "segue_authority_effect": (
            "edifice-definition"
        ),
        "mutation_authorized": False,
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
