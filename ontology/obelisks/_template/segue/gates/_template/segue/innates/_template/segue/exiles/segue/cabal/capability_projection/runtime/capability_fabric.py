#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


try:
    import networkx as nx

except ImportError:
    nx = None


savant_root = Path(
    "/root/savant-runtime"
).resolve()

exiles_root = (
    savant_root
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
)

manifest_relative_path = (
    Path(
        "interface"
    )
    / "capabilities"
    / "capabilities.json"
)

schema = (
    "savant.exile-capability-fabric.v1"
)

owner = "exile-cabal"

projection_owner = "filament"

transformation_owner = "modus"

authority_effect = "none"

accepted_exiles = (
    "carbon",
    "cataxis",
    "coda",
    "envoy",
    "filament",
    "graffiti",
    "lore",
    "mobius",
    "modus",
    "niche",
    "notary",
    "opus",
    "pact",
    "palaver",
    "shatter",
    "underscore",
    "urge",
    "zero",
)

projection_modes = {
    "reference",
    "instance",
    "composition",
}

protected_capability_fields = {
    "capability_ref",
    "source_id",
    "owner",
    "source_owner",
    "source_manifest",
    "source_manifest_digest",
    "authority_effect",
    "execution_owner",
    "version",
    "schema_version",
    "lineage",
    "provenance",
}

dangerous_effects = {
    "filesystem_read",
    "filesystem_write",
    "filesystem_mutation",
    "subprocess_execution",
    "network_access",
    "provider_access",
    "secret_access",
    "authority_mutation",
    "evidence_admission",
    "task_transition",
}

implemented_enhancements = (
    "universal capability metadata normalization",
    "stable capability references",
    "source-manifest digest binding",
    "content-addressed projection identity",
    "owner-preserving capability projection",
    "reference projection",
    "instance projection",
    "composition projection contract",
    "modus-owned masking boundary",
    "mask monotonicity",
    "operation narrowing",
    "parameter defaults and overlays",
    "parameter-contract validation",
    "destination allow and deny selectors",
    "capability dependency graph",
    "dependency closure",
    "cycle classification",
    "deterministic topological ordering",
    "networkx acceleration with stdlib fallback",
    "projection receipts",
    "lineage preservation",
    "provenance preservation",
    "authority-effect preservation",
    "privileged-effect detection",
    "fail-closed unknown handling",
    "capability negotiation",
    "effective capability arrays",
    "native ingress egress symmetry",
    "pairwise exile capability matrix",
    "semantic collision detection",
    "duplicate projection coalescence",
    "projection compatibility evaluation",
    "version requirement evaluation",
    "required-operation evaluation",
    "deterministic canonical serialization",
    "runtime-only non-authoritative composition",
    "historical manifest compatibility",
    "unresolved-manifest reporting",
    "projection dry-run semantics",
    "bounded execution dispatch planning",
)


class capability_fabric_error(
    RuntimeError
):
    pass


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
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
    )


def digest(
    value: Any,
) -> str:
    if isinstance(
        value,
        bytes,
    ):
        raw = value

    elif isinstance(
        value,
        str,
    ):
        raw = value.encode(
            "utf-8"
        )

    else:
        raw = canonical_json(
            value
        ).encode(
            "utf-8"
        )

    return hashlib.sha256(
        raw
    ).hexdigest()


