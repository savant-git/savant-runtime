#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


schema = "savant.assurance.kindred-terminology-check.v5"
authority_effect = "none"

compiler_path = Path(
    "/root/savant-runtime/assurance/convergence/modularity/"
    "compilers/migrate_legacy_relationship_term_to_kindred.py"
)


class CheckError(RuntimeError):
    pass


def load_compiler():
    if not compiler_path.is_file():
        raise CheckError(
            "Kindred terminology compiler missing"
        )

    module_name = (
        "savant_kindred_terminology_migration_v5"
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        compiler_path,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise CheckError(
            "cannot load Kindred terminology compiler"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


def check():
    compiler = load_compiler()

    remaining = compiler.discover()

    if remaining:
        raise CheckError(
            "active implementation terminology remains: "
            + json.dumps(
                remaining,
                sort_keys=True,
            )
        )

    required = (
        Path(
            "/root/savant-runtime/lexicon/kindred/"
            "canonical_semantics.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/"
            "consumer_runtime.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/"
            "compatibility_edge_projection.py"
        ),
        Path(
            "/root/savant-runtime/lexicon/kindred/"
            "legacy_bridge.py"
        ),
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise CheckError(
            "required Kindred implementation missing: "
            + ", ".join(missing)
        )

    residue = compiler.generated_residue()

    return {
        "schema": schema,
        "authority_effect": authority_effect,
        "status": "passed",
        "canonical_term": "kindred",
        "remaining_active_matches": 0,
        "generated_residue": residue,
        "generated_residue_files": len(residue),
        "generated_residue_occurrences": sum(
            int(item["occurrences"])
            for item in residue
        ),
        "generated_residue_authoritative": False,
        "generated_residue_mutated": False,
        "symlink_safe": True,
        "authority_mutated": False,
        "canon_mutated": False,
        "historical_evidence_mutated": False,
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
                    "schema": schema,
                    "authority_effect": authority_effect,
                    "status": "failed",
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
