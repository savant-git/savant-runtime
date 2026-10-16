from __future__ import annotations

from importlib import import_module
from types import MappingProxyType
from typing import Any, Mapping


schema = (
    "savant://runtime/exiles/"
    "composition/1.0.0"
)

owner = "exile:segue"
authority_effect = "none"

verified_binding_modules = MappingProxyType(
    {
        "envoy": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.envoy.runtime.exile_flow_binding"
        ),
        "niche": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.niche.runtime.exile_flow_binding"
        ),
        "opus": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.opus.runtime.exile_flow_binding"
        ),
        "palaver": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.palaver.runtime.exile_flow_binding"
        ),
        "underscore": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.underscore.runtime.exile_flow_binding"
        ),
        "urge": (
            "ontology.obelisks._template.segue.gates."
            "_template.segue.innates._template.segue."
            "exiles.urge.runtime.exile_flow_binding"
        ),
    }
)


class exile_composition_error(
    RuntimeError
):
    pass


def _binding(
    exile: str,
) -> Any:
    normalized = str(
        exile
    ).strip().lower()

    module_name = (
        verified_binding_modules.get(
            normalized
        )
    )

    if module_name is None:
        raise exile_composition_error(
            "unverified exile binding: "
            + normalized
        )

    return import_module(
        module_name
    )


def preparation(
    exile: str,
) -> dict[str, Any]:
    module = _binding(
        exile
    )

    projector = getattr(
        module,
        "preparation",
        None,
    )

    if not callable(
        projector
    ):
        raise exile_composition_error(
            "binding does not expose preparation: "
            + str(
                exile
            )
        )

    projected = projector()

    if not isinstance(
        projected,
        Mapping,
    ):
        raise exile_composition_error(
            "binding preparation must be a mapping: "
            + str(
                exile
            )
        )

    return dict(
        projected
    )


def binding_status(
    exile: str,
) -> dict[str, Any]:
    module = _binding(
        exile
    )

    projector = getattr(
        module,
        "status",
        None,
    )

    if not callable(
        projector
    ):
        raise exile_composition_error(
            "binding does not expose status: "
            + str(
                exile
            )
        )

    projected = projector()

    if not isinstance(
        projected,
        Mapping,
    ):
        raise exile_composition_error(
            "binding status must be a mapping: "
            + str(
                exile
            )
        )

    return dict(
        projected
    )


def compose() -> dict[str, Any]:
    exiles: dict[
        str,
        dict[str, Any],
    ] = {}

    for exile in sorted(
        verified_binding_modules
    ):
        prepared = preparation(
            exile
        )

        status = binding_status(
            exile
        )

        exiles[
            exile
        ] = {
            "preparation":
                prepared,
            "status":
                status,
        }

    return {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "creates_authority":
            False,
        "changes_exile_ownership":
            False,
        "fabricates_exile_behavior":
            False,
        "binding_count":
            len(
                exiles
            ),
        "bindings":
            exiles,
    }


def projection() -> dict[str, Any]:
    composed = compose()

    bindings = composed[
        "bindings"
    ]

    return {
        "schema":
            schema,
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "creates_authority":
            False,
        "changes_exile_ownership":
            False,
        "fabricates_exile_behavior":
            False,
        "verified_exiles":
            sorted(
                bindings
            ),
        "binding_count":
            len(
                bindings
            ),
        "binding_schemas": {
            exile:
                bindings[
                    exile
                ][
                    "status"
                ].get(
                    "schema"
                )
            for exile in sorted(
                bindings
            )
        },
    }


def selftest() -> dict[str, Any]:
    composed = compose()
    projected = projection()

    bindings = composed[
        "bindings"
    ]

    expected = (
        "envoy",
        "niche",
        "opus",
        "palaver",
        "underscore",
        "urge",
    )

    prepared_owners = {
        exile:
            bindings[
                exile
            ][
                "preparation"
            ].get(
                "exile"
            )
        for exile in expected
    }

    checks = {
        "six_verified_bindings":
            tuple(
                sorted(
                    bindings
                )
            )
            == expected,
        "binding_count_exact":
            projected[
                "binding_count"
            ]
            == 6,
        "envoy_owner_preserved":
            prepared_owners[
                "envoy"
            ]
            == "exile:envoy",
        "niche_owner_preserved":
            prepared_owners[
                "niche"
            ]
            == "exile:niche",
        "opus_owner_preserved":
            prepared_owners[
                "opus"
            ]
            == "exile:opus",
        "palaver_owner_preserved":
            prepared_owners[
                "palaver"
            ]
            == "exile:palaver",
        "underscore_owner_preserved":
            prepared_owners[
                "underscore"
            ]
            == "exile:underscore",
        "urge_owner_preserved":
            prepared_owners[
                "urge"
            ]
            == "exile:urge",
        "composition_owner_is_segue":
            projected[
                "owner"
            ]
            == "exile:segue",
        "authority_effect_none":
            projected[
                "authority_effect"
            ]
            == "none",
        "creates_no_authority":
            projected[
                "creates_authority"
            ]
            is False,
        "changes_no_exile_ownership":
            projected[
                "changes_exile_ownership"
            ]
            is False,
        "fabricates_no_exile_behavior":
            projected[
                "fabricates_exile_behavior"
            ]
            is False,
        "all_binding_schemas_present":
            all(
                bool(
                    projected[
                        "binding_schemas"
                    ].get(
                        exile
                    )
                )
                for exile in expected
            ),
    }

    unverified_rejected = False

    try:
        preparation(
            "carbon"
        )
    except exile_composition_error:
        unverified_rejected = True

    checks[
        "unverified_binding_rejected"
    ] = unverified_rejected

    return {
        "schema":
            (
                "savant://runtime/exiles/"
                "composition-selftest/1.0.0"
            ),
        "composition_schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "verified_exiles":
            list(
                expected
            ),
    }


__all__ = [
    "authority_effect",
    "binding_status",
    "compose",
    "exile_composition_error",
    "owner",
    "preparation",
    "projection",
    "schema",
    "selftest",
    "verified_binding_modules",
]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
