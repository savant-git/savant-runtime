#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path
from typing import Any, Mapping, Sequence

from oriel_capabilities import (
    collect as collect_capabilities,
)

from oriel_capabilities import (
    projection_packet as capability_projection_packet,
)

from oriel_introspection import (
    snapshot as introspection_snapshot,
)


owner = "carbon"
component = "oriel-composition"
authority_effect = "none"
schema = "savant.carbon.oriel-composition.v1"

carbon_root = (
    Path(
        __file__
    ).resolve().parent.parent
)


class oriel_composition_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + digest(
            value
        )[:24]
    )


def load_json(
    relative_path: str,
) -> dict[str, Any]:
    path = (
        carbon_root
        / relative_path
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_composition_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_composition_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_composition_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def export_catalog() -> dict[str, Any]:
    return load_json(
        "composition/exports.json"
    )


def import_catalog() -> dict[str, Any]:
    return load_json(
        "composition/imports.json"
    )


def specialization_reference(
) -> dict[str, Any]:
    manifest = load_json(
        "registry/manifests/oriel.json"
    )

    capabilities = load_json(
        "registry/capabilities/oriel.json"
    )

    surface = collect_capabilities()

    health = introspection_snapshot()

    result = {
        "schema":
            schema,

        "kind":
            "specialization-reference",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "specialization":
            "oriel",

        "manifest_id":
            manifest.get(
                "id"
            ),

        "manifest":
            "registry/manifests/oriel.json",

        "capability_descriptor_id":
            capabilities.get(
                "id"
            ),

        "capability_descriptor":
            "registry/capabilities/oriel.json",

        "capability_surface_id":
            surface.get(
                "id"
            ),

        "capability_provider":
            "runtime/oriel_capabilities.py",

        "capability_count":
            surface.get(
                "capability_count",
                0,
            ),

        "health_state":
            health.get(
                "oriel_state"
            ),

        "simulation_owner":
            "carbon",

        "projection_owner":
            "filament",

        "transformation_owner":
            "modus",

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,
    }

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def export_packet(
    *,
    target_exile: str,
    mask: Mapping[
        str,
        Any,
    ]
    | None = None,
    include_dependencies:
        bool = True,
) -> dict[str, Any]:
    target = str(
        target_exile
    ).strip().lower()

    if not target:
        raise oriel_composition_error(
            "target_exile is required"
        )

    catalog = export_catalog()

    export_ids = {
        str(
            value.get(
                "id",
                "",
            )
        )
        for value
        in catalog.get(
            "exports",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    required_exports = {
        "oriel_specialization",
        "oriel_capability_surface",
    }

    if not required_exports.issubset(
        export_ids
    ):
        raise oriel_composition_error(
            (
                "carbon composition exports "
                "do not expose oriel"
            )
        )

    surface = collect_capabilities()

    capability_packet = (
        capability_projection_packet(
            surface,
            target_exile=
                target,
            mask=
                mask,
            include_dependencies=
                include_dependencies,
        )
    )

    reference = (
        specialization_reference()
    )

    result = {
        "schema":
            schema,

        "kind":
            "oriel-composition-export",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "source_exile":
            "carbon",

        "source_component":
            "oriel",

        "target_exile":
            target,

        "specialization":
            reference,

        "capability_projection":
            capability_packet,

        "projection_owner":
            "filament",

        "transformation_owner":
            "modus",

        "apply_projection":
            False,

        "composition_mode":
            "reference",

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,
    }

    result[
        "id"
    ] = stable_id(
        (
            "carbon-oriel-"
            "composition-export"
        ),
        {
            "target_exile":
                target,

            "specialization_digest":
                reference[
                    "digest"
                ],

            "capability_projection_id":
                capability_packet.get(
                    "id"
                ),
        },
    )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def import_reference(
    *,
    import_id: str,
    references: Sequence[str],
) -> dict[str, Any]:
    identifier = str(
        import_id
    ).strip().lower()

    catalog = import_catalog()

    index = {
        str(
            value.get(
                "id",
                "",
            )
        ):
            value
        for value
        in catalog.get(
            "imports",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    if identifier not in index:
        raise oriel_composition_error(
            (
                "unsupported carbon import: "
                + identifier
            )
        )

    normalized = sorted(
        {
            str(
                value
            ).strip()
            for value
            in references
            if str(
                value
            ).strip()
        }
    )

    if not normalized:
        raise oriel_composition_error(
            (
                "at least one reference "
                "is required"
            )
        )

    contract = index[
        identifier
    ]

    result = {
        "schema":
            schema,

        "kind":
            (
                "oriel-composition-"
                "import-reference"
            ),

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "import_id":
            identifier,

        "import_kind":
            contract.get(
                "kind"
            ),

        "purpose":
            contract.get(
                "purpose"
            ),

        "references":
            normalized,

        "binding":
            "reference",

        "imported_authority_inherited":
            False,

        "imported_authority_mutable":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "apply_import":
            False,
    }

    result[
        "id"
    ] = stable_id(
        (
            "carbon-oriel-"
            "composition-import"
        ),
        {
            "import_id":
                identifier,

            "references":
                normalized,
        },
    )

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def profile() -> dict[str, Any]:
    exports = export_catalog()
    imports = import_catalog()

    reference = (
        specialization_reference()
    )

    result = {
        "schema":
            schema,

        "kind":
            "composition-profile",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "exports_id":
            exports.get(
                "id"
            ),

        "imports_id":
            imports.get(
                "id"
            ),

        "specialization":
            reference,

        "export_ids":
            sorted(
                str(
                    value.get(
                        "id",
                        "",
                    )
                )
                for value
                in exports.get(
                    "exports",
                    [],
                )
                if isinstance(
                    value,
                    Mapping,
                )
            ),

        "import_ids":
            sorted(
                str(
                    value.get(
                        "id",
                        "",
                    )
                )
                for value
                in imports.get(
                    "imports",
                    [],
                )
                if isinstance(
                    value,
                    Mapping,
                )
            ),

        "composition_mode":
            "reference",

        "projection_owner":
            "filament",

        "transformation_owner":
            "modus",

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,
    }

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    value = profile()

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "specialization":
            "oriel",

        "health_state":
            value[
                "specialization"
            ].get(
                "health_state"
            ),

        "export_count":
            len(
                value[
                    "export_ids"
                ]
            ),

        "import_count":
            len(
                value[
                    "import_ids"
                ]
            ),

        "reference_only":
            True,

        "authority_transfer":
            False,

        "ready":
            (
                value[
                    "specialization"
                ].get(
                    "health_state"
                )
                != "blocked"
            ),
    }


def selftest() -> dict[str, Any]:
    value = profile()

    if (
        "oriel_specialization"
        not in value[
            "export_ids"
        ]
    ):
        raise oriel_composition_error(
            (
                "oriel specialization "
                "export is missing"
            )
        )

    if (
        "oriel_capability_surface"
        not in value[
            "export_ids"
        ]
    ):
        raise oriel_composition_error(
            (
                "oriel capability surface "
                "export is missing"
            )
        )

    if (
        "external_historical_reality"
        not in value[
            "import_ids"
        ]
    ):
        raise oriel_composition_error(
            (
                "external historical reality "
                "import is missing"
            )
        )

    packet = export_packet(
        target_exile=
            "palaver",
        mask={
            "allow_ids": []
        },
        include_dependencies=
            True,
    )

    if (
        packet[
            "authority_transfer"
        ]
        or packet[
            "ownership_transfer"
        ]
    ):
        raise oriel_composition_error(
            (
                "composition packet "
                "transferred authority "
                "or ownership"
            )
        )

    imported = import_reference(
        import_id=
            "external_historical_reality",
        references=[
            "source:test"
        ],
    )

    if (
        imported[
            "imported_authority_inherited"
        ]
        or imported[
            "imported_authority_mutable"
        ]
    ):
        raise oriel_composition_error(
            (
                "import reference changed "
                "external authority semantics"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "oriel_specialization_exported":
            True,

        "oriel_capability_surface_exported":
            True,

        (
            "external_historical_reality_"
            "imported_by_reference"
        ):
            True,

        "projection_owner":
            "filament",

        "transformation_owner":
            "modus",

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "export_catalog",
    "export_packet",
    "import_catalog",
    "import_reference",
    "profile",
    "selftest",
    "specialization_reference",
    "status",
]
