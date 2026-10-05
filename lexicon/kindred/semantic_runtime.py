#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Mapping


schema = "savant.kindred.semantic-runtime.v1"
authority_effect = "none"
owner = "kindred"

canonical_module_names = (
    "adoption_step_guardian",
    "alliance_affinity",
    "collateral_calculus",
    "descent_policy",
    "generational_calculus",
    "propagation_policy",
    "relationship_resolver",
    "role_calculus",
)

quarantined_module_names = (
    "discipline_engine",
    "discipline_registry",
)

canonical_stage_order = (
    "direct_admitted_relationship",
    "reusable_role_profile_semantics",
    "purpose_specific_policy",
    "deterministic_family_algebra",
    "explainable_derived_relationship",
    "disposable_tree_graph_views",
)

module_contracts: dict[
    str,
    tuple[str, ...],
] = {
    "adoption_step_guardian": (
        "adoption",
        "step_relation",
        "guardianship",
        "foster_relation",
        "legal_relation",
        "lateral_adoption",
    ),
    "alliance_affinity": (
        "alliance",
        "affinity",
    ),
    "collateral_calculus": (
        "derive_aunt_uncle_niece_nephew",
        "enhancements",
        "health",
    ),
    "descent_policy": (
        "policy",
        "policy_for",
        "qualifies",
        "compatible_path",
        "enhancements",
        "health",
    ),
    "generational_calculus": (
        "derive_generational_roles",
        "derive_grand_roles",
        "enhancements",
        "health",
    ),
    "propagation_policy": (
        "policy",
        "policy_for",
        "decide",
        "enhancements",
        "health",
    ),
    "relationship_resolver": (
        "KindredRelationshipResolver",
    ),
    "role_calculus": (
        "ascending_role",
        "descending_role",
        "lateral_role",
        "derive_full_half",
        "aunt_uncle_role",
        "niece_nephew_role",
        "cousin_role",
        "alliance_role",
        "guardian_role",
        "affinity_ascending_role",
        "affinity_descending_role",
        "affinity_lateral_role",
        "cousin_coordinates",
        "cousin_from_distances",
        "reciprocal_descent",
        "reciprocal_lateral",
        "reciprocal_aunt_nephew",
        "reciprocal_cousins",
        "canonical_profile_catalog",
        "enhancements",
        "health",
    ),
}


class KindredSemanticRuntimeError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class ModuleBinding:
    name: str
    module: ModuleType
    capabilities: Mapping[
        str,
        Callable[..., Any] | type,
    ]

    def capability(
        self,
        name: str,
    ) -> Callable[..., Any] | type:
        capability = self.capabilities.get(
            name
        )

        if capability is None:
            raise KindredSemanticRuntimeError(
                f"{self.name} does not expose "
                f"canonical capability {name!r}"
            )

        return capability


def _load_module(
    name: str,
) -> ModuleType:
    candidates = (
        f"lexicon.kindred.{name}",
        name,
    )

    errors: list[str] = []

    for candidate in candidates:
        try:
            return importlib.import_module(
                candidate
            )

        except ModuleNotFoundError as exc:
            errors.append(
                f"{candidate}: {exc}"
            )

    raise KindredSemanticRuntimeError(
        f"cannot load canonical Kindred module "
        f"{name!r}: "
        + " | ".join(
            errors
        )
    )


def _bind_module(
    name: str,
) -> ModuleBinding:
    module = _load_module(
        name
    )

    expected = module_contracts[
        name
    ]

    capabilities: dict[
        str,
        Callable[..., Any] | type,
    ] = {}

    missing = []

    for capability_name in expected:
        value = getattr(
            module,
            capability_name,
            None,
        )

        if value is None:
            missing.append(
                capability_name
            )
            continue

        if not callable(
            value
        ):
            raise KindredSemanticRuntimeError(
                f"{name}.{capability_name} "
                "exists but is not callable"
            )

        capabilities[
            capability_name
        ] = value

    if missing:
        raise KindredSemanticRuntimeError(
            f"{name} is missing canonical "
            "capabilities: "
            + ", ".join(
                missing
            )
        )

    return ModuleBinding(
        name=name,
        module=module,
        capabilities=capabilities,
    )


