#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.query.v2"
owner = "savant"
authority_effect = "none"


def _instant(
    value: str | datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        parsed = value
    else:
        text = str(
            value
        ).strip()

        if text.endswith("Z"):
            text = (
                text[:-1]
                + "+00:00"
            )

        try:
            parsed = (
                datetime.fromisoformat(
                    text
                )
            )
        except ValueError as exc:
            raise StraubValidationError(
                "invalid query instant"
            ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed


def _record_valid_at(
    record: Mapping[str, Any],
    at: datetime | None,
) -> bool:
    if at is None:
        return True

    validity = record.get(
        "validity"
    )

    if not isinstance(
        validity,
        Mapping,
    ):
        return True

    valid_from = validity.get(
        "valid_from"
    )

    valid_until = validity.get(
        "valid_until"
    )

    if valid_from:
        start = _instant(
            str(
                valid_from
            )
        )

        if at < start:
            return False

    if valid_until:
        end = _instant(
            str(
                valid_until
            )
        )

        if at >= end:
            return False

    return True


def _string_set(
    value: Any,
) -> set[str]:
    if value is None:
        return set()

    if not isinstance(
        value,
        (list, tuple, set),
    ):
        raise StraubValidationError(
            "query collection must "
            "be a collection"
        )

    return {
        str(
            item
        ).strip()
        for item in value
        if str(
            item
        ).strip()
    }


def _capsule_maps(
    capsule: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[str]],
]:
    if not isinstance(
        capsule,
        Mapping,
    ):
        raise StraubValidationError(
            "straub query requires capsule"
        )

    if (
        capsule.get(
            "schema"
        )
        != "savant.straub.capsule.v2"
    ):
        raise StraubValidationError(
            "straub query requires "
            "capsule v2"
        )

    instances_raw = capsule.get(
        "instances"
    )

    membranes_raw = capsule.get(
        "membranes"
    )

    if not isinstance(
        instances_raw,
        list,
    ):
        raise StraubValidationError(
            "capsule instances invalid"
        )

    if not isinstance(
        membranes_raw,
        list,
    ):
        raise StraubValidationError(
            "capsule membranes invalid"
        )

    instances: dict[
        str,
        dict[str, Any],
    ] = {}

    membranes: dict[
        str,
        dict[str, Any],
    ] = {}

    outgoing: dict[
        str,
        list[str],
    ] = {}

    for raw in instances_raw:
        if not isinstance(
            raw,
            Mapping,
        ):
            raise StraubValidationError(
                "capsule instance invalid"
            )

        record = deepcopy(
            dict(
                raw
            )
        )

        instance_id = str(
            record.get(
                "id"
            )
            or ""
        ).strip()

        if not instance_id:
            raise StraubValidationError(
                "capsule instance id missing"
            )

        instances[
            instance_id
        ] = record

    for raw in membranes_raw:
        if not isinstance(
            raw,
            Mapping,
        ):
            raise StraubValidationError(
                "capsule membrane invalid"
            )

        record = deepcopy(
            dict(
                raw
            )
        )

        membrane_id = str(
            record.get(
                "id"
            )
            or ""
        ).strip()

        source = str(
            record.get(
                "from"
            )
            or ""
        ).strip()

        target = str(
            record.get(
                "to"
            )
            or ""
        ).strip()

        if (
            not membrane_id
            or not source
            or not target
        ):
            raise StraubValidationError(
                "capsule membrane incomplete"
            )

        membranes[
            membrane_id
        ] = record

        outgoing.setdefault(
            source,
            []
        ).append(
            membrane_id
        )

    for membrane_ids in (
        outgoing.values()
    ):
        membrane_ids.sort()

    return (
        instances,
        membranes,
        outgoing,
    )


class StraubQuery:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        (
            self._instances,
            self._membranes,
            self._outgoing,
        ) = _capsule_maps(
            capsule
        )

    def effective_metadata(
        self,
        subject_id: str,
        *,
        at: str | datetime | None = None,
        relation_in: list[str] | None = None,
        definition_in: list[str] | None = None,
        authority_equals: Any = None,
        authority_filter_enabled: bool = False,
    ) -> dict[str, Any]:
        subject = self._instances.get(
            subject_id
        )

        if subject is None:
            raise KeyError(
                subject_id
            )

        moment = _instant(
            at
        )

        relations = _string_set(
            relation_in
        )

        definitions = _string_set(
            definition_in
        )

        rows: list[
            dict[str, Any]
        ] = []

        for membrane_id in (
            self._outgoing.get(
                subject_id,
                []
            )
        ):
            edge = self._membranes[
                membrane_id
            ]

            if not _record_valid_at(
                edge,
                moment,
            ):
                continue

            relation = str(
                edge.get(
                    "relation"
                )
                or ""
            )

            if (
                relations
                and relation
                not in relations
            ):
                continue

            umbra_id = str(
                edge.get(
                    "to"
                )
                or ""
            )

            umbra = self._instances.get(
                umbra_id
            )

            if umbra is None:
                continue

            if not _record_valid_at(
                umbra,
                moment,
            ):
                continue

            if (
                authority_filter_enabled
                and umbra.get(
                    "authority"
                )
                != authority_equals
            ):
                continue

            payload = umbra.get(
                "payload"
            )

            if not isinstance(
                payload,
                Mapping,
            ):
                payload = {}

            definition_id = str(
                payload.get(
                    "definition"
                )
                or ""
            )

            if (
                definitions
                and definition_id
                not in definitions
            ):
                continue

            rows.append(
                {
                    "umbra_id":
                        umbra_id,
                    "umbra_kind":
                        str(
                            umbra.get(
                                "kind"
                            )
                            or ""
                        ),
                    "definition":
                        (
                            definition_id
                            or None
                        ),
                    "value":
                        deepcopy(
                            payload.get(
                                "value"
                            )
                        ),
                    "relation":
                        relation,
                    "membrane":
                        membrane_id,
                    "authority":
                        deepcopy(
                            umbra.get(
                                "authority"
                            )
                        ),
                    "provenance":
                        deepcopy(
                            umbra.get(
                                "provenance"
                            )
                        ),
                    "validity":
                        deepcopy(
                            umbra.get(
                                "validity"
                            )
                        ),
                }
            )

        rows.sort(
            key=lambda row: (
                str(
                    row[
                        "definition"
                    ]
                    or ""
                ),
                row[
                    "relation"
                ],
                row[
                    "umbra_id"
                ],
            )
        )

        projection = {
            "schema":
                "savant.straub."
                "effective-metadata-isotope.v1",
            "kind":
                "isotope",
            "subject":
                subject_id,
            "at":
                moment.isoformat() if moment is not None else None,
            "metadata_count":
                len(
                    rows
                ),
            "metadata":
                rows,
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

    def search(
        self,
        spec: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        query = dict(
            spec
            or {}
        )

        ids = _string_set(
            query.get(
                "ids"
            )
        )

        kinds = _string_set(
            query.get(
                "kinds"
            )
        )

        confidence_in = _string_set(
            query.get(
                "provenance_confidence_in"
            )
        )

        dependency_any = _string_set(
            query.get(
                "dependency_any"
            )
        )

        dependency_all = _string_set(
            query.get(
                "dependency_all"
            )
        )

        metadata_definitions = (
            _string_set(
                query.get(
                    "metadata_definition_in"
                )
            )
        )

        metadata_relations = (
            _string_set(
                query.get(
                    "metadata_relation_in"
                )
            )
        )

        authority_filter_enabled = (
            "authority_equals"
            in query
        )

        authority_equals = deepcopy(
            query.get(
                "authority_equals"
            )
        )

        moment = _instant(
            query.get(
                "at"
            )
        )

        include_invalid = bool(
            query.get(
                "include_invalid",
                False,
            )
        )

        results: list[
            dict[str, Any]
        ] = []

        for instance_id in sorted(
            self._instances
        ):
            record = self._instances[
                instance_id
            ]

            if (
                ids
                and instance_id
                not in ids
            ):
                continue

            kind = str(
                record.get(
                    "kind"
                )
                or ""
            )

            if (
                kinds
                and kind
                not in kinds
            ):
                continue

            if (
                not include_invalid
                and not _record_valid_at(
                    record,
                    moment,
                )
            ):
                continue

            if (
                authority_filter_enabled
                and record.get(
                    "authority"
                )
                != authority_equals
            ):
                continue

            provenance = record.get(
                "provenance"
            )

            if not isinstance(
                provenance,
                Mapping,
            ):
                provenance = {}

            confidence = str(
                provenance.get(
                    "confidence"
                )
                or ""
            )

            if (
                confidence_in
                and confidence
                not in confidence_in
            ):
                continue

            dependencies = set(
                str(
                    value
                ).strip()
                for value
                in (
                    record.get(
                        "dependencies"
                    )
                    or []
                )
                if str(
                    value
                ).strip()
            )

            if (
                dependency_any
                and not (
                    dependencies
                    & dependency_any
                )
            ):
                continue

            if (
                dependency_all
                and not dependency_all
                .issubset(
                    dependencies
                )
            ):
                continue

            metadata = (
                self.effective_metadata(
                    instance_id,
                    at=moment,
                    relation_in=(
                        sorted(
                            metadata_relations
                        )
                        if metadata_relations
                        else None
                    ),
                    definition_in=(
                        sorted(
                            metadata_definitions
                        )
                        if metadata_definitions
                        else None
                    ),
                )
            )

            if (
                metadata_definitions
                or metadata_relations
            ):
                if (
                    metadata[
                        "metadata_count"
                    ]
                    == 0
                ):
                    continue

            results.append(
                {
                    "id":
                        instance_id,
                    "kind":
                        kind,
                    "digest":
                        record.get(
                            "digest"
                        ),
                    "authority":
                        deepcopy(
                            record.get(
                                "authority"
                            )
                        ),
                    "provenance":
                        deepcopy(
                            provenance
                        ),
                    "dependencies":
                        sorted(
                            dependencies
                        ),
                    "metadata_count":
                        metadata[
                            "metadata_count"
                        ],
                }
            )

        projection = {
            "schema":
                "savant.straub.query-isotope.v1",
            "kind":
                "isotope",
            "query":
                deepcopy(
                    query
                ),
            "at":
                moment.isoformat() if moment is not None else None,
            "result_count":
                len(
                    results
                ),
            "results":
                results,
            "projection_only":
                True,
            "authority_interpretation":
                "exact_only",
            "authority_effect":
                "none",
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection
