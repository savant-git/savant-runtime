#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml


RUNTIME_ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = RUNTIME_ROOT.parent

REGISTRY_PATH = (
    RUNTIME_ROOT
    / "runtime_registry.yaml"
)

COMPILED_ROOT = (
    RUNTIME_ROOT
    / "compiled"
)

ADDRESS_INDEX_PATH = (
    COMPILED_ROOT
    / "runtime_address_index.json"
)


class RuntimeAddressError(
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


def load_yaml(
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
        payload = yaml.safe_load(
            handle
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeAddressError(
            f"Expected object root: {path}"
        )

    return payload


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
        raise RuntimeAddressError(
            f"Expected object root: {path}"
        )

    return payload


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def normalize_address(
    value: str,
) -> str:
    return str(
        value
    ).strip()


class RuntimeAddressIndex:

    def __init__(
        self,
    ) -> None:
        registry = load_yaml(
            REGISTRY_PATH
        )

        runtime = registry.get(
            "runtime"
        )

        if not isinstance(
            runtime,
            dict,
        ):
            raise RuntimeAddressError(
                "runtime registry entry missing"
            )

        subsystems = runtime.get(
            "subsystems",
            {}
        )

        if not isinstance(
            subsystems,
            dict,
        ):
            raise RuntimeAddressError(
                "runtime.subsystems must be an object"
            )

        self.registry = registry
        self.runtime = runtime
        self.subsystems = subsystems

        self.execution_order = [
            normalize_address(
                item
            )
            for item in runtime.get(
                "execution_order",
                [],
            )
            if normalize_address(
                item
            )
        ]

    def add_record(
        self,
        records: dict[str, dict[str, Any]],
        aliases: dict[str, str],
        record: dict[str, Any],
    ) -> None:
        address = normalize_address(
            record.get(
                "address",
                "",
            )
        )

        if not address:
            raise RuntimeAddressError(
                "Record address missing"
            )

        if address in records:
            raise RuntimeAddressError(
                f"Duplicate address: {address}"
            )

        record = dict(
            record
        )

        record[
            "address"
        ] = address

        record[
            "digest"
        ] = digest(
            {
                key: value
                for key, value
                in record.items()
                if key != "digest"
            }
        )

        records[
            address
        ] = record

        for alias in record.get(
            "aliases",
            [],
        ):
            alias = normalize_address(
                alias
            )

            if not alias:
                continue

            existing = aliases.get(
                alias
            )

            if (
                existing is not None
                and existing != address
            ):
                raise RuntimeAddressError(
                    f"Alias collision: {alias}"
                )

            aliases[
                alias
            ] = address

    def build(
        self,
    ) -> dict[str, Any]:
        records: dict[
            str,
            dict[str, Any],
        ] = {}

        aliases: dict[
            str,
            str,
        ] = {}

        runtime_id = normalize_address(
            self.runtime.get(
                "id",
                "runtime:savant:lexicon",
            )
        )

        self.add_record(
            records,
            aliases,
            {
                "address": runtime_id,
                "type": "runtime",
                "canonical": self.runtime.get(
                    "canonical"
                ),
                "status": self.runtime.get(
                    "status"
                ),
                "version": self.runtime.get(
                    "version"
                ),
                "authority": self.runtime.get(
                    "authority"
                ),
                "source": str(
                    REGISTRY_PATH
                ),
                "aliases": [
                    "runtime",
                    "runtime:root",
                    "savant:runtime",
                ],
                "relationships": {
                    "contains": [
                        normalize_address(
                            self.subsystems[
                                subsystem
                            ].get(
                                "id",
                                (
                                    "runtime:"
                                    "subsystem:"
                                    f"{subsystem}"
                                ),
                            )
                        )
                        for subsystem
                        in self.execution_order
                    ]
                },
            },
        )

        previous_address: str | None = None

        for position, subsystem in enumerate(
            self.execution_order
        ):
            entry = self.subsystems.get(
                subsystem,
                {}
            )

            if not isinstance(
                entry,
                dict,
            ):
                raise RuntimeAddressError(
                    f"Invalid subsystem record: {subsystem}"
                )

            subsystem_address = normalize_address(
                entry.get(
                    "id",
                    (
                        "runtime:"
                        "subsystem:"
                        f"{subsystem}"
                    ),
                )
            )

            controller_relative = normalize_address(
                entry.get(
                    "controller",
                    "",
                )
            )

            controller_path = (
                LEXICON_ROOT
                / controller_relative
            )

            relationships: dict[
                str,
                list[str],
            ] = {
                "contained_by": [
                    runtime_id
                ],
                "depends_on": [],
                "precedes": [],
                "follows": [],
            }

            if previous_address is not None:
                relationships[
                    "follows"
                ].append(
                    previous_address
                )

                records[
                    previous_address
                ][
                    "relationships"
                ][
                    "precedes"
                ].append(
                    subsystem_address
                )

            self.add_record(
                records,
                aliases,
                {
                    "address": subsystem_address,
                    "type": (
                        "runtime_subsystem"
                    ),
                    "canonical": subsystem,
                    "position": position,
                    "required": bool(
                        entry.get(
                            "required",
                            True,
                        )
                    ),
                    "controller": (
                        controller_relative
                    ),
                    "controller_path": str(
                        controller_path
                    ),
                    "controller_exists": (
                        controller_path.is_file()
                    ),
                    "controller_executable": (
                        controller_path.is_file()
                        and os.access(
                            controller_path,
                            os.X_OK,
                        )
                    ),
                    "actions": entry.get(
                        "actions",
                        {},
                    ),
                    "source": str(
                        REGISTRY_PATH
                    ),
                    "aliases": [
                        subsystem,
                        f"subsystem:{subsystem}",
                        f"runtime:{subsystem}",
                    ],
                    "relationships": relationships,
                },
            )

            previous_address = subsystem_address

        for dependency in self.runtime.get(
            "dependencies",
            [],
        ):
            dependency_address = normalize_address(
                dependency
            )

            if not dependency_address:
                continue

            if dependency_address not in records:
                self.add_record(
                    records,
                    aliases,
                    {
                        "address": dependency_address,
                        "type": (
                            "external_dependency"
                        ),
                        "canonical": (
                            dependency_address
                        ),
                        "source": str(
                            REGISTRY_PATH
                        ),
                        "aliases": [],
                        "relationships": {
                            "required_by": [
                                runtime_id
                            ]
                        },
                    },
                )

            records[
                runtime_id
            ][
                "relationships"
            ].setdefault(
                "depends_on",
                [],
            ).append(
                dependency_address
            )

        for record in records.values():
            relationships = record.get(
                "relationships",
                {}
            )

            if isinstance(
                relationships,
                dict,
            ):
                for relation, targets in (
                    relationships.items()
                ):
                    if isinstance(
                        targets,
                        list,
                    ):
                        relationships[
                            relation
                        ] = sorted(
                            set(
                                normalize_address(
                                    target
                                )
                                for target
                                in targets
                                if normalize_address(
                                    target
                                )
                            )
                        )

            record[
                "digest"
            ] = digest(
                {
                    key: value
                    for key, value
                    in record.items()
                    if key != "digest"
                }
            )

        ordered_records = {
            address: records[
                address
            ]
            for address
            in sorted(
                records
            )
        }

        ordered_aliases = {
            alias: aliases[
                alias
            ]
            for alias
            in sorted(
                aliases
            )
        }

        payload = {
            "index_id": (
                "runtime:index:address"
            ),
            "version": "1.0.0",
            "runtime": runtime_id,
            "record_count": len(
                ordered_records
            ),
            "alias_count": len(
                ordered_aliases
            ),
            "records": ordered_records,
            "aliases": ordered_aliases,
            "provenance": {
                "source": str(
                    REGISTRY_PATH
                ),
                "generator": str(
                    Path(
                        __file__
                    ).resolve()
                ),
            },
            "lineage": {
                "derived_from": [
                    runtime_id,
                    str(
                        REGISTRY_PATH
                    ),
                ]
            },
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def materialize(
        self,
    ) -> dict[str, Any]:
        payload = self.build()

        write_json(
            ADDRESS_INDEX_PATH,
            payload,
        )

        return {
            "operation": "materialize",
            "passed": True,
            "path": str(
                ADDRESS_INDEX_PATH
            ),
            "record_count": payload[
                "record_count"
            ],
            "alias_count": payload[
                "alias_count"
            ],
            "digest": payload[
                "digest"
            ],
        }


def resolve_address(
    query: str,
    index: dict[str, Any],
) -> dict[str, Any]:
    query = normalize_address(
        query
    )

    records = index.get(
        "records",
        {}
    )

    aliases = index.get(
        "aliases",
        {}
    )

    if not isinstance(
        records,
        dict,
    ):
        raise RuntimeAddressError(
            "Invalid address index records"
        )

    if not isinstance(
        aliases,
        dict,
    ):
        raise RuntimeAddressError(
            "Invalid address index aliases"
        )

    canonical = query

    if query not in records:
        canonical = normalize_address(
            aliases.get(
                query,
                "",
            )
        )

    record = records.get(
        canonical
    )

    if not isinstance(
        record,
        dict,
    ):
        return {
            "operation": "resolve",
            "passed": False,
            "query": query,
            "resolved": False,
            "address": None,
            "record": None,
        }

    return {
        "operation": "resolve",
        "passed": True,
        "query": query,
        "resolved": True,
        "address": canonical,
        "record": record,
    }


def related_records(
    query: str,
    relation: str | None,
    index: dict[str, Any],
) -> dict[str, Any]:
    resolution = resolve_address(
        query,
        index,
    )

    if not resolution[
        "resolved"
    ]:
        return {
            "operation": "related",
            "passed": False,
            "query": query,
            "relation": relation,
            "resolved": False,
            "records": [],
        }

    record = resolution[
        "record"
    ]

    relationships = record.get(
        "relationships",
        {}
    )

    if not isinstance(
        relationships,
        dict,
    ):
        relationships = {}

    selected: dict[
        str,
        list[str],
    ]

    if relation is None:
        selected = {
            key: value
            for key, value
            in relationships.items()
            if isinstance(
                value,
                list,
            )
        }
    else:
        values = relationships.get(
            relation,
            []
        )

        selected = {
            relation: (
                values
                if isinstance(
                    values,
                    list,
                )
                else []
            )
        }

    records = index.get(
        "records",
        {}
    )

    results = []

    for relation_name in sorted(
        selected
    ):
        for target in selected[
            relation_name
        ]:
            results.append(
                {
                    "relation": relation_name,
                    "address": target,
                    "record": records.get(
                        target
                    ),
                }
            )

    return {
        "operation": "related",
        "passed": True,
        "query": query,
        "address": resolution[
            "address"
        ],
        "relation": relation,
        "count": len(
            results
        ),
        "records": results,
    }


def ensure_index() -> dict[str, Any]:
    if not ADDRESS_INDEX_PATH.is_file():
        RuntimeAddressIndex().materialize()

    return load_json(
        ADDRESS_INDEX_PATH
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "build"
    )

    subparsers.add_parser(
        "materialize"
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "address"
    )

    related_parser = subparsers.add_parser(
        "related"
    )

    related_parser.add_argument(
        "address"
    )

    related_parser.add_argument(
        "--relation"
    )

    subparsers.add_parser(
        "list"
    )

    args = parser.parse_args()

    if args.command == "build":
        result = RuntimeAddressIndex().build()

    elif args.command == "materialize":
        result = RuntimeAddressIndex().materialize()

    elif args.command == "resolve":
        result = resolve_address(
            args.address,
            ensure_index(),
        )

    elif args.command == "related":
        result = related_records(
            args.address,
            args.relation,
            ensure_index(),
        )

    elif args.command == "list":
        index = ensure_index()

        result = {
            "operation": "list",
            "passed": True,
            "count": index.get(
                "record_count",
                0,
            ),
            "addresses": sorted(
                index.get(
                    "records",
                    {}
                )
            ),
        }

    else:
        raise RuntimeAddressError(
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
