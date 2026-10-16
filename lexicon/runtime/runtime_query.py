#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

COMPILED_ROOT = (
    RUNTIME_ROOT
    / "compiled"
)

ADDRESS_INDEX_PATH = (
    COMPILED_ROOT
    / "runtime_address_index.json"
)


class RuntimeQueryError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
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


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            str(path)
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(
            handle
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeQueryError(
            f"Expected object root: {path}"
        )

    return payload


def normalize(
    value: Any,
) -> str:
    return str(
        value
    ).strip()


def normalize_lower(
    value: Any,
) -> str:
    return normalize(
        value
    ).casefold()


def flatten_strings(
    value: Any,
) -> Iterable[str]:
    if value is None:
        return

    if isinstance(
        value,
        str,
    ):
        yield value
        return

    if isinstance(
        value,
        dict,
    ):
        for key, child in value.items():
            yield str(
                key
            )
            yield from flatten_strings(
                child
            )
        return

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        for child in value:
            yield from flatten_strings(
                child
            )
        return

    yield str(
        value
    )


def record_text(
    address: str,
    record: dict[str, Any],
) -> str:
    values = [
        address,
        *flatten_strings(
            record
        ),
    ]

    return "\n".join(
        normalize_lower(
            value
        )
        for value in values
        if normalize(
            value
        )
    )


def resolve_alias(
    value: str,
    index: dict[str, Any],
) -> str | None:
    value = normalize(
        value
    )

    records = index.get(
        "records",
        {},
    )

    aliases = index.get(
        "aliases",
        {},
    )

    if not isinstance(
        records,
        dict,
    ):
        raise RuntimeQueryError(
            "Invalid records index"
        )

    if not isinstance(
        aliases,
        dict,
    ):
        raise RuntimeQueryError(
            "Invalid alias index"
        )

    if value in records:
        return value

    target = aliases.get(
        value
    )

    if isinstance(
        target,
        str,
    ) and target in records:
        return target

    return None


def nested_get(
    value: Any,
    path: str,
) -> Any:
    current = value

    for part in path.split(
        "."
    ):
        part = normalize(
            part
        )

        if not part:
            continue

        if isinstance(
            current,
            dict,
        ):
            if part not in current:
                return None

            current = current[
                part
            ]
            continue

        if isinstance(
            current,
            list,
        ):
            try:
                position = int(
                    part
                )
            except ValueError:
                return None

            if (
                position < 0
                or position >= len(
                    current
                )
            ):
                return None

            current = current[
                position
            ]
            continue

        return None

    return current


def compare_value(
    actual: Any,
    operator: str,
    expected: str,
) -> bool:
    expected_normalized = normalize_lower(
        expected
    )

    if operator == "exists":
        return actual is not None

    if operator == "missing":
        return actual is None

    if operator == "eq":
        return normalize_lower(
            actual
        ) == expected_normalized

    if operator == "ne":
        return normalize_lower(
            actual
        ) != expected_normalized

    if operator == "contains":
        if isinstance(
            actual,
            (
                list,
                tuple,
                set,
            ),
        ):
            return any(
                normalize_lower(
                    item
                ) == expected_normalized
                for item in actual
            )

        return expected_normalized in normalize_lower(
            actual
        )

    if operator == "prefix":
        return normalize_lower(
            actual
        ).startswith(
            expected_normalized
        )

    if operator == "suffix":
        return normalize_lower(
            actual
        ).endswith(
            expected_normalized
        )

    if operator == "regex":
        return (
            re.search(
                expected,
                normalize(
                    actual
                ),
            )
            is not None
        )

    raise RuntimeQueryError(
        f"Unknown operator: {operator}"
    )


class RuntimeQuery:

    def __init__(
        self,
        index_path: Path = ADDRESS_INDEX_PATH,
    ) -> None:
        self.index_path = index_path
        self.index = load_json(
            index_path
        )

        records = self.index.get(
            "records",
            {}
        )

        aliases = self.index.get(
            "aliases",
            {}
        )

        if not isinstance(
            records,
            dict,
        ):
            raise RuntimeQueryError(
                "records must be an object"
            )

        if not isinstance(
            aliases,
            dict,
        ):
            raise RuntimeQueryError(
                "aliases must be an object"
            )

        self.records: dict[
            str,
            dict[str, Any],
        ] = {
            normalize(
                address
            ): record
            for address, record in records.items()
            if isinstance(
                record,
                dict,
            )
        }

        self.aliases: dict[
            str,
            str,
        ] = {
            normalize(
                alias
            ): normalize(
                target
            )
            for alias, target in aliases.items()
            if normalize(
                alias
            )
            and normalize(
                target
            )
        }

    def resolve(
        self,
        address: str,
    ) -> dict[str, Any]:
        canonical = resolve_alias(
            address,
            self.index,
        )

        if canonical is None:
            return {
                "operation": "resolve",
                "passed": False,
                "query": address,
                "resolved": False,
                "address": None,
                "record": None,
            }

        return {
            "operation": "resolve",
            "passed": True,
            "query": address,
            "resolved": True,
            "address": canonical,
            "record": self.records[
                canonical
            ],
        }

    def search(
        self,
        query: str,
        *,
        record_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        terms = [
            normalize_lower(
                term
            )
            for term in re.split(
                r"\s+",
                query,
            )
            if normalize(
                term
            )
        ]

        expected_type = (
            normalize_lower(
                record_type
            )
            if record_type
            else None
        )

        results = []

        for address in sorted(
            self.records
        ):
            record = self.records[
                address
            ]

            if expected_type is not None:
                if normalize_lower(
                    record.get(
                        "type",
                        "",
                    )
                ) != expected_type:
                    continue

            searchable = record_text(
                address,
                record,
            )

            if not all(
                term in searchable
                for term in terms
            ):
                continue

            score = 0

            address_lower = normalize_lower(
                address
            )

            canonical_lower = normalize_lower(
                record.get(
                    "canonical",
                    "",
                )
            )

            for term in terms:
                if term == address_lower:
                    score += 100
                elif term in address_lower:
                    score += 40

                if term == canonical_lower:
                    score += 80
                elif term in canonical_lower:
                    score += 30

                score += searchable.count(
                    term
                )

            results.append(
                {
                    "address": address,
                    "score": score,
                    "record": record,
                }
            )

        results.sort(
            key=lambda item: (
                -int(
                    item[
                        "score"
                    ]
                ),
                str(
                    item[
                        "address"
                    ]
                ),
            )
        )

        if limit is not None:
            results = results[
                :max(
                    limit,
                    0,
                )
            ]

        payload = {
            "operation": "search",
            "passed": True,
            "query": query,
            "record_type": record_type,
            "count": len(
                results
            ),
            "results": results,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def filter(
        self,
        field: str,
        operator: str,
        expected: str = "",
        *,
        limit: int | None = None,
    ) -> dict[str, Any]:
        results = []

        for address in sorted(
            self.records
        ):
            record = self.records[
                address
            ]

            actual = nested_get(
                record,
                field,
            )

            if not compare_value(
                actual,
                operator,
                expected,
            ):
                continue

            results.append(
                {
                    "address": address,
                    "field": field,
                    "actual": actual,
                    "record": record,
                }
            )

        if limit is not None:
            results = results[
                :max(
                    limit,
                    0,
                )
            ]

        payload = {
            "operation": "filter",
            "passed": True,
            "field": field,
            "operator": operator,
            "expected": expected,
            "count": len(
                results
            ),
            "results": results,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def traverse(
        self,
        start: str,
        *,
        relation: str | None = None,
        depth: int = 1,
        direction: str = "out",
    ) -> dict[str, Any]:
        canonical = resolve_alias(
            start,
            self.index,
        )

        if canonical is None:
            return {
                "operation": "traverse",
                "passed": False,
                "start": start,
                "resolved": False,
                "results": [],
            }

        if direction not in {
            "out",
            "in",
            "both",
        }:
            raise RuntimeQueryError(
                f"Invalid direction: {direction}"
            )

        max_depth = max(
            depth,
            0,
        )

        queue: list[
            tuple[
                str,
                int,
                list[str],
            ]
        ] = [
            (
                canonical,
                0,
                [
                    canonical
                ],
            )
        ]

        visited = {
            canonical
        }

        results = []

        while queue:
            address, current_depth, path = (
                queue.pop(
                    0
                )
            )

            if current_depth >= max_depth:
                continue

            outgoing = self._outgoing(
                address,
                relation,
            )

            incoming = self._incoming(
                address,
                relation,
            )

            edges = []

            if direction in {
                "out",
                "both",
            }:
                edges.extend(
                    outgoing
                )

            if direction in {
                "in",
                "both",
            }:
                edges.extend(
                    incoming
                )

            edges.sort(
                key=lambda item: (
                    item[
                        "relation"
                    ],
                    item[
                        "target"
                    ],
                    item[
                        "direction"
                    ],
                )
            )

            for edge in edges:
                target = edge[
                    "target"
                ]

                next_path = [
                    *path,
                    target,
                ]

                results.append(
                    {
                        "from": address,
                        "to": target,
                        "relation": edge[
                            "relation"
                        ],
                        "direction": edge[
                            "direction"
                        ],
                        "depth": (
                            current_depth
                            + 1
                        ),
                        "path": next_path,
                        "record": self.records.get(
                            target
                        ),
                    }
                )

                if target in visited:
                    continue

                visited.add(
                    target
                )

                if target in self.records:
                    queue.append(
                        (
                            target,
                            current_depth
                            + 1,
                            next_path,
                        )
                    )

        payload = {
            "operation": "traverse",
            "passed": True,
            "start": start,
            "address": canonical,
            "relation": relation,
            "direction": direction,
            "depth": max_depth,
            "count": len(
                results
            ),
            "results": results,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def path(
        self,
        start: str,
        end: str,
        *,
        relation: str | None = None,
        max_depth: int = 16,
    ) -> dict[str, Any]:
        start_address = resolve_alias(
            start,
            self.index,
        )

        end_address = resolve_alias(
            end,
            self.index,
        )

        if (
            start_address is None
            or end_address is None
        ):
            return {
                "operation": "path",
                "passed": False,
                "start": start,
                "end": end,
                "resolved": False,
                "found": False,
                "path": [],
            }

        queue: list[
            tuple[
                str,
                list[dict[str, Any]],
            ]
        ] = [
            (
                start_address,
                [],
            )
        ]

        visited = {
            start_address
        }

        while queue:
            current, edges = queue.pop(
                0
            )

            if current == end_address:
                addresses = [
                    start_address,
                    *[
                        edge[
                            "to"
                        ]
                        for edge in edges
                    ],
                ]

                payload = {
                    "operation": "path",
                    "passed": True,
                    "start": start_address,
                    "end": end_address,
                    "found": True,
                    "length": len(
                        edges
                    ),
                    "addresses": addresses,
                    "edges": edges,
                }

                payload[
                    "digest"
                ] = digest(
                    payload
                )

                return payload

            if len(
                edges
            ) >= max_depth:
                continue

            outgoing = self._outgoing(
                current,
                relation,
            )

            for edge in outgoing:
                target = edge[
                    "target"
                ]

                if target in visited:
                    continue

                visited.add(
                    target
                )

                queue.append(
                    (
                        target,
                        [
                            *edges,
                            {
                                "from": current,
                                "to": target,
                                "relation": edge[
                                    "relation"
                                ],
                            },
                        ],
                    )
                )

        payload = {
            "operation": "path",
            "passed": True,
            "start": start_address,
            "end": end_address,
            "found": False,
            "length": None,
            "addresses": [],
            "edges": [],
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def _outgoing(
        self,
        address: str,
        relation: str | None,
    ) -> list[dict[str, str]]:
        record = self.records.get(
            address,
            {}
        )

        relationships = record.get(
            "relationships",
            {}
        )

        if not isinstance(
            relationships,
            dict,
        ):
            return []

        results = []

        for relation_name, targets in (
            relationships.items()
        ):
            if (
                relation is not None
                and relation_name != relation
            ):
                continue

            if not isinstance(
                targets,
                list,
            ):
                continue

            for target in targets:
                target = normalize(
                    target
                )

                if not target:
                    continue

                results.append(
                    {
                        "relation": relation_name,
                        "target": target,
                        "direction": "out",
                    }
                )

        return results

    def _incoming(
        self,
        address: str,
        relation: str | None,
    ) -> list[dict[str, str]]:
        results = []

        for source, record in self.records.items():
            relationships = record.get(
                "relationships",
                {}
            )

            if not isinstance(
                relationships,
                dict,
            ):
                continue

            for relation_name, targets in (
                relationships.items()
            ):
                if (
                    relation is not None
                    and relation_name != relation
                ):
                    continue

                if not isinstance(
                    targets,
                    list,
                ):
                    continue

                if address not in {
                    normalize(
                        target
                    )
                    for target in targets
                }:
                    continue

                results.append(
                    {
                        "relation": relation_name,
                        "target": source,
                        "direction": "in",
                    }
                )

        return results


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--index",
        default=str(
            ADDRESS_INDEX_PATH
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "address"
    )

    search_parser = subparsers.add_parser(
        "search"
    )

    search_parser.add_argument(
        "query"
    )

    search_parser.add_argument(
        "--type"
    )

    search_parser.add_argument(
        "--limit",
        type=int,
    )

    filter_parser = subparsers.add_parser(
        "filter"
    )

    filter_parser.add_argument(
        "field"
    )

    filter_parser.add_argument(
        "operator",
        choices=[
            "eq",
            "ne",
            "contains",
            "prefix",
            "suffix",
            "regex",
            "exists",
            "missing",
        ],
    )

    filter_parser.add_argument(
        "expected",
        nargs="?",
        default="",
    )

    filter_parser.add_argument(
        "--limit",
        type=int,
    )

    traverse_parser = subparsers.add_parser(
        "traverse"
    )

    traverse_parser.add_argument(
        "start"
    )

    traverse_parser.add_argument(
        "--relation"
    )

    traverse_parser.add_argument(
        "--depth",
        type=int,
        default=1,
    )

    traverse_parser.add_argument(
        "--direction",
        choices=[
            "out",
            "in",
            "both",
        ],
        default="out",
    )

    path_parser = subparsers.add_parser(
        "path"
    )

    path_parser.add_argument(
        "start"
    )

    path_parser.add_argument(
        "end"
    )

    path_parser.add_argument(
        "--relation"
    )

    path_parser.add_argument(
        "--max-depth",
        type=int,
        default=16,
    )

    args = parser.parse_args()

    query = RuntimeQuery(
        Path(
            args.index
        )
    )

    if args.command == "resolve":
        result = query.resolve(
            args.address
        )

    elif args.command == "search":
        result = query.search(
            args.query,
            record_type=args.type,
            limit=args.limit,
        )

    elif args.command == "filter":
        result = query.filter(
            args.field,
            args.operator,
            args.expected,
            limit=args.limit,
        )

    elif args.command == "traverse":
        result = query.traverse(
            args.start,
            relation=args.relation,
            depth=args.depth,
            direction=args.direction,
        )

    elif args.command == "path":
        result = query.path(
            args.start,
            args.end,
            relation=args.relation,
            max_depth=args.max_depth,
        )

    else:
        raise RuntimeQueryError(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )

    return (
        0
        if result.get(
            "passed",
            True,
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