def normalized_strings(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [
            value
        ]

    if not isinstance(
        value,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return []

    return sorted(
        {
            str(
                item
            ).strip()
            for item
            in value
            if str(
                item
            ).strip()
        }
    )


def manifest_path(
    exile: str,
) -> Path:
    exile_id = str(
        exile
    ).strip().lower()

    if exile_id not in accepted_exiles:
        raise capability_fabric_error(
            (
                "unknown accepted exile: "
                + exile_id
            )
        )

    return (
        exiles_root
        / exile_id
        / manifest_relative_path
    )


def read_manifest(
    exile: str,
) -> dict[str, Any]:
    path = manifest_path(
        exile
    )

    if not path.is_file():
        return {
            "schema":
                (
                    "savant.exile-capability-"
                    "manifest-source.v1"
                ),

            "owner":
                exile,

            "status":
                "unresolved",

            "manifest_present":
                False,

            "path":
                str(
                    path
                ),

            "manifest_digest":
                None,

            "capabilities":
                [],
        }

    raw = path.read_bytes()

    try:
        document = json.loads(
            raw.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise capability_fabric_error(
            (
                "invalid capability manifest: "
                + str(
                    path
                )
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        document,
        dict,
    ):
        raise capability_fabric_error(
            (
                "capability manifest must "
                "be an object: "
                + str(
                    path
                )
            )
        )

    capabilities = document.get(
        "capabilities",
        []
    )

    if capabilities is None:
        capabilities = []

    if not isinstance(
        capabilities,
        list,
    ):
        raise capability_fabric_error(
            (
                "manifest capabilities must "
                "be a list: "
                + str(
                    path
                )
            )
        )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "manifest-source.v1"
            ),

        "owner":
            exile,

        "status":
            str(
                document.get(
                    "status",
                    "unknown",
                )
            ),

        "manifest_present":
            True,

        "path":
            str(
                path
            ),

        "manifest_digest":
            digest(
                raw
            ),

        "document":
            document,

        "capabilities":
            capabilities,
    }


def infer_privileged_effects(
    capability: Mapping[str, Any],
) -> list[str]:
    discovered = set()

    values = [
        capability.get(
            "id"
        ),
        capability.get(
            "purpose"
        ),
        capability.get(
            "description"
        ),
        capability.get(
            "mutation_effect"
        ),
        capability.get(
            "authority_effect"
        ),
        capability.get(
            "operation"
        ),
    ]

    haystack = " ".join(
        str(
            value
            or ""
        ).lower()
        for value
        in values
    )

    for effect in dangerous_effects:
        fragments = {
            effect,
            effect.replace(
                "_",
                " ",
            ),
        }

        if any(
            fragment
            in haystack
            for fragment
            in fragments
        ):
            discovered.add(
                effect
            )

    if (
        capability.get(
            "mutation_effect"
        )
        not in {
            None,
            "",
            "none",
            "runtime_state",
        }
    ):
        discovered.add(
            "durable_or_delegated_mutation"
        )

    if (
        capability.get(
            "authority_effect"
        )
        not in {
            None,
            "",
            "none",
        }
    ):
        discovered.add(
            "authority_effect"
        )

    return sorted(
        discovered
    )


def projection_contract(
    capability: Mapping[str, Any],
) -> dict[str, Any]:
    supplied = capability.get(
        "projection"
    )

    if isinstance(
        supplied,
        Mapping,
    ):
        modes = normalized_strings(
            supplied.get(
                "modes"
            )
        )

        if not modes:
            modes = [
                "reference"
            ]

        modes = [
            mode
            for mode
            in modes
            if mode
            in projection_modes
        ]

        allowed_consumers = normalized_strings(
            supplied.get(
                "allowed_consumers"
            )
        )

        denied_consumers = normalized_strings(
            supplied.get(
                "denied_consumers"
            )
        )

        instanceable = bool(
            supplied.get(
                "instanceable",
                (
                    "instance"
                    in modes
                ),
            )
        )

        composable = bool(
            supplied.get(
                "composable",
                (
                    "composition"
                    in modes
                ),
            )
        )

    else:
        modes = [
            "reference"
        ]

        allowed_consumers = []

        denied_consumers = []

        instanceable = False

        composable = False

    return {
        "modes":
            sorted(
                set(
                    modes
                )
            ),

        "allowed_consumers":
            allowed_consumers,

        "denied_consumers":
            denied_consumers,

        "instanceable":
            instanceable,

        "composable":
            composable,

        "maskable":
            True,

        "ownership_transfer":
            False,

        "authority_transfer":
            False,
    }


def normalize_capability(
    *,
    exile: str,
    capability: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    source_id = str(
        capability.get(
            "id",
            "",
        )
    ).strip()

    if not source_id:
        raise capability_fabric_error(
            (
                "capability without id in "
                + exile
            )
        )

    declared_owner = str(
        capability.get(
            "owner",
            exile,
        )
    ).strip().lower()

    owner_conflict = (
        declared_owner
        != exile
    )

    capability_ref = (
        "exile:"
        + exile
        + "/capability:"
        + source_id
    )

    operations = normalized_strings(
        capability.get(
            "operations"
        )
    )

    operation = capability.get(
        "operation"
    )

    if operation:
        operations = sorted(
            {
                *operations,
                str(
                    operation
                ).strip(),
            }
        )

    description = (
        capability.get(
            "purpose"
        )
        or capability.get(
            "description"
        )
    )

    kind = str(
        capability.get(
            "kind",
            capability.get(
                "group",
                "unspecified",
            ),
        )
    ).strip()

    status = str(
        capability.get(
            "status",
            manifest.get(
                "status",
                "unknown",
            ),
        )
    ).strip()

    execution_owner = str(
        capability.get(
            "execution_owner",
            declared_owner,
        )
    ).strip().lower()

    authority_value = str(
        capability.get(
            "authority_effect",
            (
                manifest.get(
                    "document",
                    {}
                ).get(
                    "authority_effect",
                    "none",
                )
                if isinstance(
                    manifest.get(
                        "document"
                    ),
                    Mapping,
                )
                else "none"
            ),
        )
    ).strip()

    parameter_contract = capability.get(
        "parameters"
    )

    if not isinstance(
        parameter_contract,
        Mapping,
    ):
        parameter_contract = {}

    dependencies = normalized_strings(
        capability.get(
            "dependencies"
        )
    )

    conflicts = normalized_strings(
        capability.get(
            "conflicts"
        )
    )

    tags = normalized_strings(
        capability.get(
            "tags"
        )
    )

    labels = normalized_strings(
        capability.get(
            "labels"
        )
    )

    capability_projection = projection_contract(
        capability
    )

    normalized = {
        "schema":
            (
                "savant.exile-capability.v1"
            ),

        "schema_version":
            "1.0.0",

        "capability_ref":
            capability_ref,

        "source_id":
            source_id,

        "name":
            str(
                capability.get(
                    "name",
                    source_id,
                )
            ).strip(),

        "owner":
            declared_owner,

        "source_owner":
            exile,

        "owner_conflict":
            owner_conflict,

        "status":
            status,

        "kind":
            kind,

        "purpose":
            (
                str(
                    description
                ).strip()
                if description
                is not None
                else None
            ),

        "version":
            str(
                capability.get(
                    "version",
                    "unversioned",
                )
            ),

        "authority_effect":
            authority_value,

        "mutation_effect":
            capability.get(
                "mutation_effect"
            ),

        "execution_owner":
            execution_owner,

        "projection_owner":
            projection_owner,

        "transformation_owner":
            transformation_owner,

        "operations":
            operations,

        "inputs":
            copy.deepcopy(
                capability.get(
                    "inputs",
                    [],
                )
            ),

        "outputs":
            copy.deepcopy(
                capability.get(
                    "outputs",
                    [],
                )
            ),

        "parameters":
            copy.deepcopy(
                parameter_contract
            ),

        "dependencies":
            dependencies,

        "conflicts":
            conflicts,

        "requirements":
            copy.deepcopy(
                capability.get(
                    "requirements",
                    {}
                )
            ),

        "permissions":
            copy.deepcopy(
                capability.get(
                    "permissions",
                    {}
                )
            ),

        "side_effects":
            normalized_strings(
                capability.get(
                    "side_effects"
                )
            ),

        "privileged_effects":
            infer_privileged_effects(
                capability
            ),

        "deterministic":
            capability.get(
                "deterministic"
            ),

        "idempotent":
            capability.get(
                "idempotent"
            ),

        "reversible":
            capability.get(
                "reversible"
            ),

        "stateful":
            capability.get(
                "stateful"
            ),

        "streaming":
            capability.get(
                "streaming"
            ),

        "async_capable":
            capability.get(
                "async_capable"
            ),

        "security_class":
            capability.get(
                "security_class",
                "unspecified",
            ),

        "data_class":
            capability.get(
                "data_class",
                "unspecified",
            ),

        "resource_class":
            capability.get(
                "resource_class",
                "unspecified",
            ),

        "latency_class":
            capability.get(
                "latency_class",
                "unspecified",
            ),

        "evidence_requirements":
            copy.deepcopy(
                capability.get(
                    "evidence_requirements",
                    [],
                )
            ),

        "compatibility":
            copy.deepcopy(
                capability.get(
                    "compatibility",
                    {}
                )
            ),

        "projection":
            capability_projection,

        "moods":
            normalized_strings(
                capability.get(
                    "moods"
                )
            ),

        "slots":
            normalized_strings(
                capability.get(
                    "slots"
                )
            ),

        "tags":
            tags,

        "labels":
            labels,

        "lineage": {
            "source_capability_ref":
                capability_ref,

            "source_manifest":
                manifest.get(
                    "path"
                ),

            "source_manifest_digest":
                manifest.get(
                    "manifest_digest"
                ),
        },

        "provenance": {
            "source":
                manifest.get(
                    "path"
                ),

            "source_digest":
                manifest.get(
                    "manifest_digest"
                ),

            "source_class":
                "implementation_projection",

            "authority_effect":
                "none",
        },

        "source_manifest":
            manifest.get(
                "path"
            ),

        "source_manifest_digest":
            manifest.get(
                "manifest_digest"
            ),

        "projection_only":
            True,

        "authoritative":
            False,
    }

    normalized[
        "capability_digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in normalized.items()
            if key
            != "capability_digest"
        }
    )

    return normalized


def capabilities_for(
    exile: str,
) -> list[dict[str, Any]]:
    manifest = read_manifest(
        exile
    )

    normalized = []

    for capability in manifest.get(
        "capabilities",
        []
    ):
        if not isinstance(
            capability,
            Mapping,
        ):
            continue

        normalized.append(
            normalize_capability(
                exile=exile,
                capability=capability,
                manifest=manifest,
            )
        )

    return sorted(
        normalized,
        key=lambda item: (
            str(
                item[
                    "owner"
                ]
            ),
            str(
                item[
                    "source_id"
                ]
            ),
        ),
    )


def all_capabilities() -> list[
    dict[
        str,
        Any,
    ]
]:
    output = []

    for exile in accepted_exiles:
        output.extend(
            capabilities_for(
                exile
            )
        )

    return sorted(
        output,
        key=lambda item: (
            str(
                item[
                    "source_owner"
                ]
            ),
            str(
                item[
                    "source_id"
                ]
            ),
        ),
    )


def capability_index() -> dict[
    str,
    dict[
        str,
        Any,
    ],
]:
    index = {}

    for capability in all_capabilities():
        reference = str(
            capability[
                "capability_ref"
            ]
        )

        index[
            reference
        ] = capability

        source_owner = str(
            capability[
                "source_owner"
            ]
        )

        source_id = str(
            capability[
                "source_id"
            ]
        )

        index[
            (
                source_owner
                + ":"
                + source_id
            )
        ] = capability

    return index


def resolve_capability(
    *,
    source_exile: str,
    capability_id: str,
) -> dict[str, Any]:
    source = str(
        source_exile
    ).strip().lower()

    identifier = str(
        capability_id
    ).strip()

    candidates = capabilities_for(
        source
    )

    for capability in candidates:
        if identifier in {
            capability[
                "source_id"
            ],
            capability[
                "capability_ref"
            ],
        }:
            return capability

    raise capability_fabric_error(
        (
            "capability not found: "
            + source
            + ":"
            + identifier
        )
    )


def version_satisfies(
    actual: str,
    required: str | None,
) -> bool | None:
    if required is None:
        return True

    required_value = str(
        required
    ).strip()

    if not required_value:
        return True

    actual_value = str(
        actual
    ).strip()

    if actual_value == "unversioned":
        return None

    if required_value.startswith(
        "=="
    ):
        return (
            actual_value
            == required_value[
                2:
            ].strip()
        )

    return (
        actual_value
        == required_value
    )


def validate_parameter_type(
    value: Any,
    expected: str,
) -> bool:
    type_map = {
        "string":
            str,

        "integer":
            int,

        "number":
            (
                int,
                float,
            ),

        "boolean":
            bool,

        "object":
            dict,

        "array":
            list,

        "null":
            type(
                None
            ),
    }

    expected_type = type_map.get(
        str(
            expected
        ).strip().lower()
    )

    if expected_type is None:
        return False

    if (
        expected
        == "integer"
        and isinstance(
            value,
            bool,
        )
    ):
        return False

    if (
        expected
        == "number"
        and isinstance(
            value,
            bool,
        )
    ):
        return False

    return isinstance(
        value,
        expected_type,
    )


def apply_parameter_contract(
    capability: Mapping[str, Any],
    supplied: Mapping[str, Any] | None,
) -> dict[str, Any]:
    contract = capability.get(
        "parameters"
    )

    if not isinstance(
        contract,
        Mapping,
    ):
        contract = {}

    supplied_values = dict(
        supplied
        or {}
    )

    defaults = contract.get(
        "defaults",
        {}
    )

    if not isinstance(
        defaults,
        Mapping,
    ):
        defaults = {}

    effective = {
        **defaults,
        **supplied_values,
    }

    required = normalized_strings(
        contract.get(
            "required"
        )
    )

    allowed = normalized_strings(
        contract.get(
            "allowed"
        )
    )

    types = contract.get(
        "types",
        {}
    )

    if not isinstance(
        types,
        Mapping,
    ):
        types = {}

    missing = [
        key
        for key
        in required
        if key not in effective
    ]

    unexpected = (
        sorted(
            set(
                effective
            )
            - set(
                allowed
            )
        )
        if allowed
        else []
    )

    type_failures = []

    for key, expected in types.items():
        if key not in effective:
            continue

        if not validate_parameter_type(
            effective[
                key
            ],
            str(
                expected
            ),
        ):
            type_failures.append(
                {
                    "parameter":
                        key,

                    "expected":
                        expected,

                    "actual_type":
                        type(
                            effective[
                                key
                            ]
                        ).__name__,
                }
            )

    return {
        "valid":
            (
                not missing
                and not unexpected
                and not type_failures
            ),

        "effective":
            effective,

        "missing":
            missing,

        "unexpected":
            unexpected,

        "type_failures":
            type_failures,
    }


def normalize_mask(
    mask: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if mask is None:
        return None

    if not isinstance(
        mask,
        Mapping,
    ):
        raise capability_fabric_error(
            "mask must be an object"
        )

    mask_owner = str(
        mask.get(
            "owner",
            "",
        )
    ).strip().lower()

    if mask_owner != transformation_owner:
        raise capability_fabric_error(
            (
                "capability masks must be "
                "owned by modus"
            )
        )

    mood_id = str(
        mask.get(
            "mood_id",
            mask.get(
                "id",
                "",
            ),
        )
    ).strip()

    if not mood_id:
        raise capability_fabric_error(
            (
                "modus mask requires "
                "mood_id"
            )
        )

    overlays = mask.get(
        "metadata_overlay",
        {}
    )

    if not isinstance(
        overlays,
        Mapping,
    ):
        raise capability_fabric_error(
            (
                "metadata_overlay must "
                "be an object"
            )
        )

    forbidden_overlay = sorted(
        set(
            overlays
        )
        & protected_capability_fields
    )

    if forbidden_overlay:
        raise capability_fabric_error(
            (
                "modus mask may not alter "
                "protected capability fields: "
                + ", ".join(
                    forbidden_overlay
                )
            )
        )

    return {
        "owner":
            transformation_owner,

        "mood_id":
            mood_id,

        "enabled":
            bool(
                mask.get(
                    "enabled",
                    True,
                )
            ),

        "allow_operations":
            normalized_strings(
                mask.get(
                    "allow_operations"
                )
            ),

        "deny_operations":
            normalized_strings(
                mask.get(
                    "deny_operations"
                )
            ),

        "parameter_defaults":
            copy.deepcopy(
                mask.get(
                    "parameter_defaults",
                    {},
                )
            ),

        "metadata_overlay":
            copy.deepcopy(
                overlays
            ),

        "restrictions":
            copy.deepcopy(
                mask.get(
                    "restrictions",
                    {},
                )
            ),

        "authority_effect":
            "none",
    }


def apply_mask(
    capability: Mapping[str, Any],
    mask: Mapping[str, Any] | None,
) -> dict[str, Any]:
    effective = copy.deepcopy(
        dict(
            capability
        )
    )

    normalized = normalize_mask(
        mask
    )

    if normalized is None:
        return {
            "valid":
                True,

            "effective_capability":
                effective,

            "mask":
                None,

            "violations":
                [],
        }

    if not normalized[
        "enabled"
    ]:
        return {
            "valid":
                False,

            "effective_capability":
                effective,

            "mask":
                normalized,

            "violations": [
                "modus mask disabled capability"
            ],
        }

    original_operations = set(
        normalized_strings(
            capability.get(
                "operations"
            )
        )
    )

    allow_operations = set(
        normalized[
            "allow_operations"
        ]
    )

    deny_operations = set(
        normalized[
            "deny_operations"
        ]
    )

    if allow_operations:
        illegal_expansion = (
            allow_operations
            - original_operations
        )

        if illegal_expansion:
            return {
                "valid":
                    False,

                "effective_capability":
                    effective,

                "mask":
                    normalized,

                "violations": [
                    (
                        "modus mask attempted "
                        "operation expansion: "
                        + ", ".join(
                            sorted(
                                illegal_expansion
                            )
                        )
                    )
                ],
            }

        operations = (
            original_operations
            & allow_operations
        )

    else:
        operations = set(
            original_operations
        )

    operations -= deny_operations

    effective[
        "operations"
    ] = sorted(
        operations
    )

    metadata_overlay = normalized[
        "metadata_overlay"
    ]

    for key, value in metadata_overlay.items():
        effective[
            key
        ] = copy.deepcopy(
            value
        )

    parameter_defaults = normalized[
        "parameter_defaults"
    ]

    existing_parameters = effective.get(
        "parameters"
    )

    if not isinstance(
        existing_parameters,
        Mapping,
    ):
        existing_parameters = {}

    existing_defaults = existing_parameters.get(
        "defaults",
        {}
    )

    if not isinstance(
        existing_defaults,
        Mapping,
    ):
        existing_defaults = {}

    effective[
        "parameters"
    ] = {
        **existing_parameters,

        "defaults": {
            **existing_defaults,
            **parameter_defaults,
        },
    }

    effective[
        "active_modus_mask"
    ] = normalized

    effective[
        "source_capability_digest"
    ] = capability.get(
        "capability_digest"
    )

    effective[
        "effective_capability_digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in effective.items()
            if key
            != "effective_capability_digest"
        }
    )

    return {
        "valid":
            True,

        "effective_capability":
            effective,

        "mask":
            normalized,

        "violations":
            [],
    }


def projection_compatibility(
    capability: Mapping[str, Any],
    *,
    destination_exile: str,
    mode: str,
    required_operations:
        Sequence[str]
        | None = None,
    required_version:
        str
        | None = None,
) -> dict[str, Any]:
    destination = str(
        destination_exile
    ).strip().lower()

    if destination not in accepted_exiles:
        return {
            "compatible":
                False,

            "state":
                "fail",

            "reasons": [
                "destination is not an accepted exile"
            ],
        }

    projection = capability.get(
        "projection"
    )

    if not isinstance(
        projection,
        Mapping,
    ):
        projection = {}

    allowed_modes = set(
        normalized_strings(
            projection.get(
                "modes"
            )
        )
    )

    reasons = []

    unknowns = []

    if mode not in projection_modes:
        reasons.append(
            "unknown projection mode"
        )

    elif mode not in allowed_modes:
        reasons.append(
            (
                "projection mode is not "
                "declared by source capability"
            )
        )

    allowed_consumers = set(
        normalized_strings(
            projection.get(
                "allowed_consumers"
            )
        )
    )

    denied_consumers = set(
        normalized_strings(
            projection.get(
                "denied_consumers"
            )
        )
    )

    if (
        destination
        in denied_consumers
    ):
        reasons.append(
            "destination is explicitly denied"
        )

    if (
        allowed_consumers
        and destination
        not in allowed_consumers
    ):
        reasons.append(
            (
                "destination is not in "
                "allowed consumer set"
            )
        )

    if (
        mode == "instance"
        and not projection.get(
            "instanceable",
            False,
        )
    ):
        reasons.append(
            "capability is not declared instanceable"
        )

    if (
        mode == "composition"
        and not projection.get(
            "composable",
            False,
        )
    ):
        reasons.append(
            "capability is not declared composable"
        )

    version_result = version_satisfies(
        str(
            capability.get(
                "version",
                "unversioned",
            )
        ),
        required_version,
    )

    if version_result is False:
        reasons.append(
            "version requirement failed"
        )

    elif version_result is None:
        unknowns.append(
            (
                "source capability is "
                "unversioned"
            )
        )

    required = set(
        normalized_strings(
            required_operations
        )
    )

    available = set(
        normalized_strings(
            capability.get(
                "operations"
            )
        )
    )

    missing_operations = sorted(
        required
        - available
    )

    if missing_operations:
        reasons.append(
            (
                "required operations unavailable: "
                + ", ".join(
                    missing_operations
                )
            )
        )

    if capability.get(
        "owner_conflict"
    ):
        reasons.append(
            (
                "source capability owner conflicts "
                "with source exile"
            )
        )

    status = str(
        capability.get(
            "status",
            "unknown",
        )
    ).strip().lower()

    if status in {
        "stub",
        "unresolved",
        "disabled",
        "retired",
        "inactive",
    }:
        reasons.append(
            (
                "source capability status "
                "is not runtime-eligible"
            )
        )

    if reasons:
        state = "fail"
        compatible = False

    elif unknowns:
        state = "unknown"
        compatible = False

    else:
        state = "pass"
        compatible = True

    return {
        "compatible":
            compatible,

        "state":
            state,

        "reasons":
            reasons,

        "unknowns":
            unknowns,

        "required_operations":
            sorted(
                required
            ),

        "missing_operations":
            missing_operations,

        "required_version":
            required_version,

        "source_version":
            capability.get(
                "version"
            ),
    }


def create_projection(
    *,
    source_exile: str,
    capability_id: str,
    destination_exile: str,
    mode: str = "reference",
    parameters:
        Mapping[str, Any]
        | None = None,
    mask:
        Mapping[str, Any]
        | None = None,
    required_operations:
        Sequence[str]
        | None = None,
    required_version:
        str
        | None = None,
    request_context:
        Mapping[str, Any]
        | None = None,
) -> dict[str, Any]:
    source = str(
        source_exile
    ).strip().lower()

    destination = str(
        destination_exile
    ).strip().lower()

    projection_mode = str(
        mode
    ).strip().lower()

    capability = resolve_capability(
        source_exile=source,
        capability_id=capability_id,
    )

    compatibility = projection_compatibility(
        capability,
        destination_exile=destination,
        mode=projection_mode,
        required_operations=
            required_operations,
        required_version=
            required_version,
    )

    if not compatibility[
        "compatible"
    ]:
        return {
            "schema":
                (
                    "savant.exile-capability-"
                    "projection.v1"
                ),

            "owner":
                owner,

            "projection_owner":
                projection_owner,

            "authority_effect":
                authority_effect,

            "allowed":
                False,

            "state":
                compatibility[
                    "state"
                ],

            "source_exile":
                source,

            "destination_exile":
                destination,

            "capability_ref":
                capability[
                    "capability_ref"
                ],

            "mode":
                projection_mode,

            "compatibility":
                compatibility,

            "projection_only":
                True,
        }

    mask_result = apply_mask(
        capability,
        mask,
    )

    if not mask_result[
        "valid"
    ]:
        return {
            "schema":
                (
                    "savant.exile-capability-"
                    "projection.v1"
                ),

            "owner":
                owner,

            "projection_owner":
                projection_owner,

            "authority_effect":
                authority_effect,

            "allowed":
                False,

            "state":
                "fail",

            "source_exile":
                source,

            "destination_exile":
                destination,

            "capability_ref":
                capability[
                    "capability_ref"
                ],

            "mode":
                projection_mode,

            "compatibility":
                compatibility,

            "mask":
                mask_result,

            "projection_only":
                True,
        }

    effective_capability = (
        mask_result[
            "effective_capability"
        ]
    )

    parameter_result = apply_parameter_contract(
        effective_capability,
        parameters,
    )

    if not parameter_result[
        "valid"
    ]:
        return {
            "schema":
                (
                    "savant.exile-capability-"
                    "projection.v1"
                ),

            "owner":
                owner,

            "projection_owner":
                projection_owner,

            "authority_effect":
                authority_effect,

            "allowed":
                False,

            "state":
                "fail",

            "source_exile":
                source,

            "destination_exile":
                destination,

            "capability_ref":
                capability[
                    "capability_ref"
                ],

            "mode":
                projection_mode,

            "compatibility":
                compatibility,

            "parameter_validation":
                parameter_result,

            "projection_only":
                True,
        }

    request_body = {
        "source_exile":
            source,

        "capability_ref":
            capability[
                "capability_ref"
            ],

        "capability_digest":
            capability[
                "capability_digest"
            ],

        "destination_exile":
            destination,

        "mode":
            projection_mode,

        "parameters":
            parameter_result[
                "effective"
            ],

        "mask":
            mask_result[
                "mask"
            ],

        "required_operations":
            normalized_strings(
                required_operations
            ),

        "required_version":
            required_version,

        "request_context":
            copy.deepcopy(
                request_context
                or {}
            ),
    }

    request_digest = digest(
        request_body
    )

    projection_id = (
        "capability-projection:"
        + request_digest[
            :24
        ]
    )

    if projection_mode == "reference":
        instance_id = None

    else:
        instance_id = (
            "capability-instance:"
            + digest(
                {
                    "projection_id":
                        projection_id,

                    "destination":
                        destination,

                    "source":
                        capability[
                            "capability_ref"
                        ],
                }
            )[
                :24
            ]
        )

    effective = copy.deepcopy(
        effective_capability
    )

    effective[
        "consumer"
    ] = destination

    effective[
        "projection_mode"
    ] = projection_mode

    effective[
        "projection_id"
    ] = projection_id

    effective[
        "instance_id"
    ] = instance_id

    effective[
        "effective_parameters"
    ] = parameter_result[
        "effective"
    ]

    effective[
        "owner"
    ] = capability[
        "owner"
    ]

    effective[
        "authority_effect"
    ] = capability[
        "authority_effect"
    ]

    effective[
        "projection_only"
    ] = True

    effective[
        "authoritative"
    ] = False

    effective[
        "lineage"
    ] = {
        **copy.deepcopy(
            capability.get(
                "lineage",
                {}
            )
        ),

        "projection_id":
            projection_id,

        "projection_mode":
            projection_mode,

        "destination_exile":
            destination,

        "instance_id":
            instance_id,
    }

    effective[
        "effective_capability_digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in effective.items()
            if key
            != "effective_capability_digest"
        }
    )

    execution_plan = {
        "dispatch_owner":
            projection_owner,

        "capability_owner":
            capability[
                "owner"
            ],

        "execution_owner":
            capability[
                "execution_owner"
            ],

        "transformation_owner":
            (
                transformation_owner
                if mask_result[
                    "mask"
                ]
                else None
            ),

        "destination_exile":
            destination,

        "capability_ref":
            capability[
                "capability_ref"
            ],

        "instance_id":
            instance_id,

        "operations":
            effective.get(
                "operations",
                [],
            ),

        "parameters":
            parameter_result[
                "effective"
            ],

        "authority_effect":
            "none",

        "durable_mutation":
            False,

        "requires_owner_adapter":
            True,
    }

    stable_receipt = {
        "projection_id":
            projection_id,

        "request_digest":
            request_digest,

        "source_manifest_digest":
            capability[
                "source_manifest_digest"
            ],

        "source_capability_digest":
            capability[
                "capability_digest"
            ],

        "effective_capability_digest":
            effective[
                "effective_capability_digest"
            ],

        "source_owner":
            source,

        "destination_owner":
            destination,

        "capability_owner":
            capability[
                "owner"
            ],

        "projection_owner":
            projection_owner,

        "transformation_owner":
            (
                transformation_owner
                if mask_result[
                    "mask"
                ]
                else None
            ),

        "mode":
            projection_mode,

        "authority_effect":
            "none",

        "authority_transfer":
            False,

        "ownership_transfer":
            False,
    }

    receipt_digest = digest(
        stable_receipt
    )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "projection.v1"
            ),

        "owner":
            owner,

        "projection_owner":
            projection_owner,

        "transformation_owner":
            (
                transformation_owner
                if mask_result[
                    "mask"
                ]
                else None
            ),

        "authority_effect":
            authority_effect,

        "allowed":
            True,

        "state":
            "pass",

        "projection_id":
            projection_id,

        "instance_id":
            instance_id,

        "source_exile":
            source,

        "destination_exile":
            destination,

        "mode":
            projection_mode,

        "compatibility":
            compatibility,

        "parameter_validation":
            parameter_result,

        "source_capability":
            capability,

        "effective_capability":
            effective,

        "execution_plan":
            execution_plan,

        "receipt": {
            **stable_receipt,

            "receipt_digest":
                receipt_digest,

            "created_at":
                utc_now(),
        },

        "projection_only":
            True,

        "authoritative":
            False,
    }


