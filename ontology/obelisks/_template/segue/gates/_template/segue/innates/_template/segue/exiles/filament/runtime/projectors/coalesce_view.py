from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

COALESCE = (
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
    / "segue"
    / "prodigals"
    / "coalesce"
)

COALESCE_RUNTIME_DIR = (
    COALESCE
    / "runtime"
)

COALESCE_RUNTIME = (
    COALESCE_RUNTIME_DIR
    / "coalesce.py"
)


def load_coalesce():
    if not COALESCE_RUNTIME.is_file():
        raise RuntimeError(
            f"Coalesce runtime missing: {COALESCE_RUNTIME}"
        )

    runtime_path = str(
        COALESCE_RUNTIME_DIR
    )

    if runtime_path not in sys.path:
        sys.path.insert(
            0,
            runtime_path,
        )

    spec = importlib.util.spec_from_file_location(
        "savant_coalesce_runtime",
        COALESCE_RUNTIME,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Unable to load Coalesce runtime."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def derive_coalesce_view(
    recipe: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    coalesce = load_coalesce()

    execution = coalesce.execute_recipe(
        recipe,
        context or {},
    )

    artifacts = execution.get(
        "artifacts",
        {},
    )

    records = execution.get(
        "records",
        [],
    )

    trace = execution.get(
        "trace",
        [],
    )

    coalesce_state = execution.get(
        "coalesce",
        {},
    )

    return {
        "id": (
            "wavre:filament:"
            f"coalesce:{recipe}"
        ),
        "kind": "ui_wavre",
        "owner": "exile:filament",
        "source": "prodigal:modus:coalesce",
        "recipe": recipe,
        "authority_effect": "none",
        "rebuildable": True,
        "records": records,
        "artifacts": artifacts,
        "trace": trace,
        "composition": {
            "piece_count": (
                coalesce_state.get(
                    "piece_count"
                )
            ),
            "digest": (
                coalesce_state.get(
                    "composition_digest"
                )
            ),
        },
        "interface": {
            "summary": {
                "record_count": len(
                    records
                ),
                "executed_piece_count": len(
                    trace
                ),
                "artifact_count": len(
                    artifacts
                ),
            },
            "records": [
                {
                    "id": row.get(
                        "id"
                    ),
                    "title": row.get(
                        "title",
                        row.get(
                            "name",
                            row.get(
                                "id"
                            ),
                        ),
                    ),
                    "date": row.get(
                        "date",
                        row.get(
                            "occurred_at",
                            "",
                        ),
                    ),
                    "kind": row.get(
                        "kind",
                        row.get(
                            "type",
                            "record",
                        ),
                    ),
                    "status": row.get(
                        "status",
                        "unknown",
                    ),
                    "category": row.get(
                        "category",
                        row.get(
                            "domain",
                            row.get(
                                "owner",
                                "general",
                            ),
                        ),
                    ),
                    "preview": row.get(
                        "preview",
                        row.get(
                            "description",
                            row.get(
                                "summary",
                                "",
                            ),
                        ),
                    ),
                    "provenance": row.get(
                        "provenance"
                    ),
                    "relationships": row.get(
                        "relationships",
                        [],
                    ),
                }
                for row in records
            ],
        },
    }
