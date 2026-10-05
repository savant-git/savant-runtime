#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping

from .model import (
    StraubValidationError,
    content_digest,
)


schema = "savant.straub.query.v2"
owner = "savant"
authority_effect = "none"

_UNSET = object()


def _parse_instant(
    value: Any,
) -> datetime | None:
    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        parsed = value
    elif isinstance(
        value,
        str,
    ):
        candidate = value.strip()

        if not candidate:
            raise StraubValidationError(
                "temporal instant cannot be blank"
            )

        if candidate.endswith("Z"):
            candidate = (
                candidate[:-1]
                + "+00:00"
            )

        try:
            parsed = datetime.fromisoformat(
                candidate
            )
        except ValueError as exc:
            raise StraubValidationError(
                "invalid temporal instant"
            ) from exc
    else:
        raise StraubValidationError(
            "temporal instant must be "
            "an iso datetime or null"
        )

    if parsed.tzinfo is None:
        raise StraubValidationError(
            "temporal instant must include "
            "a timezone"
        )

    return parsed


def _instant_text(
    value: datetime | None,
) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _record_valid_at(
    record: Mapping[str, Any],
    instant: datetime | None,
) -> bool:
    if instant is None:
        return True

    validity = record.get(
        "validity"
    )

    if validity is None:
        return True

    if not isinstance(
        validity,
        Mapping,
    ):
        raise StraubValidationError(
            "record validity must be "
            "an object"
        )

    valid_from_raw = validity.get(
        "valid_from"
    )

    valid_until_raw = validity.get(
        "valid_until"
    )

    valid_from = (
        _parse_instant(
            valid_from_raw
        )
        if valid_from_raw is not None
        else None
    )

    valid_until = (
        _parse_instant(
            valid_until_raw
        )
        if valid_until_raw is not None
        else None
    )

    if (
        valid_from is not None
        and instant < valid_from
    ):
        return False

    if (
        valid_until is not None
        and instant >= valid_until
    ):
        return False

    return True


def _confidence(
    record: Mapping[str, Any],
) -> Any:
    provenance = record.get(
        "provenance"
    )

    if not isinstance(
        provenance,
        Mapping,
    ):
        return None

    return provenance.get(
        "confidence"
    )


def _dependencies(
    record: Mapping[str, Any],
) -> set[str]:
    raw = record.get(
        "dependencies"
    )

    if not isinstance(
        raw,
        list,
    ):
        return set()

    return {
        str(item)
        for item in raw
        if str(item).strip()
    }