def dependency_edges(
    capabilities:
        Iterable[
            Mapping[
                str,
                Any,
            ]
        ],
) -> list[
    tuple[
        str,
        str,
    ]
]:
    index = {
        str(
            capability[
                "capability_ref"
            ]
        ):
            capability
        for capability
        in capabilities
    }

    aliases = {}

    for reference, capability in index.items():
        aliases[
            reference
        ] = reference

        aliases[
            (
                str(
                    capability[
                        "source_owner"
                    ]
                )
                + ":"
                + str(
                    capability[
                        "source_id"
                    ]
                )
            )
        ] = reference

    edges = []

    for reference, capability in index.items():
        for dependency in capability.get(
            "dependencies",
            [],
        ):
            target = aliases.get(
                str(
                    dependency
                )
            )

            if target is None:
                continue

            edges.append(
                (
                    target,
                    reference,
                )
            )

    return sorted(
        set(
            edges
        )
    )


def stdlib_graph_analysis(
    nodes: Sequence[str],
    edges:
        Sequence[
            tuple[
                str,
                str,
            ]
        ],
) -> dict[str, Any]:
    adjacency = defaultdict(
        list
    )

    indegree = {
        node:
            0
        for node
        in nodes
    }

    for source, target in edges:
        adjacency[
            source
        ].append(
            target
        )

        indegree[
            target
        ] = (
            indegree.get(
                target,
                0,
            )
            + 1
        )

    queue = sorted(
        [
            node
            for node, degree
            in indegree.items()
            if degree == 0
        ]
    )

    order = []

    while queue:
        current = queue.pop(
            0
        )

        order.append(
            current
        )

        for target in sorted(
            adjacency.get(
                current,
                []
            )
        ):
            indegree[
                target
            ] -= 1

            if indegree[
                target
            ] == 0:
                queue.append(
                    target
                )

                queue.sort()

    cyclic = (
        len(
            order
        )
        != len(
            nodes
        )
    )

    cycles = []

    if cyclic:
        unresolved = sorted(
            set(
                nodes
            )
            - set(
                order
            )
        )

        cycles.append(
            {
                "class":
                    "dependency-cycle-or-cycle-dependent",

                "members":
                    unresolved,
            }
        )

    return {
        "backend":
            "stdlib",

        "acyclic":
            not cyclic,

        "topological_order":
            order,

        "cycles":
            cycles,
    }


