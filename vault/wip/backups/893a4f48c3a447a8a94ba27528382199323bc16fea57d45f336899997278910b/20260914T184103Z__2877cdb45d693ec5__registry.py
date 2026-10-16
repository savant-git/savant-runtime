#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

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


schema = "savant.straub.registry.v1"
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
            membrane_id=(
                membrane_id
            ),
            subject_id=(
                subject_id
            ),
            umbra_id=(
                umbra_id
            ),
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

        for membrane_id in self._outgoing.get(
            subject_id,
            [],
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

    def health(
        self,
    ) -> dict[str, Any]:
        umbra_definitions = sum(
            1
            for record
            in self._instances.values()
            if (
                record.get(
                    "kind"
                )
                == "umbra.definition"
            )
        )

        umbra_values = sum(
            1
            for record
            in self._instances.values()
            if (
                record.get(
                    "kind"
                )
                == "umbra.value"
            )
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
            "umbra_definition_count":
                umbra_definitions,
            "umbra_value_count":
                umbra_values,
            "storage_engine":
                None,
            "persistence_bound":
                False,
            "projection_term":
                "radia",
            "projection_only":
                True,
            "authority_effect":
                authority_effect,
        }