class StraubQuery:
    def __init__(
        self,
        capsule: Mapping[str, Any],
    ) -> None:
        if not isinstance(
            capsule,
            Mapping,
        ):
            raise StraubValidationError(
                "query requires straub capsule"
            )

        if (
            capsule.get(
                "schema"
            )
            != "savant.straub.capsule.v2"
        ):
            raise StraubValidationError(
                "query requires capsule v2"
            )

        self._capsule = deepcopy(
            dict(
                capsule
            )
        )

        self._source_digest = str(
            capsule.get(
                "digest"
            )
            or ""
        )

        if not self._source_digest:
            raise StraubValidationError(
                "capsule digest missing"
            )

        instances = capsule.get(
            "instances"
        )

        membranes = capsule.get(
            "membranes"
        )

        if not isinstance(
            instances,
            list,
        ):
            raise StraubValidationError(
                "capsule instances invalid"
            )

        if not isinstance(
            membranes,
            list,
        ):
            raise StraubValidationError(
                "capsule membranes invalid"
            )

        self._instances: dict[
            str,
            dict[str, Any],
        ] = {}

        self._membranes: dict[
            str,
            dict[str, Any],
        ] = {}

        for raw in instances:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "instance record invalid"
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
                    "instance id missing"
                )

            self._instances[
                record_id
            ] = record

        for raw in membranes:
            if not isinstance(
                raw,
                Mapping,
            ):
                raise StraubValidationError(
                    "membrane record invalid"
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
                    "membrane id missing"
                )

            self._membranes[
                record_id
            ] = record

    @property
    def source_digest(
        self,
    ) -> str:
        return self._source_digest

    def effective_metadata(
        self,
        subject_id: str,
        *,
        at: Any = None,
        relation: str | None = None,
        definition: str | None = None,
        definition_id: str | None = None,
        authority_equals: Any = _UNSET,
    ) -> dict[str, Any]:
        subject_id = str(
            subject_id
        ).strip()

        if not subject_id:
            raise StraubValidationError(
                "metadata subject id required"
            )

        if (
            definition is not None
            and definition_id is not None
            and definition != definition_id
        ):
            raise StraubValidationError(
                "conflicting metadata "
                "definition filters"
            )

        definition_filter = (
            definition
            if definition is not None
            else definition_id
        )

        instant = _parse_instant(
            at
        )

        rows: list[
            dict[str, Any]
        ] = []

        for membrane_id in sorted(
            self._membranes
        ):
            membrane = self._membranes[
                membrane_id
            ]

            if (
                str(
                    membrane.get(
                        "from"
                    )
                    or ""
                )
                != subject_id
            ):
                continue

            if (
                relation is not None
                and membrane.get(
                    "relation"
                )
                != relation
            ):
                continue

            if not _record_valid_at(
                membrane,
                instant,
            ):
                continue

            target_id = str(
                membrane.get(
                    "to"
                )
                or ""
            )

            target = self._instances.get(
                target_id
            )

            if target is None:
                continue

            if (
                target.get(
                    "kind"
                )
                != "umbra.value"
            ):
                continue

            if not _record_valid_at(
                target,
                instant,
            ):
                continue

            payload = target.get(
                "payload"
            )

            if not isinstance(
                payload,
                Mapping,
            ):
                continue

            target_definition = str(
                payload.get(
                    "definition"
                )
                or ""
            )

            if (
                definition_filter is not None
                and target_definition
                != definition_filter
            ):
                continue

            if (
                authority_equals
                is not _UNSET
                and target.get(
                    "authority"
                )
                != authority_equals
            ):
                continue

            rows.append(
                {
                    "membrane_id":
                        membrane_id,
                    "relation":
                        membrane.get(
                            "relation"
                        ),
                    "umbra_id":
                        target_id,
                    "definition":
                        target_definition,
                    "value":
                        deepcopy(
                            payload.get(
                                "value"
                            )
                        ),
                    "authority":
                        deepcopy(
                            target.get(
                                "authority"
                            )
                        ),
                    "validity": deepcopy(
                        target.get(
                            "validity"
                        )
                    ),
                    "provenance":
                        deepcopy(
                            target.get(
                                "provenance"
                            )
                        ),
                }
            )

        projection = {
            "schema":
                "savant.straub."
                "effective-metadata-isotope.v2",
            "kind":
                "isotope",
            "subject":
                subject_id,
            "at":
                _instant_text(
                    instant
                ),
            "relation":
                relation,
            "definition":
                definition_filter,
            "authority_filter":
                (
                    None
                    if authority_equals
                    is _UNSET
                    else deepcopy(
                        authority_equals
                    )
                ),
            "authority_interpretation":
                "exact_only",
            "count":
                len(
                    rows
                ),
            "metadata":
                rows,
            "source_capsule_digest":
                self._source_digest,
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
        spec: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if spec is None:
            spec = {}

        if not isinstance(
            spec,
            Mapping,
        ):
            raise StraubValidationError(
                "query specification "
                "must be an object"
            )

        ids = {
            str(item)
            for item in (
                spec.get(
                    "ids"
                )
                or []
            )
        }

        kinds = {
            str(item)
            for item in (
                spec.get(
                    "kinds"
                )
                or []
            )
        }

        dependency_any = {
            str(item)
            for item in (
                spec.get(
                    "dependency_any"
                )
                or []
            )
        }

        dependency_all = {
            str(item)
            for item in (
                spec.get(
                    "dependency_all"
                )
                or []
            )
        }

        confidence_in = set(
            spec.get(
                "provenance_confidence_in"
            )
            or []
        )

        metadata_definition_in = {
            str(item)
            for item in (
                spec.get(
                    "metadata_definition_in"
                )
                or []
            )
        }

        metadata_relation_in = {
            str(item)
            for item in (
                spec.get(
                    "metadata_relation_in"
                )
                or []
            )
        }

        authority_filter_present = (
            "authority_equals"
            in spec
        )

        authority_equals = spec.get(
            "authority_equals"
        )

        include_invalid = bool(
            spec.get(
                "include_invalid",
                False,
            )
        )

        instant = _parse_instant(
            spec.get(
                "at"
            )
        )

        metadata_subjects: set[str] | None = (
            None
        )

        if (
            metadata_definition_in
            or metadata_relation_in
        ):
            metadata_subjects = set()

            for membrane in self._membranes.values():
                if (
                    not include_invalid
                    and not _record_valid_at(
                        membrane,
                        instant,
                    )
                ):
                    continue

                relation = str(
                    membrane.get(
                        "relation"
                    )
                    or ""
                )

                if (
                    metadata_relation_in
                    and relation
                    not in metadata_relation_in
                ):
                    continue

                target_id = str(
                    membrane.get(
                        "to"
                    )
                    or ""
                )

                target = self._instances.get(
                    target_id
                )

                if target is None:
                    continue

                if (
                    target.get(
                        "kind"
                    )
                    != "umbra.value"
                ):
                    continue

                if (
                    not include_invalid
                    and not _record_valid_at(
                        target,
                        instant,
                    )
                ):
                    continue

                payload = target.get(
                    "payload"
                )

                if not isinstance(
                    payload,
                    Mapping,
                ):
                    continue

                definition_id = str(
                    payload.get(
                        "definition"
                    )
                    or ""
                )

                if (
                    metadata_definition_in
                    and definition_id
                    not in metadata_definition_in
                ):
                    continue

                source_id = str(
                    membrane.get(
                        "from"
                    )
                    or ""
                )

                if source_id:
                    metadata_subjects.add(
                        source_id
                    )

        results: list[
            dict[str, Any]
        ] = []

        for record_id in sorted(
            self._instances
        ):
            record = self._instances[
                record_id
            ]

            if ids and record_id not in ids:
                continue

            if (
                kinds
                and str(
                    record.get(
                        "kind"
                    )
                    or ""
                )
                not in kinds
            ):
                continue

            if (
                authority_filter_present
                and record.get(
                    "authority"
                )
                != authority_equals
            ):
                continue

            if (
                confidence_in
                and _confidence(
                    record
                )
                not in confidence_in
            ):
                continue

            dependencies = _dependencies(
                record
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
                and not dependency_all.issubset(
                    dependencies
                )
            ):
                continue

            if (
                metadata_subjects
                is not None
                and record_id
                not in metadata_subjects
            ):
                continue

            if (
                not include_invalid
                and not _record_valid_at(
                    record,
                    instant,
                )
            ):
                continue

            results.append(
                deepcopy(
                    record
                )
            )

        projection = {
            "schema":
                "savant.straub."
                "query-isotope.v2",
            "kind":
                "isotope",
            "spec":
                deepcopy(
                    dict(
                        spec
                    )
                ),
            "at":
                _instant_text(
                    instant
                ),
            "authority_interpretation":
                "exact_only",
            "result_count":
                len(
                    results
                ),
            "results":
                results,
            "source_capsule_digest":
                self._source_digest,
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