def graph_analysis() -> dict[str, Any]:
    capabilities = all_capabilities()

    nodes = sorted(
        {
            str(
                capability[
                    "capability_ref"
                ]
            )
            for capability
            in capabilities
        }
    )

    edges = dependency_edges(
        capabilities
    )

    if nx is None:
        result = stdlib_graph_analysis(
            nodes,
            edges,
        )

    else:
        graph = nx.DiGraph()

        graph.add_nodes_from(
            nodes
        )

        graph.add_edges_from(
            edges
        )

        acyclic = nx.is_directed_acyclic_graph(
            graph
        )

        result = {
            "backend":
                "networkx",

            "acyclic":
                acyclic,

            "topological_order":
                (
                    list(
                        nx.lexicographical_topological_sort(
                            graph
                        )
                    )
                    if acyclic
                    else []
                ),

            "cycles":
                (
                    []
                    if acyclic
                    else [
                        {
                            "class":
                                "dependency-cycle",

                            "members":
                                cycle,
                        }
                        for cycle
                        in nx.simple_cycles(
                            graph
                        )
                    ]
                ),
        }

    return {
        "schema":
            (
                "savant.exile-capability-"
                "graph.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            "none",

        "projection_only":
            True,

        "node_count":
            len(
                nodes
            ),

        "edge_count":
            len(
                edges
            ),

        "nodes":
            nodes,

        "edges": [
            {
                "source":
                    source,

                "target":
                    target,
            }
            for source, target
            in edges
        ],

        **result,
    }


def dependency_closure(
    capability_ref: str,
) -> dict[str, Any]:
    capabilities = all_capabilities()

    refs = {
        str(
            capability[
                "capability_ref"
            ]
        )
        for capability
        in capabilities
    }

    if capability_ref not in refs:
        raise capability_fabric_error(
            (
                "unknown capability ref: "
                + capability_ref
            )
        )

    edges = dependency_edges(
        capabilities
    )

    reverse = defaultdict(
        set
    )

    for dependency, dependent in edges:
        reverse[
            dependent
        ].add(
            dependency
        )

    visited = set()

    stack = [
        capability_ref
    ]

    while stack:
        current = stack.pop()

        for dependency in sorted(
            reverse.get(
                current,
                set(),
            )
        ):
            if dependency in visited:
                continue

            visited.add(
                dependency
            )

            stack.append(
                dependency
            )

    return {
        "capability_ref":
            capability_ref,

        "dependency_count":
            len(
                visited
            ),

        "dependencies":
            sorted(
                visited
            ),
    }


def semantic_collisions(
    capabilities:
        Sequence[
            Mapping[
                str,
                Any,
            ]
        ],
) -> list[dict[str, Any]]:
    grouped = defaultdict(
        list
    )

    for capability in capabilities:
        semantic_key = str(
            capability.get(
                "source_id",
                "",
            )
        )

        if semantic_key:
            grouped[
                semantic_key
            ].append(
                capability
            )

    collisions = []

    for semantic_key, values in grouped.items():
        owners = sorted(
            {
                str(
                    item.get(
                        "owner"
                    )
                )
                for item
                in values
            }
        )

        if len(
            owners
        ) < 2:
            continue

        collisions.append(
            {
                "semantic_id":
                    semantic_key,

                "owners":
                    owners,

                "capability_refs":
                    sorted(
                        str(
                            item[
                                "capability_ref"
                            ]
                        )
                        for item
                        in values
                    ),

                "resolution":
                    (
                        "preserve owner-qualified "
                        "identity"
                    ),
            }
        )

    return sorted(
        collisions,
        key=lambda item:
            item[
                "semantic_id"
            ],
    )


def effective_array(
    *,
    exile: str,
    projections:
        Sequence[
            Mapping[
                str,
                Any,
            ]
        ]
        | None = None,
) -> dict[str, Any]:
    destination = str(
        exile
    ).strip().lower()

    if destination not in accepted_exiles:
        raise capability_fabric_error(
            (
                "unknown accepted exile: "
                + destination
            )
        )

    native = capabilities_for(
        destination
    )

    ingress = []

    for projection in projections or []:
        if not isinstance(
            projection,
            Mapping,
        ):
            continue

        if not projection.get(
            "allowed"
        ):
            continue

        if projection.get(
            "destination_exile"
        ) != destination:
            continue

        effective = projection.get(
            "effective_capability"
        )

        if isinstance(
            effective,
            Mapping,
        ):
            ingress.append(
                copy.deepcopy(
                    dict(
                        effective
                    )
                )
            )

    effective = []

    seen = set()

    for capability in [
        *native,
        *ingress,
    ]:
        identity = (
            capability.get(
                "instance_id"
            )
            or capability.get(
                "capability_ref"
            )
        )

        if identity in seen:
            continue

        seen.add(
            identity
        )

        effective.append(
            capability
        )

    egress = []

    for capability in native:
        modes = (
            capability.get(
                "projection",
                {}
            ).get(
                "modes",
                [],
            )
        )

        if modes:
            egress.append(
                {
                    "capability_ref":
                        capability[
                            "capability_ref"
                        ],

                    "modes":
                        modes,
                }
            )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "array.v1"
            ),

        "owner":
            destination,

        "authority_effect":
            "none",

        "projection_only":
            True,

        "native_count":
            len(
                native
            ),

        "ingress_count":
            len(
                ingress
            ),

        "effective_count":
            len(
                effective
            ),

        "egress_count":
            len(
                egress
            ),

        "native":
            native,

        "ingress":
            sorted(
                ingress,
                key=lambda item: (
                    str(
                        item.get(
                            "source_owner",
                            "",
                        )
                    ),
                    str(
                        item.get(
                            "source_id",
                            "",
                        )
                    ),
                ),
            ),

        "effective":
            sorted(
                effective,
                key=lambda item: (
                    str(
                        item.get(
                            "owner",
                            "",
                        )
                    ),
                    str(
                        item.get(
                            "source_id",
                            "",
                        )
                    ),
                ),
            ),

        "egress":
            sorted(
                egress,
                key=lambda item:
                    item[
                        "capability_ref"
                    ],
            ),

        "collisions":
            semantic_collisions(
                effective
            ),
    }


