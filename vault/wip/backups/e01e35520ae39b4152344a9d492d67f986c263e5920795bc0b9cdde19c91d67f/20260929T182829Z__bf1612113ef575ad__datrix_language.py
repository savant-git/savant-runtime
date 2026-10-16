#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from runtime.translucent.svg import (
    NS,
    SVG_NS,
    TL_NS,
    TranslucentSVGError,
    svg_runtime,
)
from runtime.straub.interface import DatrixInterface
from runtime.straub.datrix_profiles import (
    manifest as datrix_profile_manifest,
)


schema = "savant.translucent.datrix-language.v1"
owner = "savant"
authority_effect = "none"

MAX_RESULTS = 100000


class TranslucentDatrixError(
    ValueError
):
    pass


def _canonical(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _clean(
    value: Any,
    field: str,
) -> str:
    result = str(
        value or ""
    ).strip()

    if not result:
        raise TranslucentDatrixError(
            f"{field} is required"
        )

    return result


def _split(
    value: Any,
) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part
        in str(
            value or ""
        ).split(",")
        if part.strip()
    )


def _scalar(
    value: str | None,
    type_name: str | None = None,
) -> Any:
    if value is None:
        return None

    kind = str(
        type_name or "string"
    ).strip().casefold()

    if kind == "string":
        return value

    if kind == "integer":
        return int(
            value
        )

    if kind == "number":
        return float(
            value
        )

    if kind == "boolean":
        normalized = (
            value
            .strip()
            .casefold()
        )

        if normalized in {
            "true",
            "1",
            "yes",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
        }:
            return False

        raise TranslucentDatrixError(
            f"invalid boolean: {value!r}"
        )

    if kind == "null":
        return None

    if kind == "json":
        return json.loads(
            value
        )

    raise TranslucentDatrixError(
        "unsupported scalar type: "
        f"{kind}"
    )


def _tag(
    local: str,
) -> str:
    return (
        f"{{{TL_NS}}}"
        f"{local}"
    )


def _validate_svg_source(
    source: str,
) -> ET.Element:
    try:
        return svg_runtime.parse(
            source
        )

    except TranslucentSVGError as exc:
        raise TranslucentDatrixError(
            str(
                exc
            )
        ) from exc


def _payload(
    node: ET.Element,
) -> dict[
    str,
    Any,
]:
    result: dict[
        str,
        Any,
    ] = {}

    for field in node.findall(
        "tl:field",
        NS,
    ):
        name = _clean(
            field.get(
                "name"
            ),
            "field.name",
        )

        if (
            "value"
            in field.attrib
        ):
            result[
                name
            ] = _scalar(
                field.get(
                    "value"
                ),
                field.get(
                    "type"
                ),
            )

        elif list(
            field
        ):
            result[
                name
            ] = _payload(
                field
            )

        else:
            result[
                name
            ] = _scalar(
                field.text or "",
                field.get(
                    "type"
                ),
            )

    return result


def language_manifest(
) -> dict[
    str,
    Any,
]:
    return {
        "schema":
            schema,

        "kind":
            (
                "translucent."
                "datrix-dialect"
            ),

        "host":
            "svg+xml",

        "namespace":
            TL_NS,

        "canonical_program_location":
            (
                "svg/metadata/"
                "tl:program"
            ),

        "operators":
            [
                "open",
                "put",
                "segue",
                "select",
                "match",
                "where",
                "walk",
                "project",
                "order",
                "limit",
                "union",
                "intersect",
                "diff",
                "aggregate",
                "assert",
                "checkpoint",
                "health",
                "explain",
            ],

        "where_operators":
            [
                "eq",
                "ne",
                "exists",
                "contains",
                "in",
                "prefix",
            ],

        "profile_family":
            datrix_profile_manifest(),

        "svg_runtime":
            svg_runtime.manifest(),

        "security":
            {
                "doctype":
                    "forbidden",

                "entities":
                    "forbidden",

                **svg_runtime
                .manifest()[
                    "security"
                ],
            },

        "semantic_rule":
            (
                "namespaced translucent "
                "elements are executable "
                "substance; visible svg "
                "glyphs may project the "
                "same operator identities "
                "but presentation never "
                "becomes authority"
            ),

        "authority_effect":
            authority_effect,
    }


