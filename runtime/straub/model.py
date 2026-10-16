#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping


schema = "savant.straub.model.v1"
owner = "savant"
authority_effect = "none"


class StraubError(RuntimeError):
    pass


class StraubValidationError(StraubError):
    pass


class StraubConflictError(StraubError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def content_digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean_id(
    value: Any,
    *,
    field: str,
) -> str:
    result = str(
        value or ""
    ).strip()

    if not result:
        raise StraubValidationError(
            f"{field} is required"
        )

    if result != result.lower():
        raise StraubValidationError(
            f"{field} must be lowercase"
        )

    return result


def normalize_string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if not isinstance(
        value,
        (list, tuple, set),
    ):
        raise StraubValidationError(
            "expected a collection"
        )

    result: set[str] = set()

    for item in value:
        text = str(
            item or ""
        ).strip()

        if text:
            result.add(text)

    return sorted(result)


def normalize_validity(
    value: Any,
) -> dict[str, str | None]:
    if value is None:
        value = {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise StraubValidationError(
            "validity must be an object"
        )

    return {
        "valid_from":
            (
                str(
                    value.get(
                        "valid_from"
                    )
                ).strip()
                if value.get(
                    "valid_from"
                )
                else None
            ),
        "valid_until":
            (
                str(
                    value.get(
                        "valid_until"
                    )
                ).strip()
                if value.get(
                    "valid_until"
                )
                else None
            ),
    }


def normalize_provenance(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        value = {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise StraubValidationError(
            "provenance must be an object"
        )

    return {
        "source":
            str(
                value.get(
                    "source"
                )
                or ""
            ).strip(),
        "confidence":
            str(
                value.get(
                    "confidence"
                )
                or "confirmed"
            ).strip(),
        "evidence":
            normalize_string_list(
                value.get(
                    "evidence"
                )
            ),
        "created_from":
            normalize_string_list(
                value.get(
                    "created_from"
                )
            ),
    }


def normalize_lineage(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        value = {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise StraubValidationError(
            "lineage must be an object"
        )

    return {
        "derived_from":
            normalize_string_list(
                value.get(
                    "derived_from"
                )
            ),
        "supersedes":
            normalize_string_list(
                value.get(
                    "supersedes"
                )
            ),
        "superseded_by":
            (
                str(
                    value.get(
                        "superseded_by"
                    )
                ).strip()
                if value.get(
                    "superseded_by"
                )
                else None
            ),
        "history":
            deepcopy(
                list(
                    value.get(
                        "history"
                    )
                    or []
                )
            ),
    }


def normalize_instance(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise StraubValidationError(
            "instance must be an object"
        )

    instance_id = clean_id(
        value.get("id"),
        field="id",
    )

    kind = clean_id(
        value.get(
            "kind",
            "instance",
        ),
        field="kind",
    )

    result = {
        "schema":
            "savant.straub.instance.v1",
        "id":
            instance_id,
        "kind":
            kind,
        "status":
            str(
                value.get(
                    "status"
                )
                or "active"
            ).strip(),
        "authority":
            deepcopy(
                value.get(
                    "authority"
                )
            ),
        "payload":
            deepcopy(
                value.get(
                    "payload"
                )
            ),
        "metadata":
            deepcopy(
                dict(
                    value.get(
                        "metadata"
                    )
                    or {}
                )
            ),
        "dependencies":
            normalize_string_list(
                value.get(
                    "dependencies"
                )
            ),
        "relationships":
            deepcopy(
                list(
                    value.get(
                        "relationships"
                    )
                    or []
                )
            ),
        "provenance":
            normalize_provenance(
                value.get(
                    "provenance"
                )
            ),
        "lineage":
            normalize_lineage(
                value.get(
                    "lineage"
                )
            ),
        "validity":
            normalize_validity(
                value.get(
                    "validity"
                )
            ),
        "extensions":
            deepcopy(
                dict(
                    value.get(
                        "extensions"
                    )
                    or {}
                )
            ),
    }

    result["digest"] = (
        content_digest(
            result
        )
    )

    return result


def umbra_definition(
    *,
    instance_id: str,
    label: str,
    value_type: str,
    applies_to: list[str] | None = None,
    description: str = "",
    provenance: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    constraints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return normalize_instance(
        {
            "id":
                instance_id,
            "kind":
                "umbra.definition",
            "payload": {
                "label":
                    str(
                        label
                    ).strip(),
                "description":
                    str(
                        description
                    ).strip(),
                "value_type":
                    str(
                        value_type
                    ).strip(),
                "applies_to":
                    sorted(
                        set(
                            applies_to
                            or []
                        )
                    ),
                "constraints":
                    deepcopy(
                        dict(
                            constraints
                            or {}
                        )
                    ),
            },
            "provenance":
                provenance,
            "lineage":
                lineage,
        }
    )


def umbra_value(
    *,
    instance_id: str,
    definition_id: str,
    value: Any,
    provenance: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    validity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    definition = clean_id(
        definition_id,
        field="definition_id",
    )

    return normalize_instance(
        {
            "id":
                instance_id,
            "kind":
                "umbra.value",
            "payload": {
                "definition":
                    definition,
                "value":
                    deepcopy(
                        value
                    ),
            },
            "dependencies": [
                definition,
            ],
            "provenance":
                provenance,
            "lineage":
                lineage,
            "validity":
                validity,
        }
    )


def membrane(
    *,
    membrane_id: str,
    subject_id: str,
    umbra_id: str,
    relation: str = "described_by",
    provenance: Mapping[str, Any] | None = None,
    lineage: Mapping[str, Any] | None = None,
    validity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    membrane_ref = clean_id(
        membrane_id,
        field="membrane_id",
    )

    subject_ref = clean_id(
        subject_id,
        field="subject_id",
    )

    umbra_ref = clean_id(
        umbra_id,
        field="umbra_id",
    )

    relation_ref = clean_id(
        relation,
        field="relation",
    )

    result = {
        "schema":
            "savant.straub.membrane.v1",
        "id":
            membrane_ref,
        "kind":
            "membrane",
        "from":
            subject_ref,
        "to":
            umbra_ref,
        "relation":
            relation_ref,
        "direction":
            "directed",
        "dependencies":
            sorted(
                {
                    subject_ref,
                    umbra_ref,
                }
            ),
        "provenance":
            normalize_provenance(
                provenance
            ),
        "lineage":
            normalize_lineage(
                lineage
            ),
        "validity":
            normalize_validity(
                validity
            ),
        "authority_effect":
            "none",
    }

    result["digest"] = (
        content_digest(
            result
        )
    )

    return result


def dyad(
    *,
    subject: Mapping[str, Any],
    umbra: Mapping[str, Any],
    membrane_record: Mapping[str, Any],
) -> dict[str, Any]:
    subject_id = clean_id(
        subject.get("id"),
        field="subject.id",
    )

    umbra_id = clean_id(
        umbra.get("id"),
        field="umbra.id",
    )

    membrane_id = clean_id(
        membrane_record.get(
            "id"
        ),
        field="membrane.id",
    )

    if (
        membrane_record.get(
            "from"
        )
        != subject_id
    ):
        raise StraubValidationError(
            "membrane subject mismatch"
        )

    if (
        membrane_record.get(
            "to"
        )
        != umbra_id
    ):
        raise StraubValidationError(
            "membrane umbra mismatch"
        )

    result = {
        "schema":
            "savant.straub.dyad.v1",
        "kind":
            "dyad",
        "subject":
            subject_id,
        "umbra":
            umbra_id,
        "membrane":
            membrane_id,
        "authority_effect":
            "none",
    }

    result["digest"] = (
        content_digest(
            result
        )
    )

    return result