def negotiate(
    *,
    exile: str,
    requirements: Mapping[str, Any],
    projections:
        Sequence[
            Mapping[
                str,
                Any,
            ]
        ]
        | None = None,
) -> dict[str, Any]:
    array = effective_array(
        exile=exile,
        projections=projections,
    )

    required_ids = set(
        normalized_strings(
            requirements.get(
                "ids"
            )
        )
    )

    required_operations = set(
        normalized_strings(
            requirements.get(
                "operations"
            )
        )
    )

    required_kinds = set(
        normalized_strings(
            requirements.get(
                "kinds"
            )
        )
    )

    required_tags = set(
        normalized_strings(
            requirements.get(
                "tags"
            )
        )
    )

    required_owners = set(
        normalized_strings(
            requirements.get(
                "owners"
            )
        )
    )

    matches = []

    rejected = []

    for capability in array[
        "effective"
    ]:
        reasons = []

        if (
            required_ids
            and not (
                capability.get(
                    "source_id"
                )
                in required_ids
                or capability.get(
                    "capability_ref"
                )
                in required_ids
            )
        ):
            reasons.append(
                "id"
            )

        if (
            required_operations
            - set(
                capability.get(
                    "operations",
                    [],
                )
            )
        ):
            reasons.append(
                "operations"
            )

        if (
            required_kinds
            and capability.get(
                "kind"
            )
            not in required_kinds
        ):
            reasons.append(
                "kind"
            )

        if (
            required_tags
            - set(
                capability.get(
                    "tags",
                    [],
                )
            )
        ):
            reasons.append(
                "tags"
            )

        if (
            required_owners
            and capability.get(
                "owner"
            )
            not in required_owners
        ):
            reasons.append(
                "owner"
            )

        if reasons:
            rejected.append(
                {
                    "capability_ref":
                        capability[
                            "capability_ref"
                        ],

                    "reasons":
                        reasons,
                }
            )

        else:
            matches.append(
                capability
            )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "negotiation.v1"
            ),

        "owner":
            exile,

        "authority_effect":
            "none",

        "projection_only":
            True,

        "requirements":
            dict(
                requirements
            ),

        "match_count":
            len(
                matches
            ),

        "matches":
            sorted(
                matches,
                key=lambda item: (
                    str(
                        item.get(
                            "owner",
                            "",
                        )
                    ),
                    str(
                        item.get(
                            "source_id",
                            "",
                        )
                    ),
                ),
            ),

        "rejected":
            rejected,
    }


