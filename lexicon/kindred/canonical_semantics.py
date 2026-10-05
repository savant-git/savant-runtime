#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from dataclasses import dataclass
from types import ModuleType
from typing import Any


schema_version = "savant.kindred.canonical-semantics.v1"
authority_effect = "none"
owner = "kindred"

canonical_chain = (
    "direct_admitted_relationship",
    "reusable_role_profile_semantics",
    "purpose_specific_policy",
    "deterministic_family_algebra",
    "explainable_derived_relationship",
    "disposable_tree_graph_views",
)

canonical_modules = (
    "adoption_step_guardian",
    "alliance_affinity",
    "collateral_calculus",
    "descent_policy",
    "generational_calculus",
    "propagation_policy",
    "relationship_resolver",
    "role_calculus",
)

quarantined_modules = (
    "discipline_engine",
    "discipline_registry",
)

package_prefix = "lexicon.kindred"


class KindredCanonicalSemanticsError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CanonicalModule:
    name: str
    qualified_name: str
    module: ModuleType


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            value
        )
    ).hexdigest()


def qualified_name(
    module_name: str,
) -> str:
    if not isinstance(
        module_name,
        str,
    ) or not module_name:
        raise KindredCanonicalSemanticsError(
            "module name must be a non-empty string"
        )

    return (
        f"{package_prefix}.{module_name}"
    )


def require_not_quarantined(
    module_name: str,
) -> None:
    if module_name in quarantined_modules:
        raise KindredCanonicalSemanticsError(
            "quarantined kindred semantics "
            f"cannot enter canonical surface: {module_name}"
        )


def load_canonical_module(
    module_name: str,
) -> CanonicalModule:
    if module_name not in canonical_modules:
        raise KindredCanonicalSemanticsError(
            "module is not admitted to canonical "
            f"kindred semantics: {module_name}"
        )

    require_not_quarantined(
        module_name
    )

    target = qualified_name(
        module_name
    )

    module = importlib.import_module(
        target
    )

    return CanonicalModule(
        name=module_name,
        qualified_name=target,
        module=module,
    )


def load_canonical_surface() -> tuple[
    CanonicalModule,
    ...,
]:
    loaded = tuple(
        load_canonical_module(
            module_name
        )
        for module_name
        in canonical_modules
    )

    names = tuple(
        item.name
        for item in loaded
    )

    if names != canonical_modules:
        raise KindredCanonicalSemanticsError(
            "canonical module order changed"
        )

    return loaded


def surface_projection() -> dict[str, Any]:
    loaded = load_canonical_surface()

    modules = [
        {
            "name":
                item.name,
            "qualified_name":
                item.qualified_name,
        }
        for item in loaded
    ]

    substance = {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "canonical_chain":
            list(
                canonical_chain
            ),
        "canonical_modules":
            modules,
        "quarantined_modules":
            list(
                quarantined_modules
            ),
        "discipline_semantics_canonical":
            False,
        "projection":
            True,
        "mutation_authority":
            False,
    }

    return {
        **substance,
        "projection_digest":
            digest(
                substance
            ),
    }


def self_check() -> dict[str, Any]:
    first = surface_projection()
    second = surface_projection()

    if first != second:
        raise KindredCanonicalSemanticsError(
            "canonical kindred surface "
            "is not deterministic"
        )

    if (
        first.get(
            "mutation_authority"
        )
        is not False
    ):
        raise KindredCanonicalSemanticsError(
            "canonical kindred surface "
            "acquired mutation authority"
        )

    if (
        first.get(
            "discipline_semantics_canonical"
        )
        is not False
    ):
        raise KindredCanonicalSemanticsError(
            "discipline semantics escaped quarantine"
        )

    admitted = {
        item[
            "name"
        ]
        for item in first[
            "canonical_modules"
        ]
    }

    quarantined = set(
        first[
            "quarantined_modules"
        ]
    )

    overlap = sorted(
        admitted
        & quarantined
    )

    if overlap:
        raise KindredCanonicalSemanticsError(
            "canonical/quarantined module overlap: "
            + ", ".join(
                overlap
            )
        )

    if tuple(
        first[
            "canonical_chain"
        ]
    ) != canonical_chain:
        raise KindredCanonicalSemanticsError(
            "canonical semantic chain changed"
        )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "discipline_semantics_canonical":
            False,
        "canonical_module_count":
            len(
                canonical_modules
            ),
        "quarantined_module_count":
            len(
                quarantined_modules
            ),
        "canonical_chain_length":
            len(
                canonical_chain
            ),
        "projection_digest":
            first[
                "projection_digest"
            ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "project",
            "self-check",
        ),
        nargs="?",
        default="self-check",
    )

    arguments = parser.parse_args()

    try:
        if arguments.command == "project":
            result = surface_projection()
        else:
            result = self_check()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
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
