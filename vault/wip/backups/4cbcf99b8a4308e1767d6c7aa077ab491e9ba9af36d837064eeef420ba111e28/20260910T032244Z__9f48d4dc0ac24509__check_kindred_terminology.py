#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


schema = "savant.assurance.kindred-terminology-check.v2"
authority_effect = "none"

compiler_path = Path(
    "/root/savant-runtime/assurance/convergence/modularity/compilers/migrate_active_kindred_to_kindred.py"
)


class CheckError(RuntimeError):
    pass


def load_compiler():
    module_name = (
        "savant_migrate_active_kindred_to_kindred"
    )

    spec = (
        importlib.util.spec_from_file_location(
            module_name,
            compiler_path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise CheckError(
            "cannot load terminology compiler"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        module_name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def check() -> dict[str, object]:
    compiler = load_compiler()

    active, preserved = (
        compiler.discover()
    )

    if active:
        raise CheckError(
            "active SAVANT-owned kindred "
            "terminology remains: "
            + json.dumps(
                active,
                sort_keys=True,
            )
        )

    required = (
        Path(
            "/root/savant-runtime/lexicon/kindred/canonical_semantics.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/consumer_runtime.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/compatibility_edge_projection.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/legacy_bridge.py"
        ),
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise CheckError(
            "required Kindred implementation "
            "missing: "
            + ", ".join(missing)
        )

    return {
        "schema":
            schema,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "canonical_term":
            "kindred",
        "deprecated_active_term":
            "kindred",
        "remaining_active_matches":
            0,
        "preserved_historical_files":
            len(preserved),
        "preserved_historical_occurrences":
            sum(
                int(item["occurrences"])
                for item in preserved
            ),
        "historical_evidence_mutated":
            False,
        "kindred_root":
            "/root/savant-runtime/lexicon/kindred",
    }


def main() -> int:
    try:
        print(
            json.dumps(
                check(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
