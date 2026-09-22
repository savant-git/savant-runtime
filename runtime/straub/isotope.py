#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.carbon.straub.isotope.v1"
owner_exile = "carbon"
owner_module = "straub"
authority_effect = "none"


def isotope(
    *,
    source_ids: list[str],
    projection: Mapping[str, Any],
    projection_type: str,
    source_capsule_digest: str | None = None,
    dependencies: list[str] | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a deterministic datrix isotope.

    An isotope is a deterministic projection derived from
    canonical datrix substance. It is never independent
    semantic authority.
    """

    if not isinstance(
        projection,
        Mapping,
    ):
        raise StraubValidationError(
            "isotope projection must be an object"
        )

    projection_type = str(
        projection_type
    ).strip()

    if not projection_type:
        raise StraubValidationError(
            "isotope projection_type required"
        )

    normalized_source_ids = sorted(
        {
            str(item).strip()
            for item in source_ids
            if str(item).strip()
        }
    )

    normalized_dependencies = sorted(
        {
            str(item).strip()
            for item in (
                dependencies
                or []
            )
            if str(item).strip()
        }
    )

    record = {
        "schema":
            schema,
        "kind":
            "isotope",
        "projection_type":
            projection_type,
        "source_ids":
            normalized_source_ids,
        "source_capsule_digest":
            (
                str(
                    source_capsule_digest
                ).strip()
                if source_capsule_digest
                is not None
                else None
            ),
        "dependencies":
            normalized_dependencies,
        "projection":
            deepcopy(
                dict(
                    projection
                )
            ),
        "provenance":
            deepcopy(
                dict(
                    provenance
                    or {}
                )
            ),
        "deterministic":
            True,
        "projection_only":
            True,
        "semantic_authority":
            False,
        "authority_effect":
            "none",
    }

    record[
        "digest"
    ] = content_digest(
        record
    )

    record[
        "id"
    ] = (
        "isotope:"
        + record[
            "digest"
        ]
    )

    return record


def validate_isotope(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        record,
        Mapping,
    ):
        raise StraubValidationError(
            "isotope must be an object"
        )

    candidate = deepcopy(
        dict(
            record
        )
    )

    if (
        candidate.get(
            "schema"
        )
        != schema
    ):
        raise StraubValidationError(
            "unsupported isotope schema"
        )

    if (
        candidate.get(
            "kind"
        )
        != "isotope"
    ):
        raise StraubValidationError(
            "invalid isotope kind"
        )

    if (
        candidate.get(
            "deterministic"
        )
        is not True
    ):
        raise StraubValidationError(
            "isotope must be deterministic"
        )

    if (
        candidate.get(
            "projection_only"
        )
        is not True
    ):
        raise StraubValidationError(
            "isotope must be projection-only"
        )

    if (
        candidate.get(
            "semantic_authority"
        )
        is not False
    ):
        raise StraubValidationError(
            "isotope cannot be semantic authority"
        )

    expected_digest_record = deepcopy(
        candidate
    )

    expected_digest_record.pop(
        "id",
        None,
    )

    supplied_digest = (
        expected_digest_record.pop(
            "digest",
            None,
        )
    )

    expected_digest = content_digest(
        expected_digest_record
    )

    if (
        supplied_digest
        != expected_digest
    ):
        raise StraubValidationError(
            "isotope digest mismatch"
        )

    expected_id = (
        "isotope:"
        + expected_digest
    )

    if (
        candidate.get(
            "id"
        )
        != expected_id
    ):
        raise StraubValidationError(
            "isotope id mismatch"
        )

    return candidate
