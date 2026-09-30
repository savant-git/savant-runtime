#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence


schema = "savant.translucent.datrix-query.v1"
authority_effect = "none"
MAX_ROWS = 100_000
MAX_JOIN_ROWS = 100_000
MAX_PREDICATE_DEPTH = 64


class DatrixQueryError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DatrixQueryError(
            f"value is not canonical-json compatible: {exc}"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def path_get(value: Any, path: str) -> Any:
    current = value
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        if isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
            continue
        return None
    return current


def _sort_token(value: Any) -> tuple[int, Any]:
    if value is None:
        return (5, "")
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return (1, value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DatrixQueryError("non-finite number cannot participate in ordering")
        return (1, value)
    if isinstance(value, str):
        return (2, value)
    if isinstance(value, (list, tuple)):
        return (3, _canonical(value))
    if isinstance(value, Mapping):
        return (4, _canonical(value))
    return (4, _canonical(value))


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str):
        return str(expected) in actual
    if isinstance(actual, Mapping):
        return expected in actual
    if isinstance(actual, Sequence) and not isinstance(actual, (str, bytes, bytearray)):
        return expected in actual
    return False


def _compare(actual: Any, op: str, expected: Any, expected2: Any = None) -> bool:
    operator = str(op or "eq").strip().casefold()
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "exists":
        return (actual is not None) == bool(expected)
    if operator == "contains":
        return _contains(actual, expected)
    if operator == "in":
        return actual in expected if isinstance(expected, Sequence) and not isinstance(
            expected, (str, bytes, bytearray)
        ) else False
    if operator == "not-in":
        return actual not in expected if isinstance(expected, Sequence) and not isinstance(
            expected, (str, bytes, bytearray)
        ) else True
    if operator == "prefix":
        return isinstance(actual, str) and actual.startswith(str(expected))
    if operator == "suffix":
        return isinstance(actual, str) and actual.endswith(str(expected))
    try:
        if operator == "gt":
            return actual is not None and actual > expected
        if operator == "gte":
            return actual is not None and actual >= expected
        if operator == "lt":
            return actual is not None and actual < expected
        if operator == "lte":
            return actual is not None and actual <= expected
        if operator == "between":
            return actual is not None and expected <= actual <= expected2
    except TypeError:
        return False
    raise DatrixQueryError(f"unsupported predicate operator: {operator}")


def evaluate_predicate(
    record: Mapping[str, Any],
    predicate: Mapping[str, Any] | None,
    *,
    depth: int = 0,
) -> bool:
    if predicate is None:
        return True
    if depth > MAX_PREDICATE_DEPTH:
        raise DatrixQueryError(
            f"predicate tree exceeds depth {MAX_PREDICATE_DEPTH}"
        )
    kind = str(predicate.get("kind") or "where").casefold()
    if kind == "where":
        return _compare(
            path_get(record, str(predicate.get("path") or "")),
            str(predicate.get("op") or "eq"),
            predicate.get("value"),
            predicate.get("value2"),
        )
    children = predicate.get("children")
    if not isinstance(children, Sequence) or isinstance(children, (str, bytes, bytearray)):
        raise DatrixQueryError(f"predicate group {kind!r} requires child predicates")
    child_values = [
        evaluate_predicate(record, child, depth=depth + 1)
        for child in children
        if isinstance(child, Mapping)
    ]
    if len(child_values) != len(children):
        raise DatrixQueryError("predicate groups may contain predicate mappings only")
    if kind == "all":
        if not child_values:
            raise DatrixQueryError("all predicate requires at least one child")
        return all(child_values)
    if kind == "any":
        if not child_values:
            raise DatrixQueryError("any predicate requires at least one child")
        return any(child_values)
    if kind == "not":
        if len(child_values) != 1:
            raise DatrixQueryError("not predicate requires exactly one child")
        return not child_values[0]
    raise DatrixQueryError(f"unsupported predicate kind: {kind}")


def filter_records(
    records: Sequence[Mapping[str, Any]],
    predicate: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if len(records) > MAX_ROWS:
        raise DatrixQueryError(f"source exceeds {MAX_ROWS} records")
    return [
        deepcopy(dict(record))
        for record in records
        if evaluate_predicate(record, predicate)
    ]


def order_records(
    records: Sequence[Mapping[str, Any]],
    orders: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = [deepcopy(dict(record)) for record in records]
    normalized: list[tuple[str, bool]] = []
    for order in orders:
        path = str(order.get("by") or "").strip()
        if not path:
            raise DatrixQueryError("order.by is required")
        direction = str(order.get("direction") or "asc").strip().casefold()
        if direction not in {"asc", "desc"}:
            raise DatrixQueryError("order.direction must be asc or desc")
        normalized.append((path, direction == "desc"))
    for path, reverse in reversed(normalized):
        result.sort(
            key=lambda record, p=path: _sort_token(path_get(record, p)),
            reverse=reverse,
        )
    return result


def project_records(
    records: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    normalized = tuple(str(field).strip() for field in fields if str(field).strip())
    if not normalized:
        return [deepcopy(dict(record)) for record in records]
    return [
        {field: deepcopy(path_get(record, field)) for field in normalized}
        for record in records
    ]


def distinct_records(
    records: Sequence[Mapping[str, Any]],
    by: Sequence[str] = (),
) -> list[dict[str, Any]]:
    paths = tuple(str(path).strip() for path in by if str(path).strip())
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        key_value: Any
        if paths:
            key_value = [path_get(record, path) for path in paths]
        else:
            key_value = record
        key = _canonical(key_value)
        if key in seen:
            continue
        seen.add(key)
        result.append(deepcopy(dict(record)))
    return result


def apply_select(
    records: Sequence[Mapping[str, Any]],
    *,
    predicate: Mapping[str, Any] | None = None,
    orders: Sequence[Mapping[str, Any]] = (),
    distinct_by: Sequence[str] = (),
    distinct: bool = False,
    offset: int = 0,
    limit: int | None = None,
    fields: Sequence[str] = (),
) -> list[dict[str, Any]]:
    if isinstance(offset, bool) or int(offset) < 0:
        raise DatrixQueryError("offset must be a non-negative integer")
    if limit is not None and (isinstance(limit, bool) or int(limit) < 0):
        raise DatrixQueryError("limit must be a non-negative integer")
    result = filter_records(records, predicate)
    if orders:
        result = order_records(result, orders)
    if distinct or distinct_by:
        result = distinct_records(result, distinct_by)
    start = int(offset)
    stop = None if limit is None else start + int(limit)
    result = result[start:stop]
    result = project_records(result, fields)
    if len(result) > MAX_ROWS:
        raise DatrixQueryError(f"query produced more than {MAX_ROWS} records")
    return result


def _join_match(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    clauses: Sequence[Mapping[str, Any]],
) -> bool:
    for clause in clauses:
        left_path = str(clause.get("left") or "").strip()
        right_path = str(clause.get("right") or "").strip()
        if not left_path or not right_path:
            raise DatrixQueryError("join conditions require left and right paths")
        if not _compare(
            path_get(left, left_path),
            str(clause.get("op") or "eq"),
            path_get(right, right_path),
        ):
            return False
    return True


def join_records(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    *,
    clauses: Sequence[Mapping[str, Any]],
    join_type: str = "inner",
    max_rows: int = MAX_JOIN_ROWS,
) -> list[dict[str, Any]]:
    if not clauses:
        raise DatrixQueryError("join requires at least one on clause")
    mode = str(join_type or "inner").strip().casefold()
    if mode not in {"inner", "left", "right", "full", "semi", "anti"}:
        raise DatrixQueryError(
            "join type must be inner, left, right, full, semi, or anti"
        )
    output: list[dict[str, Any]] = []
    matched_right: set[int] = set()
    for left_row in left:
        matches: list[tuple[int, Mapping[str, Any]]] = []
        for index, right_row in enumerate(right):
            if _join_match(left_row, right_row, clauses):
                matches.append((index, right_row))
        if mode == "semi":
            if matches:
                output.append(deepcopy(dict(left_row)))
        elif mode == "anti":
            if not matches:
                output.append(deepcopy(dict(left_row)))
        elif matches:
            for index, right_row in matches:
                matched_right.add(index)
                output.append(
                    {
                        "left": deepcopy(dict(left_row)),
                        "right": deepcopy(dict(right_row)),
                    }
                )
        elif mode in {"left", "full"}:
            output.append({"left": deepcopy(dict(left_row)), "right": None})
        if len(output) > max_rows:
            raise DatrixQueryError(f"join produced more than {max_rows} rows")
    if mode in {"right", "full"}:
        for index, right_row in enumerate(right):
            if index not in matched_right:
                output.append({"left": None, "right": deepcopy(dict(right_row))})
                if len(output) > max_rows:
                    raise DatrixQueryError(f"join produced more than {max_rows} rows")
    return output


def _metric_values(
    records: Sequence[Mapping[str, Any]],
    path: str,
    *,
    distinct: bool,
) -> list[Any]:
    values = [path_get(record, path) for record in records] if path else []
    if distinct:
        unique: list[Any] = []
        seen: set[str] = set()
        for value in values:
            key = _canonical(value)
            if key not in seen:
                seen.add(key)
                unique.append(value)
        values = unique
    return values


def aggregate_records(
    records: Sequence[Mapping[str, Any]],
    *,
    group_by: Sequence[str] = (),
    metrics: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    if len(records) > MAX_ROWS:
        raise DatrixQueryError(f"aggregate source exceeds {MAX_ROWS} records")
    groups: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    paths = tuple(str(path).strip() for path in group_by if str(path).strip())
    for record in records:
        group = {path: deepcopy(path_get(record, path)) for path in paths}
        key = _canonical(group)
        groups.setdefault(key, (group, []))[1].append(deepcopy(dict(record)))
    if not records and not paths:
        groups[_canonical({})] = ({}, [])
    normalized_metrics = [dict(metric) for metric in metrics]
    if not normalized_metrics:
        normalized_metrics = [{"alias": "count", "fn": "count", "path": "", "distinct": False}]
    result: list[dict[str, Any]] = []
    for key in sorted(groups):
        group, members = groups[key]
        metric_values: dict[str, Any] = {}
        for metric in normalized_metrics:
            alias = str(metric.get("alias") or "").strip()
            function = str(metric.get("fn") or "count").strip().casefold()
            path = str(metric.get("path") or "").strip()
            distinct = bool(metric.get("distinct", False))
            if not alias:
                raise DatrixQueryError("aggregate metric alias is required")
            if alias in metric_values:
                raise DatrixQueryError(f"duplicate aggregate metric alias: {alias}")
            values = _metric_values(members, path, distinct=distinct)
            numeric = [
                value
                for value in values
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            if function == "count":
                value: Any = len(values) if path else len(members)
            elif function == "count-nonnull":
                value = sum(item is not None for item in values)
            elif function == "sum":
                value = sum(numeric)
            elif function == "min":
                value = min(values, key=_sort_token) if values else None
            elif function == "max":
                value = max(values, key=_sort_token) if values else None
            elif function == "avg":
                value = (sum(numeric) / len(numeric)) if numeric else None
            else:
                raise DatrixQueryError(f"unsupported aggregate function: {function}")
            if isinstance(value, float) and not math.isfinite(value):
                raise DatrixQueryError(
                    f"aggregate metric {alias!r} produced a non-finite number"
                )
            metric_values[alias] = value
        result.append(
            {
                "group": group,
                "metrics": metric_values,
                "count": len(members),
                "_members": members,
            }
        )
        if len(result) > MAX_ROWS:
            raise DatrixQueryError(f"aggregate produced more than {MAX_ROWS} groups")
    return result


def window_records(
    records: Sequence[Mapping[str, Any]],
    *,
    function: str,
    alias: str,
    partition_by: Sequence[str] = (),
    orders: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    fn = str(function or "").strip().casefold().replace("_", "-")
    if fn not in {"row-number", "rank", "dense-rank"}:
        raise DatrixQueryError(
            "window function must be row-number, rank, or dense-rank"
        )
    alias_name = str(alias or "").strip()
    if not alias_name:
        raise DatrixQueryError("window alias is required")
    partitions: dict[str, list[dict[str, Any]]] = {}
    paths = tuple(str(path).strip() for path in partition_by if str(path).strip())
    for record in records:
        key = _canonical([path_get(record, path) for path in paths])
        partitions.setdefault(key, []).append(deepcopy(dict(record)))
    output: list[dict[str, Any]] = []
    for partition_key in sorted(partitions):
        rows = order_records(partitions[partition_key], orders) if orders else partitions[partition_key]
        previous_key: str | None = None
        current_rank = 0
        dense_rank = 0
        for index, record in enumerate(rows, start=1):
            order_key = _canonical(
                [path_get(record, str(order.get("by") or "")) for order in orders]
            )
            if previous_key != order_key:
                current_rank = index
                dense_rank += 1
                previous_key = order_key
            if fn == "row-number":
                value = index
            elif fn == "rank":
                value = current_rank
            else:
                value = dense_rank
            enriched = deepcopy(record)
            window = enriched.get("window")
            if window is None:
                enriched["window"] = {}
                window = enriched["window"]
            if not isinstance(window, dict):
                raise DatrixQueryError("record already contains non-object window field")
            if alias_name in window:
                raise DatrixQueryError(f"window alias already exists: {alias_name}")
            window[alias_name] = value
            output.append(enriched)
    if len(output) > MAX_ROWS:
        raise DatrixQueryError(f"window produced more than {MAX_ROWS} rows")
    return output


def result_set(
    records: Sequence[Mapping[str, Any]],
    *,
    kind: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(records) > MAX_ROWS:
        raise DatrixQueryError(f"result set exceeds {MAX_ROWS} rows")
    result = {
        "schema": "savant.translucent.record-set.v5",
        "kind": str(kind),
        "count": len(records),
        "records": [deepcopy(dict(record)) for record in records],
        "metadata": deepcopy(dict(metadata or {})),
        "projection_only": True,
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


__all__ = [
    "DatrixQueryError",
    "MAX_JOIN_ROWS",
    "MAX_PREDICATE_DEPTH",
    "MAX_ROWS",
    "aggregate_records",
    "apply_select",
    "authority_effect",
    "distinct_records",
    "evaluate_predicate",
    "filter_records",
    "join_records",
    "order_records",
    "path_get",
    "project_records",
    "result_set",
    "schema",
    "window_records",
]
