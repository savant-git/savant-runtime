#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from .composition import (
    composition,
    definition_group,
    project_effective_definitions,
    validate_value,
)
from .model import (
    StraubConflictError,
    StraubValidationError,
    content_digest,
    dyad,
    membrane,
    normalize_instance,
    umbra_definition,
    umbra_value,
)


schema = "savant.straub.registry.v2"
owner = "savant"
authority_effect = "none"


def _instant(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    text = str(
        value
    ).strip()

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    parsed = datetime.fromisoformat(
        text
    )

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed


def _valid_at(
    record: Mapping[str, Any],
    at: datetime,
) -> bool:
    validity = record.get(
        "validity"
    )

    if not isinstance(
        validity,
        Mapping,
    ):
        return True

    start = _instant(
        validity.get(
            "valid_from"
        )
    )

    end = _instant(
        validity.get(
            "valid_until"
        )
    )

    if (
        start is not None
        and at < start
    ):
        return False

    if (
        end is not None
        and at >= end
    ):
        return False

    return True


class StraubRegistry:
    def __init__(
        self,
    ) -> None:
        self._instances: dict[
            str,
            dict[str, Any],
        ] = {}

        self._membranes: dict[
            str,
            dict[str, Any],
        ] = {}

        self._outgoing: dict[
            str,
            list[str],
        ] = {}

        self._incoming: dict[
            str,
            list[str],
        ] = {}

    def _index_membrane(
        self,
        record: Mapping[str, Any],
    ) -> None:
        source = str(
            record[
                "from"
            ]
        )

        target = str(
            record[
                "to"
            ]
        )

        membrane_id = str(
            record[
                "id"
            ]
        )

        self._outgoing.setdefault(
            source,
            [],
        )

        self._incoming.setdefault(
            target,
            [],
        )

        if (
            membrane_id
            not in self._outgoing[
                source
            ]
        ):
            self._outgoing[
                source
            ].append(
                membrane_id
            )

            self._outgoing[
                source
            ].sort()

        if (
            membrane_id
            not in self._incoming[
                target
            ]
        ):
            self._incoming[
                target
            ].append(
                membrane_id
            )

            self._incoming[
                target
            ].sort()

    def substantiate(
        self,
        value: Mapping[str, Any],
    ) -> dict[str, Any]:
        record = normalize_instance(
            value
        )

        instance_id = record[
            "id"
        ]

        existing = self._instances.get(
            instance_id
        )

        if existing is not None:
            if (
                existing[
                    "digest"
                ]
                != record[
                    "digest"
                ]
            ):
                raise StraubConflictError(
                    "instance identity already "
                    "contains different substance: "
                    f"{instance_id}"
                )

            return deepcopy(
                existing
            )

        self._instances[
            instance_id
        ] = deepcopy(
            record
        )

        return deepcopy(
            record
        )

    def define_metadata(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.substantiate(
            umbra_definition(
                **kwargs
            )
        )

    def define_group(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        candidate = definition_group(
            **kwargs
        )

        definitions = (
            candidate[
                "payload"
            ][
                "definitions"
            ]
        )

        for definition_id in definitions:
            definition = (
                self._instances.get(
                    definition_id
                )
            )

            if definition is None:
                raise StraubValidationError(
                    "umbra definition does not exist: "
                    f"{definition_id}"
                )

            if (
                definition.get(
                    "kind"
                )
                != "umbra.definition"
            ):
                raise StraubValidationError(
                    "umbra group member is not "
                    "umbra.definition: "
                    f"{definition_id}"
                )

        return self.substantiate(
            candidate
        )

    def define_composition(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        candidate = composition(
            **kwargs
        )

        payload = candidate[
            "payload"
        ]

        for group_id in payload[
            "groups"
        ]:
            group = self._instances.get(
                group_id
            )

            if group is None:
                raise StraubValidationError(
                    "umbra group does not exist: "
                    f"{group_id}"
                )

            if (
                group.get(
                    "kind"
                )
                != "umbra.group"
            ):
                raise StraubValidationError(
                    "composition group reference "
                    "is not umbra.group"
                )

        for definition_id in payload[
            "definitions"
        ]:
            definition = (
                self._instances.get(
                    definition_id
                )
            )

            if definition is None:
                raise StraubValidationError(
                    "umbra definition does not exist: "
                    f"{definition_id}"
                )

            if (
                definition.get(
                    "kind"
                )
                != "umbra.definition"
            ):
                raise StraubValidationError(
                    "composition definition reference "
                    "is not umbra.definition"
                )

        return self.substantiate(
            candidate
        )

    def effective_definitions(
        self,
        composition_id: str,
    ) -> dict[str, Any]:
        record = self._instances.get(
            composition_id
        )

        if record is None:
            raise StraubValidationError(
                "umbra composition does not exist: "
                f"{composition_id}"
            )

        return project_effective_definitions(
            composition_record=record,
            instances=self._instances,
        )

    def instantiate_metadata(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        definition_id = str(
            kwargs.get(
                "definition_id"
            )
            or ""
        )

        definition = (
            self._instances.get(
                definition_id
            )
        )

        if definition is None:
            raise StraubValidationError(
                "metadata definition does not exist: "
                f"{definition_id}"
            )

        if (
            definition.get(
                "kind"
            )
            != "umbra.definition"
        ):
            raise StraubValidationError(
                "metadata definition reference "
                "does not identify umbra.definition"
            )

        payload = definition.get(
            "payload"
        )

        if not isinstance(
            payload,
            Mapping,
        ):
            raise StraubValidationError(
                "metadata definition payload missing"
            )

        validate_value(
            value=kwargs.get(
                "value"
            ),
            value_type=str(
                payload.get(
                    "value_type"
                )
                or "any"
            ),
        )

        return self.substantiate(
            umbra_value(
                **kwargs
            )
        )

    def attach_metadata(
        self,
        *,
        membrane_id: str,
        subject_id: str,
        umbra_id: str,
        relation: str = "described_by",
        provenance: Mapping[
            str,
            Any,
        ] | None = None,
        lineage: Mapping[
            str,
            Any,
        ] | None = None,
        validity: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        subject = self._instances.get(
            subject_id
        )

        if subject is None:
            raise StraubValidationError(
                "subject instance does not exist: "
                f"{subject_id}"
            )

        umbra_record = (
            self._instances.get(
                umbra_id
            )
        )

        if umbra_record is None:
            raise StraubValidationError(
                "umbra instance does not exist: "
                f"{umbra_id}"
            )

        if not str(
            umbra_record.get(
                "kind"
            )
            or ""
        ).startswith(
            "umbra."
        ):
            raise StraubValidationError(
                "metadata target must be "
                "an umbra instance"
            )

        record = membrane(
            membrane_id=membrane_id,
            subject_id=subject_id,
            umbra_id=umbra_id,
            relation=relation,
            provenance=provenance,
            lineage=lineage,
            validity=validity,
        )

        existing = self._membranes.get(
            membrane_id
        )

        if existing is not None:
            if (
                existing[
                    "digest"
                ]
                != record[
                    "digest"
                ]
            ):
                raise StraubConflictError(
                    "membrane identity already "
                    "contains different substance: "
                    f"{membrane_id}"
                )

            return deepcopy(
                existing
            )

        self._membranes[
            membrane_id
        ] = deepcopy(
            record
        )

        self._index_membrane(
            record
        )

        return deepcopy(
            record
        )

    def instance(
        self,
        instance_id: str,
    ) -> dict[str, Any]:
        record = self._instances.get(
            instance_id
        )

        if record is None:
            raise KeyError(
                instance_id
            )

        return deepcopy(
            record
        )

    def membrane(
        self,
        membrane_id: str,
    ) -> dict[str, Any]:
        record = self._membranes.get(
            membrane_id
        )

        if record is None:
            raise KeyError(
                membrane_id
            )

        return deepcopy(
            record
        )

    def dyad(
        self,
        membrane_id: str,
    ) -> dict[str, Any]:
        edge = self.membrane(
            membrane_id
        )

        return dyad(
            subject=self.instance(
                edge[
                    "from"
                ]
            ),
            umbra=self.instance(
                edge[
                    "to"
                ]
            ),
            membrane_record=edge,
        )

    def metadata_for(
        self,
        subject_id: str,
        *,
        at: datetime | None = None,
        relation: str | None = None,
    ) -> list[dict[str, Any]]:
        if (
            subject_id
            not in self._instances
        ):
            raise KeyError(
                subject_id
            )

        moment = (
            at
            or datetime.now(
                timezone.utc
            )
        )

        result: list[
            dict[str, Any]
        ] = []

        for membrane_id in (
            self._outgoing.get(
                subject_id,
                [],
            )
        ):
            edge = self._membranes[
                membrane_id
            ]

            if (
                relation is not None
                and edge.get(
                    "relation"
                )
                != relation
            ):
                continue

            if not _valid_at(
                edge,
                moment,
            ):
                continue

            umbra_record = (
                self._instances[
                    edge[
                        "to"
                    ]
                ]
            )

            if not _valid_at(
                umbra_record,
                moment,
            ):
                continue

            result.append(
                {
                    "dyad":
                        dyad(
                            subject=(
                                self._instances[
                                    subject_id
                                ]
                            ),
                            umbra=(
                                umbra_record
                            ),
                            membrane_record=(
                                edge
                            ),
                        ),
                    "umbra":
                        deepcopy(
                            umbra_record
                        ),
                    "membrane":
                        deepcopy(
                            edge
                        ),
                }
            )

        result.sort(
            key=lambda row: (
                row[
                    "membrane"
                ][
                    "relation"
                ],
                row[
                    "umbra"
                ][
                    "id"
                ],
            )
        )

        return result

    def radia(
        self,
        *,
        subject_id: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, Any]:
        moment = (
            at
            or datetime.now(
                timezone.utc
            )
        )

        if subject_id is not None:
            subject_ids = [
                subject_id
            ]
        else:
            subject_ids = sorted(
                self._instances
            )

        subjects: list[
            dict[str, Any]
        ] = []

        for current_id in subject_ids:
            if (
                current_id
                not in self._instances
            ):
                raise KeyError(
                    current_id
                )

            record = self._instances[
                current_id
            ]

            if not _valid_at(
                record,
                moment,
            ):
                continue

            metadata_rows = (
                self.metadata_for(
                    current_id,
                    at=moment,
                )
            )

            subjects.append(
                {
                    "id":
                        current_id,
                    "kind":
                        record[
                            "kind"
                        ],
                    "instance_digest":
                        record[
                            "digest"
                        ],
                    "metadata":
                        [
                            {
                                "umbra_id":
                                    row[
                                        "umbra"
                                    ][
                                        "id"
                                    ],
                                "umbra_kind":
                                    row[
                                        "umbra"
                                    ][
                                        "kind"
                                    ],
                                "definition":
                                    (
                                        row[
                                            "umbra"
                                        ]
                                        .get(
                                            "payload",
                                            {},
                                        )
                                        .get(
                                            "definition"
                                        )
                                    ),
                                "value":
                                    (
                                        row[
                                            "umbra"
                                        ]
                                        .get(
                                            "payload",
                                            {},
                                        )
                                        .get(
                                            "value"
                                        )
                                    ),
                                "relation":
                                    row[
                                        "membrane"
                                    ][
                                        "relation"
                                    ],
                                "membrane":
                                    row[
                                        "membrane"
                                    ][
                                        "id"
                                    ],
                            }
                            for row
                            in metadata_rows
                        ],
                }
            )

        projection = {
            "schema":
                "savant.straub.radia.v1",
            "kind":
                "radia",
            "projection_only":
                True,
            "authority_effect":
                "none",
            "subject_count":
                len(
                    subjects
                ),
            "subjects":
                subjects,
        }

        projection[
            "digest"
        ] = content_digest(
            projection
        )

        return projection

    def export_capsule(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema":
                "savant.straub.capsule.v1",
            "instances":
                [
                    deepcopy(
                        self._instances[
                            instance_id
                        ]
                    )
                    for instance_id
                    in sorted(
                        self._instances
                    )
                ],
            "membranes":
                [
                    deepcopy(
                        self._membranes[
                            membrane_id
                        ]
                    )
                    for membrane_id
                    in sorted(
                        self._membranes
                    )
                ],
            "projection_only":
                False,
            "storage_engine":
                None,
            "authority_effect":
                "none",
        }

        payload[
            "digest"
        ] = content_digest(
            payload
        )

        return payload

    @classmethod
    def from_capsule(
        cls,
        capsule: Mapping[str, Any],
    ) -> "StraubRegistry":
        if (
            capsule.get(
                "schema"
            )
            != "savant.straub.capsule.v1"
        ):
            raise StraubValidationError(
                "unsupported straub capsule"
            )

        supplied_digest = str(
            capsule.get(
                "digest"
            )
            or ""
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

        if (
            supplied_digest
            != content_digest(
                unsigned
            )
        ):
            raise StraubValidationError(
                "straub capsule digest mismatch"
            )

        registry = cls()

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
                "straub capsule instances invalid"
            )

        if not isinstance(
            membranes,
            list,
        ):
            raise StraubValidationError(
                "straub capsule membranes invalid"
            )

        for record in instances:
            if not isinstance(
                record,
                Mapping,
            ):
                raise StraubValidationError(
                    "straub capsule instance invalid"
                )

            normalized = (
                normalize_instance(
                    record
                )
            )

            if (
                normalized[
                    "digest"
                ]
                != record.get(
                    "digest"
                )
            ):
                raise StraubValidationError(
                    "straub instance digest mismatch"
                )

            registry._instances[
                normalized[
                    "id"
                ]
            ] = deepcopy(
                normalized
            )

        for record in membranes:
            if not isinstance(
                record,
                Mapping,
            ):
                raise StraubValidationError(
                    "straub capsule membrane invalid"
                )

            rebuilt = membrane(
                membrane_id=str(
                    record.get(
                        "id"
                    )
                    or ""
                ),
                subject_id=str(
                    record.get(
                        "from"
                    )
                    or ""
                ),
                umbra_id=str(
                    record.get(
                        "to"
                    )
                    or ""
                ),
                relation=str(
                    record.get(
                        "relation"
                    )
                    or "described_by"
                ),
                provenance=record.get(
                    "provenance"
                ),
                lineage=record.get(
                    "lineage"
                ),
                validity=record.get(
                    "validity"
                ),
            )

            if (
                rebuilt[
                    "digest"
                ]
                != record.get(
                    "digest"
                )
            ):
                raise StraubValidationError(
                    "straub membrane digest mismatch"
                )

            if (
                rebuilt[
                    "from"
                ]
                not in registry._instances
                or rebuilt[
                    "to"
                ]
                not in registry._instances
            ):
                raise StraubValidationError(
                    "straub membrane references "
                    "missing instance"
                )

            registry._membranes[
                rebuilt[
                    "id"
                ]
            ] = deepcopy(
                rebuilt
            )

            registry._index_membrane(
                rebuilt
            )

        return registry

    def health(
        self,
    ) -> dict[str, Any]:
        kinds: dict[str, int] = {}

        for record in (
            self._instances.values()
        ):
            kind = str(
                record.get(
                    "kind"
                )
                or "unknown"
            )

            kinds[
                kind
            ] = (
                kinds.get(
                    kind,
                    0,
                )
                + 1
            )

        return {
            "schema":
                schema,
            "owner":
                owner,
            "status":
                "ok",
            "instance_count":
                len(
                    self._instances
                ),
            "membrane_count":
                len(
                    self._membranes
                ),
            "instance_kinds":
                dict(
                    sorted(
                        kinds.items()
                    )
                ),
            "storage_engine":
                None,
            "persistence_bound":
                False,
            "replay_capsule":
                True,
            "metadata_composition":
                True,
            "recursive_metadata":
                True,
            "projection_term":
                "radia",
            "authority_effect":
                authority_effect,
        }