class KindredSemanticRuntime:
    """
    Composition boundary for Kindred semantics.

    This runtime does not create relationship authority.

    It binds the existing canonical Kindred modules into one
    deterministic capability surface while keeping authority-bearing
    primitives, policy evaluation, family algebra, derivation, and
    disposable projections distinct.
    """

    def __init__(
        self,
    ) -> None:
        self._bindings = {
            name: _bind_module(
                name
            )
            for name in canonical_module_names
        }

    @property
    def bindings(
        self,
    ) -> Mapping[
        str,
        ModuleBinding,
    ]:
        return dict(
            self._bindings
        )

    def module(
        self,
        name: str,
    ) -> ModuleBinding:
        if name in quarantined_module_names:
            raise KindredSemanticRuntimeError(
                f"{name!r} is quarantined and "
                "cannot participate in canonical "
                "Kindred semantics"
            )

        binding = self._bindings.get(
            name
        )

        if binding is None:
            raise KindredSemanticRuntimeError(
                f"{name!r} is not a canonical "
                "Kindred module"
            )

        return binding

    def invoke(
        self,
        module_name: str,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        binding = self.module(
            module_name
        )

        capability = binding.capability(
            capability_name
        )

        return capability(
            *args,
            **kwargs,
        )

    def resolver(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        resolver_class = self.module(
            "relationship_resolver"
        ).capability(
            "KindredRelationshipResolver"
        )

        return resolver_class(
            *args,
            **kwargs,
        )

    def role(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "role_calculus",
            capability_name,
            *args,
            **kwargs,
        )

    def generational(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "generational_calculus",
            capability_name,
            *args,
            **kwargs,
        )

    def collateral(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "collateral_calculus",
            capability_name,
            *args,
            **kwargs,
        )

    def descent(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "descent_policy",
            capability_name,
            *args,
            **kwargs,
        )

    def propagation(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "propagation_policy",
            capability_name,
            *args,
            **kwargs,
        )

    def bond(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "adoption_step_guardian",
            capability_name,
            *args,
            **kwargs,
        )

    def affinity(
        self,
        capability_name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return self.invoke(
            "alliance_affinity",
            capability_name,
            *args,
            **kwargs,
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,
            "authority_effect":
                authority_effect,
            "owner":
                owner,
            "mutation_authority":
                False,
            "projection_only":
                False,
            "relationship_authority_created":
                False,
            "canonical_stage_order":
                list(
                    canonical_stage_order
                ),
            "canonical_modules": {
                name: sorted(
                    binding.capabilities
                )
                for name, binding
                in sorted(
                    self._bindings.items()
                )
            },
            "quarantined_modules":
                list(
                    quarantined_module_names
                ),
            "discipline_modules_participate":
                False,
        }


def self_check() -> dict[str, Any]:
    runtime = KindredSemanticRuntime()

    manifest = runtime.manifest()

    if manifest[
        "relationship_authority_created"
    ] is not False:
        raise KindredSemanticRuntimeError(
            "semantic runtime created "
            "relationship authority"
        )

    if manifest[
        "mutation_authority"
    ] is not False:
        raise KindredSemanticRuntimeError(
            "semantic runtime acquired "
            "mutation authority"
        )

    if manifest[
        "discipline_modules_participate"
    ] is not False:
        raise KindredSemanticRuntimeError(
            "quarantined discipline modules "
            "entered canonical runtime"
        )

    if tuple(
        manifest[
            "canonical_stage_order"
        ]
    ) != canonical_stage_order:
        raise KindredSemanticRuntimeError(
            "canonical Kindred semantic "
            "stage order changed"
        )

    for module_name in canonical_module_names:
        expected = set(
            module_contracts[
                module_name
            ]
        )

        actual = set(
            manifest[
                "canonical_modules"
            ][
                module_name
            ]
        )

        if actual != expected:
            raise KindredSemanticRuntimeError(
                f"{module_name} capability "
                "contract mismatch"
            )

    return {
        **manifest,
        "status":
            "passed",
    }


def main() -> int:
    try:
        print(
            json.dumps(
                self_check(),
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
                    "owner":
                        owner,
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
