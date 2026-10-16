#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .datrix import StraubDatrix
from .datrix_profiles import compose_profiles, validate_profile_names
from .datrix_services import DatrixProjectionError
from .model import StraubValidationError


schema = "savant.carbon.straub.datrix-interface.v1"
owner = "carbon"
module = "straub"
authority_effect = "none"

exact_source_recovery = False
reconstruction_basis = (
    "verified behavioral contract and current straub runtime"
)

MAX_LIMIT = 100000


class DatrixInterfaceError(ValueError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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


def _path_value(
    value: Any,
    path: str,
) -> Any:
    current = value

    for part in str(
        path
    ).split(
        "."
    ):
        if not part:
            continue

        if isinstance(
            current,
            Mapping,
        ):
            current = current.get(
                part
            )

        elif (
            isinstance(
                current,
                Sequence,
            )
            and not isinstance(
                current,
                (
                    str,
                    bytes,
                    bytearray,
                ),
            )
        ):
            try:
                current = current[
                    int(
                        part
                    )
                ]

            except (
                ValueError,
                IndexError,
            ):
                return None

        else:
            return None

    return current


def _contains(
    container: Any,
    expected: Any,
) -> bool:
    if isinstance(
        container,
        str,
    ):
        return (
            str(
                expected
            )
            in container
        )

    if isinstance(
        container,
        Mapping,
    ):
        return (
            expected
            in container
        )

    if (
        isinstance(
            container,
            Sequence,
        )
        and not isinstance(
            container,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        return (
            expected
            in container
        )

    return False


def _matches(
    record: Mapping[
        str,
        Any,
    ],
    clause: Mapping[
        str,
        Any,
    ],
) -> bool:
    path = str(
        clause.get(
            "path"
        )
        or ""
    ).strip()

    op = str(
        clause.get(
            "op"
        )
        or "eq"
    ).strip().casefold()

    expected = clause.get(
        "value"
    )

    if not path:
        raise DatrixInterfaceError(
            "where.path is required"
        )

    actual = _path_value(
        record,
        path,
    )

    if op == "eq":
        return (
            actual
            == expected
        )

    if op == "ne":
        return (
            actual
            != expected
        )

    if op == "exists":
        return (
            (
                actual
                is not None
            )
            == bool(
                expected
            )
        )

    if op == "contains":
        return _contains(
            actual,
            expected,
        )

    if op == "in":
        if (
            not isinstance(
                expected,
                Sequence,
            )
            or isinstance(
                expected,
                (
                    str,
                    bytes,
                    bytearray,
                ),
            )
        ):
            raise DatrixInterfaceError(
                "where.in requires "
                "a sequence value"
            )

        return (
            actual
            in expected
        )

    if op == "prefix":
        return (
            isinstance(
                actual,
                str,
            )
            and actual.startswith(
                str(
                    expected
                )
            )
        )

    if op == "gt":
        return (
            actual
            is not None
            and actual
            > expected
        )

    if op == "gte":
        return (
            actual
            is not None
            and actual
            >= expected
        )

    if op == "lt":
        return (
            actual
            is not None
            and actual
            < expected
        )

    if op == "lte":
        return (
            actual
            is not None
            and actual
            <= expected
        )

    raise DatrixInterfaceError(
        "unsupported where "
        f"operator: {op}"
    )


def _project_fields(
    record: Mapping[
        str,
        Any,
    ],
    fields: Iterable[
        str
    ],
) -> dict[
    str,
    Any,
]:
    selected = tuple(
        str(
            field
        ).strip()
        for field
        in fields
        if str(
            field
        ).strip()
    )

    if not selected:
        return deepcopy(
            dict(
                record
            )
        )

    return {
        field:
            deepcopy(
                _path_value(
                    record,
                    field,
                )
            )
        for field
        in selected
    }


def _sort_token(
    value: Any,
) -> tuple[
    int,
    Any,
]:
    if value is None:
        return (
            4,
            "",
        )

    if isinstance(
        value,
        bool,
    ):
        return (
            0,
            int(
                value
            ),
        )

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return (
            1,
            float(
                value
            ),
        )

    if isinstance(
        value,
        str,
    ):
        return (
            2,
            value,
        )

    return (
        3,
        canonical_json(
            value
        ),
    )


class DatrixInterface:
    """
    Compatibility surface over canonical
    StraubDatrix substance.
    """

    def __init__(
        self,
        datrix: StraubDatrix,
        profiles: (
            Iterable[
                str
            ]
            | str
            | None
        ) = None,
    ) -> None:
        self._datrix = datrix

        self._profiles = (
            validate_profile_names(
                profiles
            )
        )

        self._profile_composition = (
            compose_profiles(
                self._profiles
            )
        )

    @classmethod
    def open(
        cls,
        path: (
            str
            | Path
        ),
        profiles: (
            Iterable[
                str
            ]
            | str
            | None
        ) = None,
    ) -> "DatrixInterface":
        return cls(
            StraubDatrix.open(
                path
            ),
            profiles,
        )

    @property
    def datrix(
        self,
    ) -> StraubDatrix:
        return self._datrix

    @property
    def profiles(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._profiles

    def substantiate(
        self,
        value: Mapping[
            str,
            Any,
        ],
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            Mapping,
        ):
            raise DatrixInterfaceError(
                "substance must be "
                "an object"
            )

        return (
            self._datrix
            .registry
            .substantiate(
                value
            )
        )

    def relate(
        self,
        *,
        segue_id: str,
        source_id: str,
        target_id: str,
        relation: str,
        payload: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        provenance: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
    ) -> dict[
        str,
        Any,
    ]:
        for (
            identity,
            field,
        ) in (
            (
                source_id,
                "source_id",
            ),
            (
                target_id,
                "target_id",
            ),
        ):
            try:
                (
                    self._datrix
                    .registry
                    .instance(
                        identity
                    )
                )

            except KeyError as exc:
                raise (
                    DatrixInterfaceError(
                        f"{field} does "
                        "not exist: "
                        f"{identity}"
                    )
                ) from exc

        identity = str(
            segue_id
        ).strip()

        relation_name = str(
            relation
        ).strip()

        if not identity:
            raise DatrixInterfaceError(
                "segue_id is required"
            )

        if not relation_name:
            raise DatrixInterfaceError(
                "relation is required"
            )

        return (
            self._datrix
            .registry
            .substantiate(
                {
                    "id":
                        identity,

                    "kind":
                        "segue",

                    "payload":
                        {
                            "from":
                                str(
                                    source_id
                                ).strip(),

                            "to":
                                str(
                                    target_id
                                ).strip(),

                            "relation":
                                relation_name,

                            "payload":
                                deepcopy(
                                    dict(
                                        payload
                                        or {}
                                    )
                                ),
                        },

                    "dependencies":
                        sorted(
                            {
                                str(
                                    source_id
                                ).strip(),

                                str(
                                    target_id
                                ).strip(),
                            }
                        ),

                    "provenance":
                        deepcopy(
                            dict(
                                provenance
                                or {}
                            )
                        ),

                    "lineage":
                        {},

                    "extensions":
                        {
                            "datrix_interface":
                                {
                                    "schema":
                                        schema,

                                    (
                                        "relationship_"
                                        "primitive"
                                    ):
                                        (
                                            "typed-"
                                            "segue"
                                        ),
                                }
                        },
                }
            )
        )

    def select(
        self,
        *,
        kinds: Iterable[
            str
        ] = (),
        where: Iterable[
            Mapping[
                str,
                Any,
            ]
        ] = (),
        order_by: str = "id",
        direction: str = "asc",
        limit: (
            int
            | None
        ) = None,
        fields: Iterable[
            str
        ] = (),
    ) -> dict[
        str,
        Any,
    ]:
        normalized_kinds = tuple(
            sorted(
                {
                    str(
                        kind
                    ).strip()
                    for kind
                    in kinds
                    if str(
                        kind
                    ).strip()
                }
            )
        )

        normalized_limit: (
            int
            | None
        )

        if limit is None:
            normalized_limit = None

        else:
            if (
                isinstance(
                    limit,
                    bool,
                )
                or int(
                    limit
                )
                < 0
            ):
                raise DatrixInterfaceError(
                    "limit must be a "
                    "non-negative integer"
                )

            normalized_limit = int(
                limit
            )

            if (
                normalized_limit
                > MAX_LIMIT
            ):
                raise DatrixInterfaceError(
                    "limit cannot exceed "
                    f"{MAX_LIMIT}"
                )

        direction_name = str(
            direction
            or "asc"
        ).strip().casefold()

        if direction_name not in {
            "asc",
            "desc",
        }:
            raise DatrixInterfaceError(
                "direction must be "
                "asc or desc"
            )

        query = (
            self._datrix
            .query()
            .search(
                {
                    "kinds":
                        list(
                            normalized_kinds
                        )
                }
            )
        )

        clauses = [
            dict(
                clause
            )
            for clause
            in where
        ]

        records = [
            record
            for record
            in query[
                "results"
            ]
            if all(
                _matches(
                    record,
                    clause,
                )
                for clause
                in clauses
            )
        ]

        order_path = str(
            order_by
            or "id"
        ).strip()

        records.sort(
            key=(
                lambda record:
                _sort_token(
                    _path_value(
                        record,
                        order_path,
                    )
                )
            ),
            reverse=(
                direction_name
                == "desc"
            ),
        )

        if (
            normalized_limit
            is not None
        ):
            records = records[
                :normalized_limit
            ]

        projected = [
            _project_fields(
                record,
                fields,
            )
            for record
            in records
        ]

        result = {
            "schema":
                (
                    "savant.carbon."
                    "straub.datrix-"
                    "interface-select.v1"
                ),

            "kind":
                "isotope",

            "profiles":
                list(
                    self._profiles
                ),

            "count":
                len(
                    projected
                ),

            "records":
                projected,

            "source_capsule_digest":
                self._datrix
                .capsule()[
                    "digest"
                ],

            "projection_only":
                True,

            "authoritative":
                False,

            "authority_effect":
                authority_effect,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def neighbors(
        self,
        source_id: str,
        *,
        relation: (
            str
            | None
        ) = None,
        direction: str = "both",
        depth: int = 1,
    ) -> dict[
        str,
        Any,
    ]:
        if (
            isinstance(
                depth,
                bool,
            )
            or int(
                depth
            )
            < 0
        ):
            raise DatrixInterfaceError(
                "depth must be a "
                "non-negative integer"
            )

        direction_name = str(
            direction
            or "both"
        ).strip().casefold()

        if direction_name not in {
            "out",
            "in",
            "both",
        }:
            raise DatrixInterfaceError(
                "direction must be "
                "out, in, or both"
            )

        try:
            (
                self._datrix
                .registry
                .instance(
                    source_id
                )
            )

        except KeyError as exc:
            raise (
                DatrixInterfaceError(
                    "source instance "
                    "does not exist: "
                    f"{source_id}"
                )
            ) from exc

        edges: list[
            dict[
                str,
                Any,
            ]
        ] = []

        segue_rows = (
            self._datrix
            .query()
            .search(
                {
                    "kinds":
                        [
                            "segue"
                        ]
                }
            )[
                "results"
            ]
        )

        for edge in segue_rows:
            payload = edge.get(
                "payload"
            )

            if not isinstance(
                payload,
                Mapping,
            ):
                continue

            edges.append(
                {
                    "record":
                        edge,

                    "id":
                        str(
                            edge.get(
                                "id"
                            )
                            or ""
                        ),

                    "from":
                        str(
                            payload.get(
                                "from"
                            )
                            or ""
                        ),

                    "to":
                        str(
                            payload.get(
                                "to"
                            )
                            or ""
                        ),

                    "relation":
                        str(
                            payload.get(
                                "relation"
                            )
                            or ""
                        ),
                }
            )

        capsule = (
            self._datrix
            .capsule()
        )

        for membrane in capsule.get(
            "membranes",
            [],
        ):
            if not isinstance(
                membrane,
                Mapping,
            ):
                continue

            edges.append(
                {
                    "record":
                        deepcopy(
                            dict(
                                membrane
                            )
                        ),

                    "id":
                        str(
                            membrane.get(
                                "id"
                            )
                            or ""
                        ),

                    "from":
                        str(
                            membrane.get(
                                "from"
                            )
                            or ""
                        ),

                    "to":
                        str(
                            membrane.get(
                                "to"
                            )
                            or ""
                        ),

                    "relation":
                        str(
                            membrane.get(
                                "relation"
                            )
                            or ""
                        ),
                }
            )

        visited = {
            str(
                source_id
            )
        }

        frontier = {
            str(
                source_id
            )
        }

        traversed: dict[
            str,
            dict[
                str,
                Any,
            ],
        ] = {}

        for _ in range(
            int(
                depth
            )
        ):
            next_frontier: set[
                str
            ] = set()

            for edge in edges:
                if (
                    relation
                    is not None
                    and edge[
                        "relation"
                    ]
                    != relation
                ):
                    continue

                targets: list[
                    str
                ] = []

                if (
                    direction_name
                    in {
                        "out",
                        "both",
                    }
                    and edge[
                        "from"
                    ]
                    in frontier
                ):
                    targets.append(
                        edge[
                            "to"
                        ]
                    )

                if (
                    direction_name
                    in {
                        "in",
                        "both",
                    }
                    and edge[
                        "to"
                    ]
                    in frontier
                ):
                    targets.append(
                        edge[
                            "from"
                        ]
                    )

                for target in targets:
                    if not target:
                        continue

                    if edge[
                        "id"
                    ]:
                        traversed[
                            edge[
                                "id"
                            ]
                        ] = deepcopy(
                            edge[
                                "record"
                            ]
                        )

                    if (
                        target
                        not in visited
                    ):
                        visited.add(
                            target
                        )

                        next_frontier.add(
                            target
                        )

            frontier = (
                next_frontier
            )

            if not frontier:
                break

        nodes: list[
            dict[
                str,
                Any,
            ]
        ] = []

        for identity in sorted(
            visited
        ):
            try:
                nodes.append(
                    self._datrix
                    .registry
                    .instance(
                        identity
                    )
                )

            except KeyError:
                continue

        result = {
            "schema":
                (
                    "savant.carbon."
                    "straub.datrix-"
                    "interface-neighbors.v1"
                ),

            "kind":
                "isotope",

            "source":
                str(
                    source_id
                ),

            "relation":
                relation,

            "direction":
                direction_name,

            "depth":
                int(
                    depth
                ),

            "nodes":
                nodes,

            "edges":
                [
                    traversed[
                        key
                    ]
                    for key
                    in sorted(
                        traversed
                    )
                ],

            "source_capsule_digest":
                self._datrix
                .capsule()[
                    "digest"
                ],

            "projection_only":
                True,

            "authoritative":
                False,

            "authority_effect":
                authority_effect,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result

    def project(
        self,
        projection_type: str,
    ) -> dict[
        str,
        Any,
    ]:
        requested = str(
            projection_type
            or ""
        ).strip()

        if not requested:
            raise DatrixInterfaceError(
                "projection type "
                "is required"
            )

        if (
            requested
            == "materialized-index"
        ):
            return (
                self._datrix
                .materialized_isotope()
            )

        if requested == "health":
            return (
                self._datrix
                .project_isotope(
                    projection=(
                        self.health()
                    ),

                    projection_type=(
                        "interface:health"
                    ),

                    provenance={
                        "source":
                            schema,

                        "authority_effect":
                            "none",
                    },
                )
            )

        if requested == "capsule":
            return (
                self._datrix
                .project_isotope(
                    projection=(
                        self._datrix
                        .capsule()
                    ),

                    projection_type=(
                        "interface:capsule"
                    ),

                    source_ids=[],

                    dependencies=[],

                    provenance={
                        "source":
                            schema,

                        (
                            "semantic_"
                            "authority"
                        ):
                            False,
                    },
                )
            )

        if requested.startswith(
            "service:"
        ):
            requested = (
                requested.split(
                    ":",
                    1,
                )[
                    1
                ]
            )

        try:
            return (
                self._datrix
                .project_service(
                    requested
                )
            )

        except (
            KeyError,
            ValueError,
            StraubValidationError,
            DatrixProjectionError,
        ) as exc:
            raise (
                DatrixInterfaceError(
                    "unsupported "
                    "projection type: "
                    f"{requested}"
                )
            ) from exc

    def checkpoint(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return (
            self._datrix
            .checkpoint()
        )

    def health(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        datrix_health = (
            self._datrix
            .health()
        )

        result = {
            "schema":
                schema,

            "status":
                datrix_health.get(
                    "status"
                ),

            "owner":
                owner,

            "module":
                module,

            "path":
                str(
                    self._datrix
                    .path
                ),

            "profiles":
                list(
                    self._profiles
                ),

            "profile_composition":
                deepcopy(
                    self._profile_composition
                ),

            "datrix":
                datrix_health,

            "storage_engine_selected":
                datrix_health.get(
                    "storage_engine_selected"
                ),

            "database_engine":
                datrix_health.get(
                    "database_engine"
                ),

            "exact_source_recovery":
                exact_source_recovery,

            "reconstruction_basis":
                reconstruction_basis,

            "authoritative":
                False,

            "authority_effect":
                authority_effect,
        }

        result[
            "digest"
        ] = digest(
            result
        )

        return result


def interface_manifest(
) -> dict[
    str,
    Any,
]:
    result = {
        "schema":
            schema,

        "owner":
            owner,

        "module":
            module,

        "kind":
            "datrix-standard-interface",

        "operations":
            [
                "open",
                "substantiate",
                "relate",
                "select",
                "neighbors",
                "project",
                "checkpoint",
                "health",
            ],

        "where_operators":
            [
                "eq",
                "ne",
                "exists",
                "contains",
                "in",
                "prefix",
                "gt",
                "gte",
                "lt",
                "lte",
            ],

        "profile_composition":
            True,

        "one_straub_substrate":
            True,

        "storage_engine_selected":
            False,

        "database_engine":
            None,

        "exact_source_recovery":
            exact_source_recovery,

        "reconstruction_basis":
            reconstruction_basis,

        "authoritative":
            False,

        "authority_effect":
            authority_effect,
    }

    result[
        "digest"
    ] = digest(
        result
    )

    return result


def manifest(
) -> dict[
    str,
    Any,
]:
    return (
        interface_manifest()
    )


def selftest(
) -> dict[
    str,
    Any,
]:
    with tempfile.TemporaryDirectory(
        prefix=(
            "straub-interface-test-"
        )
    ) as directory:
        interface = (
            DatrixInterface.open(
                (
                    Path(
                        directory
                    )
                    / "interface.datrix"
                ),
                (
                    "knowledge",
                    "workflow",
                ),
            )
        )

        first_value = {
            "id":
                "instance:test:first",

            "kind":
                "example",

            "payload":
                {
                    "name":
                        "alpha",

                    "score":
                        10,
                },

            "provenance":
                {
                    "source":
                        "interface-selftest",

                    "confidence":
                        "confirmed",
                },
        }

        first = (
            interface.substantiate(
                first_value
            )
        )

        second = (
            interface.substantiate(
                {
                    "id":
                        "instance:test:second",

                    "kind":
                        "example",

                    "payload":
                        {
                            "name":
                                "beta",

                            "score":
                                20,
                        },

                    "provenance":
                        {
                            "source":
                                "interface-selftest",

                            "confidence":
                                "confirmed",
                        },
                }
            )
        )

        repeated = (
            interface.substantiate(
                first_value
            )
        )

        edge = interface.relate(
            segue_id=(
                "segue:test:"
                "first-second"
            ),

            source_id=(
                first[
                    "id"
                ]
            ),

            target_id=(
                second[
                    "id"
                ]
            ),

            relation=(
                "precedes"
            ),

            payload={
                "weight":
                    1,
            },

            provenance={
                "source":
                    "interface-selftest",

                "confidence":
                    "confirmed",
            },
        )

        selected_a = (
            interface.select(
                kinds=(
                    "example",
                ),

                where=(
                    {
                        "path":
                            "payload.score",

                        "op":
                            "gte",

                        "value":
                            10,
                    },
                ),

                order_by=(
                    "payload.score"
                ),

                fields=(
                    "id",
                    "payload.name",
                ),
            )
        )

        selected_b = (
            interface.select(
                kinds=(
                    "example",
                ),

                where=(
                    {
                        "path":
                            "payload.score",

                        "op":
                            "gte",

                        "value":
                            10,
                    },
                ),

                order_by=(
                    "payload.score"
                ),

                fields=(
                    "id",
                    "payload.name",
                ),
            )
        )

        walked = (
            interface.neighbors(
                first[
                    "id"
                ],

                relation=(
                    "precedes"
                ),

                direction=(
                    "out"
                ),

                depth=1,
            )
        )

        checkpoint = (
            interface.checkpoint()
        )

        health = (
            interface.health()
        )

        immutable_conflict_rejected = (
            False
        )

        try:
            interface.substantiate(
                {
                    "id":
                        "instance:test:first",

                    "kind":
                        "example",

                    "payload":
                        {
                            "name":
                                "changed",

                            "score":
                                999,
                        },

                    "provenance":
                        {
                            "source":
                                (
                                    "interface-"
                                    "selftest"
                                )
                        },
                }
            )

        except Exception:
            immutable_conflict_rejected = (
                True
            )

        checks = {
            "authority_none":
                (
                    authority_effect
                    == "none"
                ),

            "profiles_composed":
                (
                    interface.profiles
                    == (
                        "knowledge",
                        "workflow",
                    )
                ),

            "idempotent_substance":
                (
                    first[
                        "digest"
                    ]
                    == repeated[
                        "digest"
                    ]
                ),

            "immutable_conflict_rejected":
                (
                    immutable_conflict_rejected
                ),

            "typed_segue":
                (
                    edge[
                        "kind"
                    ]
                    == "segue"
                    and edge[
                        "payload"
                    ][
                        "relation"
                    ]
                    == "precedes"
                ),

            "select_count":
                (
                    selected_a[
                        "count"
                    ]
                    == 2
                ),

            "select_deterministic":
                (
                    selected_a
                    == selected_b
                ),

            "select_projection_only":
                (
                    selected_a[
                        "projection_only"
                    ]
                    is True
                ),

            "numeric_ordering":
                (
                    [
                        row[
                            "id"
                        ]
                        for row
                        in selected_a[
                            "records"
                        ]
                    ]
                    == [
                        (
                            "instance:"
                            "test:first"
                        ),
                        (
                            "instance:"
                            "test:second"
                        ),
                    ]
                ),

            "walk_nodes":
                (
                    [
                        row[
                            "id"
                        ]
                        for row
                        in walked[
                            "nodes"
                        ]
                    ]
                    == [
                        (
                            "instance:"
                            "test:first"
                        ),
                        (
                            "instance:"
                            "test:second"
                        ),
                    ]
                ),

            "walk_edge":
                (
                    len(
                        walked[
                            "edges"
                        ]
                    )
                    == 1
                ),

            "checkpoint_non_authoritative":
                (
                    checkpoint[
                        "authority_effect"
                    ]
                    == "none"
                ),

            "health_ok":
                (
                    health[
                        "status"
                    ]
                    == "ok"
                ),

            "no_storage_engine_invented":
                (
                    health[
                        "storage_engine_selected"
                    ]
                    is False
                    and health[
                        "database_engine"
                    ]
                    is None
                ),

            "reconstruction_provenance":
                (
                    health[
                        "exact_source_recovery"
                    ]
                    is False
                    and health[
                        "reconstruction_basis"
                    ]
                    == reconstruction_basis
                ),
        }

        return {
            "schema":
                (
                    "savant.carbon."
                    "straub.datrix-"
                    "interface-selftest.v1"
                ),

            "ok":
                all(
                    checks.values()
                ),

            "checks":
                checks,

            "select_digest":
                selected_a[
                    "digest"
                ],

            "walk_digest":
                walked[
                    "digest"
                ],
        }