def capability_matrix() -> dict[str, Any]:
    rows = []

    cache = {
        exile:
            capabilities_for(
                exile
            )
        for exile
        in accepted_exiles
    }

    for source in accepted_exiles:
        capabilities = cache[
            source
        ]

        for destination in accepted_exiles:
            reference_count = 0

            instance_count = 0

            composition_count = 0

            for capability in capabilities:
                for mode in (
                    "reference",
                    "instance",
                    "composition",
                ):
                    compatibility = (
                        projection_compatibility(
                            capability,
                            destination_exile=
                                destination,
                            mode=mode,
                        )
                    )

                    if not compatibility[
                        "compatible"
                    ]:
                        continue

                    if mode == "reference":
                        reference_count += 1

                    elif mode == "instance":
                        instance_count += 1

                    else:
                        composition_count += 1

            rows.append(
                {
                    "source":
                        source,

                    "destination":
                        destination,

                    "native_capability_count":
                        len(
                            capabilities
                        ),

                    "reference_projectable":
                        reference_count,

                    "instance_projectable":
                        instance_count,

                    "composition_projectable":
                        composition_count,
                }
            )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "matrix.v1"
            ),

        "owner":
            owner,

        "authority_effect":
            "none",

        "projection_only":
            True,

        "exile_count":
            len(
                accepted_exiles
            ),

        "rows":
            rows,
    }


