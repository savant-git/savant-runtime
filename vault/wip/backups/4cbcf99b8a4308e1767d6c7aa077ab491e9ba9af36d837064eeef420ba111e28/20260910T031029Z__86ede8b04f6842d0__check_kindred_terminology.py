#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


schema = "savant.assurance.kindred-terminology-check.v1"
authority_effect = "none"

compiler_path = Path(
    "/root/savant-runtime/assurance/convergence/modularity/compilers/migrate_active_kinship_to_kindred.py"
)


class CheckError(
    RuntimeError
):
    pass


def load_compiler():
    spec = (
        importlib.util
        .spec_from_file_location(
            "migrate_active_kinship_to_kindred",
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
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return module


def check() -> dict[str, object]:
    compiler = load_compiler()

    mutable, preserved = (
        compiler.scan()
    )

    remaining = [
        {
            "path":
                str(
                    path
                ),
            "occurrences":
                count,
        }
        for (
            path,
            _before,
            _after,
            count,
        ) in mutable
    ]

    if remaining:
        raise CheckError(
            "active SAVANT-owned kinship "
            "terminology remains"
        )

    canonical_semantics = Path(
        "/root/savant-runtime/lexicon/kindred/canonical_semantics.py"
    )

    consumer_runtime = Path(
        "/root/savant-runtime/lexicon/kindred/consumer_runtime.py"
    )

    compatibility_projection = Path(
        "/root/savant-runtime/lexicon/kindred/compatibility_edge_projection.py"
    )

    legacy_bridge = Path(
        "/root/savant-runtime/lexicon/kindred/legacy_bridge.py"
    )

    required = (
        canonical_semantics,
        consumer_runtime,
        compatibility_projection,
        legacy_bridge,
    )

    missing = [
        str(
            path
        )
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise CheckError(
            "required Kindred implementation "
            "missing: "
            + ", ".join(
                missing
            )
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
        "active_legacy_term":
            "kinship",
        "remaining_active_matches":
            0,
        "historical_matches_preserved":
            len(
                preserved
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
                        str(
                            exc
                        ),
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
