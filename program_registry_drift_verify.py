#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
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

STORE_PATH = (
    MODUS_RUNTIME
    / "program_store.py"
)

REGISTRY_PATH = (
    MODUS_RUNTIME
    / "program_registry.py"
)

SUBJECT = (
    ROOT
    / "runtime"
    / "spyral"
    / "__init__.py"
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
    composition = load(
        "program_composition",
        COMPOSITION_PATH,
    )

    store_module = load(
        "program_store",
        STORE_PATH,
    )

    registry_module = load(
        "program_registry",
        REGISTRY_PATH,
    )

    with tempfile.TemporaryDirectory(
        prefix="savant-program-drift-",
        dir=str(
            ROOT
            / "runtime"
        ),
    ) as temporary_directory:
        temporary_root = Path(
            temporary_directory
        )

        temporary_source = (
            temporary_root
            / "spyral_init.py"
        )

        temporary_registry = (
            temporary_root
            / "registry.json"
        )

        temporary_store_root = (
            temporary_root
            / "instances"
        )

        shutil.copy2(
            SUBJECT,
            temporary_source,
        )

        graph = (
            composition
            .ProgramCompositionGraph()
        )

        decomposition = (
            graph.decompose_file(
                temporary_source
            )
        )

        store = (
            store_module
            .ProgramCompositionStore(
                root=temporary_store_root
            )
        )

        store_receipt = store.save(
            graph,
            decomposition,
        )

        registry = (
            registry_module
            .ProgramProjectionRegistry(
                path=temporary_registry
            )
        )

        registry.register(
            source_path=temporary_source,
            store_path=Path(
                store_receipt[
                    "path"
                ]
            ),
            decomposition=decomposition,
        )

        initial = (
            registry.verify_entry(
                temporary_source
            )
        )

        if initial["passed"] is not True:
            raise RuntimeError(
                "initial projection verification failed"
            )

        if initial["drift_detected"] is not False:
            raise RuntimeError(
                "false-positive drift detected"
            )

        original = (
            temporary_source.read_text(
                encoding="utf-8"
            )
        )

        temporary_source.write_text(
            original
            + "\n# deliberate drift probe\n",
            encoding="utf-8",
        )

        drifted = (
            registry.verify_entry(
                temporary_source
            )
        )

        if drifted["passed"] is not False:
            raise RuntimeError(
                "drift did not fail verification"
            )

        if drifted["source_matches"] is not False:
            raise RuntimeError(
                "drifted source incorrectly matched"
            )

        if drifted["projection_matches"] is not True:
            raise RuntimeError(
                "stored projection unexpectedly changed"
            )

        if drifted["drift_detected"] is not True:
            raise RuntimeError(
                "drift flag was not raised"
            )

        if (
            drifted[
                "current_source_digest"
            ]
            == drifted[
                "registered_digest"
            ]
        ):
            raise RuntimeError(
                "drifted digest did not change"
            )

        result = {
            "live_subject": str(
                SUBJECT
            ),
            "live_subject_modified": False,
            "isolated_source": str(
                temporary_source
            ),
            "initial_passed": (
                initial["passed"]
            ),
            "initial_drift_detected": (
                initial[
                    "drift_detected"
                ]
            ),
            "drifted_passed": (
                drifted["passed"]
            ),
            "drift_detected": (
                drifted[
                    "drift_detected"
                ]
            ),
            "source_matches_after_drift": (
                drifted[
                    "source_matches"
                ]
            ),
            "projection_matches_after_drift": (
                drifted[
                    "projection_matches"
                ]
            ),
            "mutation_authorized": (
                drifted[
                    "mutation_authorized"
                ]
            ),
            "projection_authoritative": (
                drifted[
                    "projection_authoritative"
                ]
            ),
            "authority_effect": (
                drifted[
                    "authority_effect"
                ]
            ),
            "fail_closed": True,
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