def manifest_status() -> list[dict[str, Any]]:
    output = []

    for exile in accepted_exiles:
        manifest = read_manifest(
            exile
        )

        output.append(
            {
                "exile":
                    exile,

                "manifest_present":
                    manifest[
                        "manifest_present"
                    ],

                "manifest_status":
                    manifest[
                        "status"
                    ],

                "manifest_digest":
                    manifest[
                        "manifest_digest"
                    ],

                "capability_count":
                    len(
                        manifest[
                            "capabilities"
                        ]
                    ),

                "path":
                    manifest[
                        "path"
                    ],
            }
        )

    return output


def capability_schema() -> dict[str, Any]:
    return {
        "$schema":
            (
                "https://json-schema.org/"
                "draft/2020-12/schema"
            ),

        "$id":
            (
                "savant://schema/"
                "exile-capability/1.0.0"
            ),

        "title":
            "savant exile capability",

        "type":
            "object",

        "required": [
            "id",
        ],

        "properties": {
            "id": {
                "type":
                    "string",

                "minLength":
                    1,
            },

            "owner": {
                "type":
                    "string",
            },

            "status": {
                "type":
                    "string",
            },

            "kind": {
                "type":
                    "string",
            },

            "purpose": {
                "type": [
                    "string",
                    "null",
                ],
            },

            "version": {
                "type":
                    "string",
            },

            "authority_effect": {
                "type":
                    "string",
            },

            "execution_owner": {
                "type":
                    "string",
            },

            "operations": {
                "type":
                    "array",

                "items": {
                    "type":
                        "string",
                },

                "uniqueItems":
                    True,
            },

            "dependencies": {
                "type":
                    "array",

                "items": {
                    "type":
                        "string",
                },

                "uniqueItems":
                    True,
            },

            "projection": {
                "type":
                    "object",

                "properties": {
                    "modes": {
                        "type":
                            "array",

                        "items": {
                            "enum": [
                                "reference",
                                "instance",
                                "composition",
                            ],
                        },
                    },

                    "allowed_consumers": {
                        "type":
                            "array",

                        "items": {
                            "type":
                                "string",
                        },
                    },

                    "denied_consumers": {
                        "type":
                            "array",

                        "items": {
                            "type":
                                "string",
                        },
                    },

                    "instanceable": {
                        "type":
                            "boolean",
                    },

                    "composable": {
                        "type":
                            "boolean",
                    },
                },
            },

            "parameters": {
                "type":
                    "object",
            },

            "inputs": {},

            "outputs": {},

            "permissions": {
                "type":
                    "object",
            },

            "requirements": {
                "type":
                    "object",
            },

            "tags": {
                "type":
                    "array",

                "items": {
                    "type":
                        "string",
                },
            },

            "labels": {
                "type":
                    "array",

                "items": {
                    "type":
                        "string",
                },
            },
        },

        "additionalProperties":
            True,
    }