class TranslucentDatrixRuntime:
    def __init__(
        self,
        *,
        root: str | Path = (
            "/root/savant-runtime"
        ),
    ) -> None:
        self.root = Path(
            root
        ).resolve()

        self._datrixes: dict[
            str,
            DatrixInterface,
        ] = {}

        self._results: dict[
            str,
            Any,
        ] = {}

    def _safe_path(
        self,
        raw: str,
    ) -> Path:
        candidate = Path(
            raw
        )

        if not candidate.is_absolute():
            candidate = (
                self.root
                / candidate
            )

        resolved = (
            candidate.resolve()
        )

        try:
            resolved.relative_to(
                self.root
            )

        except ValueError as exc:
            raise (
                TranslucentDatrixError(
                    "datrix path escapes "
                    "savant runtime root"
                )
            ) from exc

        return resolved

    def _program(
        self,
        root: ET.Element,
    ) -> ET.Element:
        try:
            return svg_runtime.program(
                root
            )

        except TranslucentSVGError as exc:
            raise (
                TranslucentDatrixError(
                    str(
                        exc
                    )
                )
            ) from exc

    def _open(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        ref = _clean(
            node.get(
                "ref"
            ),
            "open.ref",
        )

        path = self._safe_path(
            _clean(
                node.get(
                    "path"
                ),
                "open.path",
            )
        )

        profiles = _split(
            node.get(
                "profiles"
            )
        )

        if not profiles:
            profiles = (
                "knowledge",
            )

        self._datrixes[
            ref
        ] = DatrixInterface.open(
            path,
            profiles,
        )

        result = {
            "op":
                "open",

            "ref":
                ref,

            "path":
                str(
                    path
                ),

            "profiles":
                list(
                    profiles
                ),
        }

        self._results[
            ref
        ] = result

        return result

    def _datrix(
        self,
        ref: str | None,
    ) -> DatrixInterface:
        key = _clean(
            ref,
            "datrix",
        )

        try:
            return self._datrixes[
                key
            ]

        except KeyError as exc:
            raise (
                TranslucentDatrixError(
                    "unknown datrix "
                    f"reference: {key}"
                )
            ) from exc

    def _put(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        record: dict[
            str,
            Any,
        ] = {
            "id":
                _clean(
                    node.get(
                        "id"
                    ),
                    "put.id",
                ),

            "kind":
                _clean(
                    node.get(
                        "kind"
                    ),
                    "put.kind",
                ),

            "status":
                str(
                    node.get(
                        "status"
                    )
                    or "active"
                ),

            "payload":
                {},

            "metadata":
                {},

            "dependencies":
                [],

            "relationships":
                [],

            "provenance":
                {
                    "source":
                        schema,
                },

            "lineage":
                {},

            "extensions":
                {
                    "translucent":
                        {
                            "source":
                                "svg",

                            "version":
                                1,
                        }
                },
        }

        payload_node = node.find(
            "tl:payload",
            NS,
        )

        if payload_node is not None:
            record[
                "payload"
            ] = _payload(
                payload_node
            )

        metadata_node = (
            node.find(
                "tl:metadata",
                NS,
            )
        )

        if (
            metadata_node
            is not None
        ):
            record[
                "metadata"
            ] = _payload(
                metadata_node
            )

        for dep in node.findall(
            "tl:depends",
            NS,
        ):
            record[
                "dependencies"
            ].append(
                _clean(
                    dep.get(
                        "ref"
                    ),
                    "depends.ref",
                )
            )

        authority = node.get(
            "authority"
        )

        if authority is not None:
            record[
                "authority"
            ] = _scalar(
                authority,
                node.get(
                    "authority-type"
                ),
            )

        created = (
            datrix.substantiate(
                record
            )
        )

        result = {
            "op":
                "put",

            "id":
                created[
                    "id"
                ],

            "digest":
                created[
                    "digest"
                ],
        }

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = created

        return result

    def _segue(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        created = datrix.relate(
            segue_id=_clean(
                node.get(
                    "id"
                ),
                "segue.id",
            ),

            source_id=_clean(
                node.get(
                    "from"
                ),
                "segue.from",
            ),

            target_id=_clean(
                node.get(
                    "to"
                ),
                "segue.to",
            ),

            relation=_clean(
                node.get(
                    "relation"
                ),
                "segue.relation",
            ),

            payload=_payload(
                node
            ),

            provenance={
                "source":
                    schema,
            },
        )

        result = {
            "op":
                "segue",

            "id":
                created[
                    "id"
                ],

            "digest":
                created[
                    "digest"
                ],
        }

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = created

        return result

    def _where(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        op = str(
            node.get(
                "op"
            )
            or "eq"
        ).casefold()

        raw = node.get(
            "value"
        )

        if op == "in":
            value: Any = [
                _scalar(
                    part.strip(),
                    node.get(
                        "type"
                    ),
                )
                for part
                in str(
                    raw or ""
                ).split(",")
                if part.strip()
            ]

        elif op == "exists":
            value = _scalar(
                str(
                    raw
                    or "true"
                ),
                "boolean",
            )

        else:
            value = _scalar(
                raw,
                node.get(
                    "type"
                ),
            )

        return {
            "path":
                _clean(
                    node.get(
                        "path"
                    ),
                    "where.path",
                ),

            "op":
                op,

            "value":
                value,
        }

    def _select(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        kinds: list[
            str
        ] = []

        where: list[
            dict[
                str,
                Any,
            ]
        ] = []

        fields: tuple[
            str,
            ...,
        ] = ()

        order_by = "id"
        direction = "asc"

        limit: (
            int
            | None
        ) = None

        for child in list(
            node
        ):
            if (
                child.tag
                == _tag(
                    "match"
                )
            ):
                kinds.extend(
                    _split(
                        child.get(
                            "kind"
                        )
                    )
                )

            elif (
                child.tag
                == _tag(
                    "where"
                )
            ):
                where.append(
                    self._where(
                        child
                    )
                )

            elif (
                child.tag
                == _tag(
                    "project"
                )
            ):
                fields = _split(
                    child.get(
                        "fields"
                    )
                )

            elif (
                child.tag
                == _tag(
                    "order"
                )
            ):
                order_by = str(
                    child.get(
                        "by"
                    )
                    or "id"
                )

                direction = str(
                    child.get(
                        "direction"
                    )
                    or "asc"
                )

            elif (
                child.tag
                == _tag(
                    "limit"
                )
            ):
                limit = int(
                    _clean(
                        child.get(
                            "count"
                        ),
                        "limit.count",
                    )
                )

        if (
            limit is not None
            and limit
            > MAX_RESULTS
        ):
            raise (
                TranslucentDatrixError(
                    "limit cannot exceed "
                    f"{MAX_RESULTS}"
                )
            )

        result = datrix.select(
            kinds=kinds,
            where=where,
            order_by=order_by,
            direction=direction,
            limit=limit,
            fields=fields,
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = result

        return {
            "op":
                "select",

            "as":
                out,

            "count":
                result[
                    "count"
                ],

            "digest":
                result[
                    "digest"
                ],

            "result":
                result,
        }

    def _walk(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        result = datrix.neighbors(
            _clean(
                node.get(
                    "from"
                ),
                "walk.from",
            ),

            relation=node.get(
                "relation"
            ),

            direction=str(
                node.get(
                    "direction"
                )
                or "both"
            ),

            depth=int(
                str(
                    node.get(
                        "depth"
                    )
                    or "1"
                )
            ),
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = result

        return {
            "op":
                "walk",

            "as":
                out,

            "nodes":
                len(
                    result[
                        "nodes"
                    ]
                ),

            "digest":
                result[
                    "digest"
                ],

            "result":
                result,
        }

    def _project(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        projection = (
            datrix.project(
                _clean(
                    node.get(
                        "type"
                    ),
                    "project.type",
                )
            )
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = projection

        return {
            "op":
                "project",

            "as":
                out,

            "digest":
                projection[
                    "digest"
                ],

            "result":
                projection,
        }

    def _result_records(
        self,
        ref: str,
    ) -> list[
        dict[
            str,
            Any,
        ]
    ]:
        key = _clean(
            ref,
            "result.ref",
        )

        if (
            key
            not in self._results
        ):
            raise (
                TranslucentDatrixError(
                    "unknown result "
                    f"reference: {key}"
                )
            )

        value = self._results[
            key
        ]

        records = (
            value.get(
                "records"
            )
            if isinstance(
                value,
                Mapping,
            )
            else None
        )

        if not isinstance(
            records,
            list,
        ):
            raise (
                TranslucentDatrixError(
                    f"result {key!r} "
                    "is not a record set"
                )
            )

        return [
            dict(
                item
            )
            for item
            in records
            if isinstance(
                item,
                Mapping,
            )
        ]

    def _set_operation(
        self,
        node: ET.Element,
        operation: str,
    ) -> dict[
        str,
        Any,
    ]:
        refs = _split(
            node.get(
                "refs"
            )
        )

        if len(
            refs
        ) < 2:
            raise (
                TranslucentDatrixError(
                    f"{operation} requires "
                    "at least two refs"
                )
            )

        sets = []
        maps = []

        for ref in refs:
            records = (
                self._result_records(
                    ref
                )
            )

            mapping = {
                _canonical(
                    item
                ):
                    item
                for item
                in records
            }

            maps.append(
                mapping
            )

            sets.append(
                set(
                    mapping
                )
            )

        if operation == "union":
            keys = set().union(
                *sets
            )

        elif operation == "intersect":
            keys = (
                set.intersection(
                    *sets
                )
            )

        elif operation == "diff":
            keys = (
                sets[
                    0
                ].difference(
                    *sets[
                        1:
                    ]
                )
            )

        else:
            raise (
                TranslucentDatrixError(
                    "unknown set "
                    f"operation: {operation}"
                )
            )

        combined: dict[
            str,
            dict[
                str,
                Any,
            ],
        ] = {}

        for mapping in maps:
            combined.update(
                mapping
            )

        records = [
            combined[
                key
            ]
            for key
            in sorted(
                keys
            )
        ]

        result = {
            "schema":
                (
                    "savant."
                    "translucent."
                    "record-set.v1"
                ),

            "operation":
                operation,

            "refs":
                list(
                    refs
                ),

            "count":
                len(
                    records
                ),

            "records":
                records,

            "authority_effect":
                "none",
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = result

        return {
            "op":
                operation,

            "as":
                out,

            "count":
                len(
                    records
                ),

            "digest":
                result[
                    "digest"
                ],

            "result":
                result,
        }

    def _aggregate(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        source = _clean(
            node.get(
                "source"
            ),
            "aggregate.source",
        )

        records = (
            self._result_records(
                source
            )
        )

        by = str(
            node.get(
                "by"
            )
            or ""
        ).strip()

        function = str(
            node.get(
                "fn"
            )
            or "count"
        ).strip().casefold()

        path = str(
            node.get(
                "path"
            )
            or ""
        ).strip()

        groups: dict[
            str,
            list[
                dict[
                    str,
                    Any,
                ]
            ],
        ] = {}

        if by:
            for record in records:
                value: Any = record

                for part in by.split(
                    "."
                ):
                    value = (
                        value.get(
                            part
                        )
                        if isinstance(
                            value,
                            Mapping,
                        )
                        else None
                    )

                groups.setdefault(
                    _canonical(
                        value
                    ),
                    [],
                ).append(
                    record
                )

        else:
            groups[
                "null"
            ] = records

        rows = []

        for group_key in sorted(
            groups
        ):
            group_records = (
                groups[
                    group_key
                ]
            )

            group_value = json.loads(
                group_key
            )

            values = []

            if path:
                for record in (
                    group_records
                ):
                    value: Any = record

                    for part in path.split(
                        "."
                    ):
                        value = (
                            value.get(
                                part
                            )
                            if isinstance(
                                value,
                                Mapping,
                            )
                            else None
                        )

                    if (
                        isinstance(
                            value,
                            (
                                int,
                                float,
                            ),
                        )
                        and not isinstance(
                            value,
                            bool,
                        )
                    ):
                        values.append(
                            value
                        )

            if function == "count":
                aggregate_value: Any = (
                    len(
                        group_records
                    )
                )

            elif function == "sum":
                aggregate_value = sum(
                    values
                )

            elif function == "min":
                aggregate_value = (
                    min(
                        values
                    )
                    if values
                    else None
                )

            elif function == "max":
                aggregate_value = (
                    max(
                        values
                    )
                    if values
                    else None
                )

            elif function == "avg":
                aggregate_value = (
                    (
                        sum(
                            values
                        )
                        / len(
                            values
                        )
                    )
                    if values
                    else None
                )

            else:
                raise (
                    TranslucentDatrixError(
                        "unsupported aggregate "
                        f"function: {function}"
                    )
                )

            rows.append(
                {
                    "group":
                        group_value,

                    "value":
                        aggregate_value,

                    "count":
                        len(
                            group_records
                        ),
                }
            )

        result = {
            "schema":
                (
                    "savant."
                    "translucent."
                    "aggregate.v1"
                ),

            "source":
                source,

            "by":
                (
                    by
                    or None
                ),

            "function":
                function,

            "path":
                (
                    path
                    or None
                ),

            "rows":
                rows,

            "authority_effect":
                "none",
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = result

        return {
            "op":
                "aggregate",

            "as":
                out,

            "digest":
                result[
                    "digest"
                ],

            "result":
                result,
        }

    def _assert(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        ref = _clean(
            node.get(
                "ref"
            ),
            "assert.ref",
        )

        if ref not in self._results:
            raise (
                TranslucentDatrixError(
                    "unknown result "
                    f"reference: {ref}"
                )
            )

        value = self._results[
            ref
        ]

        path = _clean(
            node.get(
                "path"
            ),
            "assert.path",
        )

        actual: Any = value

        for part in path.split(
            "."
        ):
            actual = (
                actual.get(
                    part
                )
                if isinstance(
                    actual,
                    Mapping,
                )
                else None
            )

        op = str(
            node.get(
                "op"
            )
            or "eq"
        ).strip().casefold()

        expected = _scalar(
            node.get(
                "value"
            ),
            node.get(
                "type"
            ),
        )

        passed = False

        if op == "eq":
            passed = (
                actual
                == expected
            )

        elif op == "ne":
            passed = (
                actual
                != expected
            )

        elif op == "gte":
            passed = (
                actual is not None
                and actual
                >= expected
            )

        elif op == "lte":
            passed = (
                actual is not None
                and actual
                <= expected
            )

        elif op == "exists":
            passed = (
                (
                    actual
                    is not None
                )
                == bool(
                    expected
                )
            )

        else:
            raise (
                TranslucentDatrixError(
                    "unsupported assert "
                    f"operator: {op}"
                )
            )

        if not passed:
            raise (
                TranslucentDatrixError(
                    "assertion failed for "
                    f"{ref}.{path}: "
                    f"{actual!r} "
                    f"{op} "
                    f"{expected!r}"
                )
            )

        return {
            "op":
                "assert",

            "ref":
                ref,

            "path":
                path,

            "passed":
                True,
        }

    def _checkpoint(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        result = (
            datrix.checkpoint()
        )

        return {
            "op":
                "checkpoint",

            "result":
                result,
        }

    def _health(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        datrix = self._datrix(
            node.get(
                "datrix"
            )
        )

        result = (
            datrix.health()
        )

        out = node.get(
            "as"
        )

        if out:
            self._results[
                out
            ] = result

        return {
            "op":
                "health",

            "as":
                out,

            "status":
                result[
                    "status"
                ],

            "result":
                result,
        }

    def _explain(
        self,
        node: ET.Element,
    ) -> dict[
        str,
        Any,
    ]:
        ref = _clean(
            node.get(
                "ref"
            ),
            "explain.ref",
        )

        if ref not in self._results:
            raise (
                TranslucentDatrixError(
                    "unknown result "
                    f"reference: {ref}"
                )
            )

        value = self._results[
            ref
        ]

        return {
            "op":
                "explain",

            "ref":
                ref,

            "digest":
                _digest(
                    value
                ),

            "value":
                value,

            "authority_effect":
                "none",
        }

    def execute(
        self,
        source: str,
    ) -> dict[
        str,
        Any,
    ]:
        root = (
            _validate_svg_source(
                source
            )
        )

        program = self._program(
            root
        )

        operations: list[
            dict[
                str,
                Any,
            ]
        ] = []

        handlers = {
            _tag(
                "open"
            ):
                self._open,

            _tag(
                "put"
            ):
                self._put,

            _tag(
                "segue"
            ):
                self._segue,

            _tag(
                "select"
            ):
                self._select,

            _tag(
                "walk"
            ):
                self._walk,

            _tag(
                "project"
            ):
                self._project,

            _tag(
                "union"
            ):
                (
                    lambda node:
                    self._set_operation(
                        node,
                        "union",
                    )
                ),

            _tag(
                "intersect"
            ):
                (
                    lambda node:
                    self._set_operation(
                        node,
                        "intersect",
                    )
                ),

            _tag(
                "diff"
            ):
                (
                    lambda node:
                    self._set_operation(
                        node,
                        "diff",
                    )
                ),

            _tag(
                "aggregate"
            ):
                self._aggregate,

            _tag(
                "assert"
            ):
                self._assert,

            _tag(
                "checkpoint"
            ):
                self._checkpoint,

            _tag(
                "health"
            ):
                self._health,

            _tag(
                "explain"
            ):
                self._explain,
        }

        for node in list(
            program
        ):
            handler = handlers.get(
                node.tag
            )

            if handler is None:
                raise (
                    TranslucentDatrixError(
                        "unsupported translucent "
                        f"operator: {node.tag}"
                    )
                )

            operations.append(
                handler(
                    node
                )
            )

        result = {
            "schema":
                schema,

            "kind":
                (
                    "translucent."
                    "execution"
                ),

            "program_id":
                str(
                    program.get(
                        "id"
                    )
                    or "program"
                ),

            "operation_count":
                len(
                    operations
                ),

            "operations":
                operations,

            "result_refs":
                sorted(
                    self._results
                ),

            "authority_effect":
                authority_effect,
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result

    def render_execution_svg(
        self,
        execution: Mapping[
            str,
            Any,
        ],
        *,
        width: int = 1280,
        row_height: int = 34,
        renderer: str | None = None,
    ) -> str:
        try:
            return svg_runtime.render(
                "execution",
                execution,
                renderer=renderer,
                context={
                    "width":
                        width,

                    "row_height":
                        row_height,
                },
            )

        except TranslucentSVGError as exc:
            raise (
                TranslucentDatrixError(
                    str(
                        exc
                    )
                )
            ) from exc


def execute_svg(
    source: str,
    *,
    root: str | Path = (
        "/root/savant-runtime"
    ),
) -> dict[
    str,
    Any,
]:
    return (
        TranslucentDatrixRuntime(
            root=root
        ).execute(
            source
        )
    )
