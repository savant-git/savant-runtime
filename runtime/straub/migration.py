#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.migration.v1"
owner = "savant"
authority_effect = "none"


def _validate_capsule_digest(
    capsule: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        capsule,
        Mapping,
    ):
        raise StraubValidationError(
            "migration requires "
            "straub capsule"
        )

    if (
        capsule.get(
            "schema"
        )
        != "savant.straub.capsule.v2"
    ):
        raise StraubValidationError(
            "migration requires "
            "straub capsule v2"
        )

    supplied_digest = str(
        capsule.get(
            "digest"
        )
        or ""
    )

    if not supplied_digest:
        raise StraubValidationError(
            "capsule digest missing"
        )

    unsigned = deepcopy(
        dict(
            capsule
        )
    )

    unsigned.pop(
        "digest",
        None,
    )

    calculated = content_digest(
        unsigned
    )

    if (
        supplied_digest
        != calculated
    ):
        raise StraubValidationError(
            "capsule digest mismatch"
        )

    return deepcopy(
        dict(
            capsule
        )
    )


def _key_records(
    records: Any,
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(
        records,
        list,
    ):
        raise StraubValidationError(
            f"{label} must be a list"
        )

    keyed: dict[
        str,
        dict[str, Any],
    ] = {}

    for raw in records:
        if not isinstance(
            raw,
            Mapping,
        ):
            raise StraubValidationError(
                f"{label} record invalid"
            )

        record = deepcopy(
            dict(
                raw
            )
        )

        record_id = str(
            record.get(
                "id"
            )
            or ""
        ).strip()

        if not record_id:
            raise StraubValidationError(
                f"{label} record id missing"
            )

        if record_id in keyed:
            raise StraubValidationError(
                f"duplicate {label} identity: "
                f"{record_id}"
            )

        keyed[
            record_id
        ] = record

    return dict(
        sorted(
            keyed.items()
        )
    )


def _ordered_records(
    records: Any,
    *,
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(
        records,
        Mapping,
    ):
        raise StraubValidationError(
            f"{label} keyed records invalid"
        )

    result: list[
        dict[str, Any]
    ] = []

    for record_id in sorted(
        records
    ):
        raw = records[
            record_id
        ]

        if not isinstance(
            raw,
            Mapping,
        ):
            raise StraubValidationError(
                f"{label} keyed record invalid"
            )

        record = deepcopy(
            dict(
                raw
            )
        )

        if (
            str(
                record.get(
                    "id"
                )
                or ""
            )
            != record_id
        ):
            raise StraubValidationError(
                f"{label} keyed identity mismatch"
            )

        result.append(
            record
        )

    return result


def to_keyed_representation(
    capsule: Mapping[str, Any],
) -> dict[str, Any]:
    canonical = (
        _validate_capsule_digest(
            capsule
        )
    )

    source_digest = canonical[
        "digest"
    ]

    projection = {
        "schema":
            "savant.straub."
            "keyed-representation.v1",
        "kind":
            "representation",
        "representation":
            "keyed",
        "canonical_schema":
            canonical[
                "schema"
            ],
        "source_capsule_digest":
            source_digest,
        "instances_by_id":
            _key_records(
                canonical.get(
                    "instances"
                ),
                label="instances",
            ),
        "membranes_by_id":
            _key_records(
                canonical.get(
                    "membranes"
                ),
                label="membranes",
            ),
        "history":
            deepcopy(
                canonical.get(
                    "history"
                )
            ),
        "canonical_fields": {
            "projection_only":
                deepcopy(
                    canonical.get(
                        "projection_only"
                    )
                ),
            "storage_engine":
                deepcopy(
                    canonical.get(
                        "storage_engine"
                    )
                ),
            "authority_effect":
                deepcopy(
                    canonical.get(
                        "authority_effect"
                    )
                ),
        },
        "lineage": {
            "derived_from": [
                source_digest,
            ],
            "representation_of":
                source_digest,
            "reversible":
                True,
        },
        "projection_only":
            True,
        "authority_effect":
            "none",
    }

    projection[
        "digest"
    ] = content_digest(
        projection
    )

    return projection


def validate_keyed_representation(
    representation: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        representation,
        Mapping,
    ):
        raise StraubValidationError(
            "keyed representation "
            "must be an object"
        )

    if (
        representation.get(
            "schema"
        )
        != "savant.straub."
        "keyed-representation.v1"
    ):
        raise StraubValidationError(
            "unsupported straub "
            "representation"
        )

    supplied_digest = str(
        representation.get(
            "digest"
        )
        or ""
    )

    unsigned = deepcopy(
        dict(
            representation
        )
    )

    unsigned.pop(
        "digest",
        None,
    )

    calculated = content_digest(
        unsigned
    )

    if (
        supplied_digest
        != calculated
    ):
        raise StraubValidationError(
            "representation digest mismatch"
        )

    if (
        representation.get(
            "projection_only"
        )
        is not True
    ):
        raise StraubValidationError(
            "representation must be "
            "projection-only"
        )

    lineage = representation.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        Mapping,
    ):
        raise StraubValidationError(
            "representation lineage missing"
        )

    source_digest = str(
        representation.get(
            "source_capsule_digest"
        )
        or ""
    )

    if not source_digest:
        raise StraubValidationError(
            "representation source "
            "digest missing"
        )

    if (
        lineage.get(
            "representation_of"
        )
        != source_digest
    ):
        raise StraubValidationError(
            "representation lineage mismatch"
        )

    if (
        lineage.get(
            "reversible"
        )
        is not True
    ):
        raise StraubValidationError(
            "representation is not "
            "declared reversible"
        )

    return {
        "schema":
            schema,
        "valid":
            True,
        "representation_digest":
            supplied_digest,
        "source_capsule_digest":
            source_digest,
        "reversible":
            True,
        "authority_effect":
            authority_effect,
    }


def from_keyed_representation(
    representation: Mapping[str, Any],
) -> dict[str, Any]:
    validate_keyed_representation(
        representation
    )

    fields = representation.get(
        "canonical_fields"
    )

    if not isinstance(
        fields,
        Mapping,
    ):
        raise StraubValidationError(
            "canonical representation "
            "fields missing"
        )

    history = representation.get(
        "history"
    )

    if not isinstance(
        history,
        Mapping,
    ):
        raise StraubValidationError(
            "representation history missing"
        )

    capsule = {
        "schema":
            str(
                representation.get(
                    "canonical_schema"
                )
                or ""
            ),
        "instances":
            _ordered_records(
                representation.get(
                    "instances_by_id"
                ),
                label="instances",
            ),
        "membranes":
            _ordered_records(
                representation.get(
                    "membranes_by_id"
                ),
                label="membranes",
            ),
        "history":
            deepcopy(
                dict(
                    history
                )
            ),
        "projection_only":
            deepcopy(
                fields.get(
                    "projection_only"
                )
            ),
        "storage_engine":
            deepcopy(
                fields.get(
                    "storage_engine"
                )
            ),
        "authority_effect":
            deepcopy(
                fields.get(
                    "authority_effect"
                )
            ),
    }

    capsule[
        "digest"
    ] = content_digest(
        capsule
    )

    source_digest = str(
        representation.get(
            "source_capsule_digest"
        )
        or ""
    )

    if (
        capsule[
            "digest"
        ]
        != source_digest
    ):
        raise StraubValidationError(
            "representation rollback "
            "does not reproduce source capsule"
        )

    return capsule


def migration_receipt(
    *,
    source_capsule: Mapping[str, Any],
    representation: Mapping[str, Any],
    restored_capsule: Mapping[str, Any],
) -> dict[str, Any]:
    source = (
        _validate_capsule_digest(
            source_capsule
        )
    )

    validation = (
        validate_keyed_representation(
            representation
        )
    )

    restored = (
        _validate_capsule_digest(
            restored_capsule
        )
    )

    source_digest = source[
        "digest"
    ]

    restored_digest = restored[
        "digest"
    ]

    reversible = (
        source_digest
        == restored_digest
        == validation[
            "source_capsule_digest"
        ]
    )

    receipt = {
        "schema":
            "savant.straub."
            "migration-receipt.v1",
        "kind":
            "migration.receipt",
        "migration":
            "capsule-v2:"
            "canonical-to-keyed-v1",
        "source_schema":
            source[
                "schema"
            ],
        "target_schema":
            representation[
                "schema"
            ],
        "source_digest":
            source_digest,
        "representation_digest":
            representation[
                "digest"
            ],
        "restored_digest":
            restored_digest,
        "reversible":
            reversible,
        "semantic_mutation":
            False,
        "authority_effect":
            "none",
    }

    receipt[
        "digest"
    ] = content_digest(
        receipt
    )

    return receipt


def migrate_and_verify(
    capsule: Mapping[str, Any],
) -> dict[str, Any]:
    representation = (
        to_keyed_representation(
            capsule
        )
    )

    restored = (
        from_keyed_representation(
            representation
        )
    )

    receipt = migration_receipt(
        source_capsule=capsule,
        representation=representation,
        restored_capsule=restored,
    )

    if (
        receipt[
            "reversible"
        ]
        is not True
    ):
        raise StraubValidationError(
            "straub representation "
            "migration is not reversible"
        )

    return {
        "schema":
            "savant.straub."
            "migration-result.v1",
        "representation":
            representation,
        "restored_capsule":
            restored,
        "receipt":
            receipt,
        "authority_effect":
            "none",
    }