def status() -> dict[str, Any]:
    manifests = manifest_status()

    capabilities = all_capabilities()

    graph = graph_analysis()

    unresolved_manifests = [
        item[
            "exile"
        ]
        for item
        in manifests
        if not item[
            "manifest_present"
        ]
    ]

    empty_manifests = [
        item[
            "exile"
        ]
        for item
        in manifests
        if (
            item[
                "manifest_present"
            ]
            and item[
                "capability_count"
            ]
            == 0
        )
    ]

    owner_conflicts = [
        capability[
            "capability_ref"
        ]
        for capability
        in capabilities
        if capability[
            "owner_conflict"
        ]
    ]

    return {
        "schema":
            (
                "savant.exile-capability-"
                "fabric-status.v1"
            ),

        "owner":
            owner,

        "projection_owner":
            projection_owner,

        "transformation_owner":
            transformation_owner,

        "authority_effect":
            authority_effect,

        "authority_store":
            False,

        "projection_only":
            True,

        "accepted_exile_count":
            len(
                accepted_exiles
            ),

        "capability_count":
            len(
                capabilities
            ),

        "manifest_count":
            sum(
                1
                for item
                in manifests
                if item[
                    "manifest_present"
                ]
            ),

        "unresolved_manifests":
            unresolved_manifests,

        "empty_manifests":
            empty_manifests,

        "owner_conflicts":
            owner_conflicts,

        "graph_backend":
            graph[
                "backend"
            ],

        "graph_acyclic":
            graph[
                "acyclic"
            ],

        "enhancement_count":
            len(
                implemented_enhancements
            ),

        "enhancements":
            list(
                implemented_enhancements
            ),

        "projection_modes":
            sorted(
                projection_modes
            ),

        "modus_masking":
            True,

        "filament_projection_execution":
            True,

        "ownership_transfer":
            False,

        "authority_transfer":
            False,

        "ready":
            (
                not owner_conflicts
                and graph[
                    "acyclic"
                ]
            ),
    }


def selftest() -> dict[str, Any]:
    capability = None

    source = None

    for exile in accepted_exiles:
        values = capabilities_for(
            exile
        )

        if values:
            capability = values[
                0
            ]

            source = exile

            break

    if capability is None:
        raise capability_fabric_error(
            (
                "no current capability "
                "manifest contains a capability"
            )
        )

    destination = next(
        exile
        for exile
        in accepted_exiles
        if exile != source
    )

    result = create_projection(
        source_exile=source,
        capability_id=str(
            capability[
                "source_id"
            ]
        ),
        destination_exile=
            destination,
        mode="reference",
    )

    if not result.get(
        "allowed"
    ):
        raise capability_fabric_error(
            (
                "focused reference projection "
                "failed"
            )
        )

    if (
        result[
            "source_capability"
        ][
            "owner"
        ]
        != result[
            "effective_capability"
        ][
            "owner"
        ]
    ):
        raise capability_fabric_error(
            (
                "projection changed "
                "capability ownership"
            )
        )

    if (
        result[
            "authority_effect"
        ]
        != "none"
    ):
        raise capability_fabric_error(
            (
                "capability fabric created "
                "authority"
            )
        )

    array = effective_array(
        exile=destination,
        projections=[
            result
        ],
    )

    if array[
        "ingress_count"
    ] != 1:
        raise capability_fabric_error(
            (
                "effective-array ingress "
                "projection failed"
            )
        )

    return {
        "schema":
            (
                "savant.exile-capability-"
                "fabric-selftest.v1"
            ),

        "ok":
            True,

        "source":
            source,

        "destination":
            destination,

        "capability_ref":
            capability[
                "capability_ref"
            ],

        "projection_id":
            result[
                "projection_id"
            ],

        "ownership_preserved":
            True,

        "authority_effect":
            "none",

        "effective_ingress":
            array[
                "ingress_count"
            ],

        "graph":
            graph_analysis(),
    }


__all__ = [
    "accepted_exiles",
    "all_capabilities",
    "capabilities_for",
    "capability_matrix",
    "capability_schema",
    "create_projection",
    "dependency_closure",
    "effective_array",
    "graph_analysis",
    "manifest_status",
    "negotiate",
    "normalize_capability",
    "projection_compatibility",
    "read_manifest",
    "resolve_capability",
    "selftest",
    "status",
]
