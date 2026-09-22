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

IMPLEMENTATION = (
    MODUS_RUNTIME
    / "program_composition.py"
)

SUBJECT = (
    ROOT
    / "runtime"
    / "spyral"
    / "__init__.py"
)

EXPECTED_SUBJECT_SHA256 = (
    "6569b5e802c556ef6b371358ab770eb7"
    "ad6c6c54250f870ad75880e19687c125"
)


def sha256(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def prepare_import_path() -> None:
    runtime_path = str(
        MODUS_RUNTIME
    )

    if runtime_path not in sys.path:
        sys.path.insert(
            0,
            runtime_path,
        )


def load_module():
    prepare_import_path()

    specification = (
        importlib.util
        .spec_from_file_location(
            "savant_program_composition",
            IMPLEMENTATION,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise RuntimeError(
            "unable to load program composition module"
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def main() -> int:
    module = load_module()

    source_bytes = (
        SUBJECT.read_bytes()
    )

    source_digest = sha256(
        source_bytes
    )

    if (
        source_digest
        != EXPECTED_SUBJECT_SHA256
    ):
        raise RuntimeError(
            "verified subject baseline drift: "
            f"{SUBJECT}: "
            f"expected "
            f"{EXPECTED_SUBJECT_SHA256}, "
            f"found {source_digest}"
        )

    graph = (
        module.ProgramCompositionGraph()
    )

    decomposition = (
        graph.decompose_file(
            SUBJECT
        )
    )

    validation = (
        graph.validate()
    )

    if validation["valid"] is not True:
        raise RuntimeError(
            "program composition graph invalid"
        )

    projected_text = (
        graph.project_text(
            decomposition.script_instance_id
        )
    )

    projected_bytes = (
        projected_text.encode(
            "utf-8"
        )
    )

    projected_digest = sha256(
        projected_bytes
    )

    if projected_bytes != source_bytes:
        raise RuntimeError(
            "round-trip bytes differ"
        )

    if projected_digest != source_digest:
        raise RuntimeError(
            "round-trip digest differs"
        )

    if (
        decomposition.source_digest
        != source_digest
    ):
        raise RuntimeError(
            "decomposition source digest differs"
        )

    manifest = (
        graph.project_manifest(
            decomposition.script_instance_id
        )
    )

    if (
        manifest["rebuildable"]
        is not True
    ):
        raise RuntimeError(
            "projection is not marked rebuildable"
        )

    repeated_character_test = (
        "aaa\n\nbb\n"
    )

    repeat_graph = (
        module.ProgramCompositionGraph()
    )

    repeat = (
        repeat_graph.decompose_text(
            repeated_character_test,
            source_path=(
                "verification://"
                "repeated-characters"
            ),
        )
    )

    if (
        repeat_graph.project_text(
            repeat.script_instance_id
        )
        != repeated_character_test
    ):
        raise RuntimeError(
            "repeated-character or blank-line "
            "projection regression"
        )

    edifice = (
        graph.edifice
    )

    edifice_validation = (
        edifice.validate()
    )

    if (
        edifice_validation[
            "valid"
        ]
        is not True
    ):
        raise RuntimeError(
            "shared program edifice invalid"
        )

    if (
        edifice_validation[
            "level_count"
        ]
        != 9
    ):
        raise RuntimeError(
            "program edifice must contain 9 levels"
        )

    if (
        edifice_validation[
            "segue_count"
        ]
        != 8
    ):
        raise RuntimeError(
            "program edifice must contain "
            "8 adjacency segues"
        )

    result = {
        "subject": str(
            SUBJECT
        ),
        "baseline_sha256": (
            source_digest
        ),
        "projected_sha256": (
            projected_digest
        ),
        "byte_for_byte_equal": (
            projected_bytes
            == source_bytes
        ),
        "source_bytes": len(
            source_bytes
        ),
        "program_levels": len(
            module.PROGRAM_LEVELS
        ),
        "edifice_level_count": (
            edifice_validation[
                "level_count"
            ]
        ),
        "edifice_segue_count": (
            edifice_validation[
                "segue_count"
            ]
        ),
        "edifice_single_source": True,
        "segment_present": (
            module.PROGRAM_LEVELS[2]
            == "segment"
        ),
        "line_count": len(
            decomposition.line_ids
        ),
        "segment_count": len(
            decomposition.segment_ids
        ),
        "snippet_count": len(
            decomposition.snippet_ids
        ),
        "segue_count": len(
            decomposition.segue_ids
        ),
        "repeated_characters_preserved": True,
        "blank_lines_preserved": True,
        "line_terminators_preserved": True,
        "rebuildable": (
            manifest["rebuildable"]
        ),
        "authoritative": (
            manifest["authoritative"]
        ),
        "authority_effect": (
            manifest[
                "authority_effect"
            ]
        ),
        "owner": graph.owner,
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
