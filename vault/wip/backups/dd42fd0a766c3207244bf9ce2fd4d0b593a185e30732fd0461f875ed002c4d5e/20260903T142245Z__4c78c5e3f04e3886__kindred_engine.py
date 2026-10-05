#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "kindred_registry.yaml"


class KindredError(Exception):
    pass


class KindredEngine:
    def __init__(
        self,
        registry_path: Path | str = DEFAULT_REGISTRY,
    ) -> None:
        self.registry_path = Path(
            registry_path
        ).expanduser().resolve()

        self.data = self._load_yaml(
            self.registry_path
        )

        self.kindreds: dict[str, dict[str, Any]] = {}
        self.member_index: dict[str, set[str]] = defaultdict(set)
        self.parent_graph: dict[str, set[str]] = defaultdict(set)
        self.child_graph: dict[str, set[str]] = defaultdict(set)
        self.dependency_graph: dict[str, set[str]] = defaultdict(set)

        self._build_indexes()

    def _load_yaml(
        self,
        path: Path,
    ) -> dict[str, Any]:
        if not path.exists():
            raise KindredError(
                f"Registry not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = yaml.safe_load(handle)

        if not isinstance(data, dict):
            raise KindredError(
                "Kindred registry root must be an object."
            )

        return data

    def _build_indexes(self) -> None:
        raw_kindreds = self.data.get(
            "kindreds",
            [],
        )

        if not isinstance(raw_kindreds, list):
            raise KindredError(
                "kindreds must be a list."
            )

        for record in raw_kindreds:
            if not isinstance(record, dict):
                continue

            kindred_id = str(
                record.get("id", "")
            ).strip()

            if not kindred_id:
                continue

            self.kindreds[kindred_id] = record

        for kindred_id, record in self.kindreds.items():
            for member in self._string_list(
                record.get("members")
            ):
                self.member_index[member].add(
                    kindred_id
                )

            for parent in self._string_list(
                record.get("parents")
            ):
                self.parent_graph[kindred_id].add(
                    parent
                )

                self.child_graph[parent].add(
                    kindred_id
                )

            for child in self._string_list(
                record.get("children")
            ):
                self.child_graph[kindred_id].add(
                    child
                )

                self.parent_graph[child].add(
                    kindred_id
                )

            for dependency in self._string_list(
                record.get("dependencies")
            ):
                self.dependency_graph[
                    kindred_id
                ].add(dependency)

    def get(
        self,
        kindred_id: str,
    ) -> dict[str, Any]:
        try:
            return self.kindreds[kindred_id]
        except KeyError as exc:
            raise KindredError(
                f"Unknown kindred: {kindred_id}"
            ) from exc

    def members(
        self,
        kindred_id: str,
        recursive: bool = False,
    ) -> list[str]:
        record = self.get(kindred_id)

        members = set(
            self._string_list(
                record.get("members")
            )
        )

        if recursive:
            for descendant in self.descendants(
                kindred_id
            ):
                descendant_record = self.get(
                    descendant
                )

                members.update(
                    self._string_list(
                        descendant_record.get(
                            "members"
                        )
                    )
                )

        return sorted(members)

    def memberships(
        self,
        member_id: str,
        inherited: bool = True,
    ) -> list[str]:
        memberships = set(
            self.member_index.get(
                member_id,
                set(),
            )
        )

        if inherited:
            inherited_memberships: set[str] = set()

            for kindred_id in memberships:
                inherited_memberships.update(
                    self.ancestors(kindred_id)
                )

            memberships.update(
                inherited_memberships
            )

        return sorted(memberships)

    def ancestors(
        self,
        kindred_id: str,
    ) -> list[str]:
        self.get(kindred_id)

        return self._walk(
            kindred_id,
            self.parent_graph,
        )

    def descendants(
        self,
        kindred_id: str,
    ) -> list[str]:
        self.get(kindred_id)

        return self._walk(
            kindred_id,
            self.child_graph,
        )

    def dependencies(
        self,
        kindred_id: str,
        recursive: bool = False,
    ) -> list[str]:
        self.get(kindred_id)

        if not recursive:
            return sorted(
                self.dependency_graph.get(
                    kindred_id,
                    set(),
                )
            )

        return self._walk(
            kindred_id,
            self.dependency_graph,
        )

    def relationship_edges(
        self,
        kindred_id: str,
    ) -> list[dict[str, Any]]:
        record = self.get(kindred_id)

        edges: list[dict[str, Any]] = []

        for relationship in record.get(
            "relationships",
            [],
        ):
            if isinstance(relationship, str):
                edges.append(
                    {
                        "type": "related_to",
                        "source": kindred_id,
                        "target": relationship,
                    }
                )

            elif isinstance(
                relationship,
                dict,
            ):
                edges.append(
                    {
                        "type": relationship.get(
                            "type",
                            "related_to",
                        ),
                        "source": kindred_id,
                        "target": relationship.get(
                            "target"
                        ),
                        "metadata": relationship.get(
                            "metadata",
                            {},
                        ),
                    }
                )

        return edges

    def graph(self) -> dict[str, Any]:
        nodes = [
            {
                "id": kindred_id,
                "canonical": record.get(
                    "canonical"
                ),
                "status": record.get("status"),
            }
            for kindred_id, record
            in sorted(self.kindreds.items())
        ]

        edges: list[dict[str, Any]] = []

        for source, targets in sorted(
            self.parent_graph.items()
        ):
            for target in sorted(targets):
                edges.append(
                    {
                        "type": "parent",
                        "source": source,
                        "target": target,
                    }
                )

        for source, targets in sorted(
            self.dependency_graph.items()
        ):
            for target in sorted(targets):
                edges.append(
                    {
                        "type": "depends_on",
                        "source": source,
                        "target": target,
                    }
                )

        for kindred_id in sorted(self.kindreds):
            edges.extend(
                self.relationship_edges(
                    kindred_id
                )
            )

        for member, kindreds in sorted(
            self.member_index.items()
        ):
            for kindred_id in sorted(kindreds):
                edges.append(
                    {
                        "type": "member_of",
                        "source": member,
                        "target": kindred_id,
                    }
                )

        return {
            "registry_id": self.data.get(
                "registry_id"
            ),
            "version": self.data.get(
                "version"
            ),
            "nodes": nodes,
            "edges": edges,
        }

    def _walk(
        self,
        start: str,
        graph: dict[str, set[str]],
    ) -> list[str]:
        visited: set[str] = set()
        queue = deque(
            sorted(
                graph.get(
                    start,
                    set(),
                )
            )
        )

        while queue:
            node = queue.popleft()

            if node in visited:
                continue

            visited.add(node)

            for target in sorted(
                graph.get(
                    node,
                    set(),
                )
            ):
                if target not in visited:
                    queue.append(target)

        return sorted(visited)

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []

        if isinstance(value, list):
            result: list[str] = []

            for item in value:
                text = str(item).strip()

                if text:
                    result.append(text)

            return result

        return [str(value).strip()]


def print_json(
    payload: Any,
) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kindred-engine"
    )

    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("kindred_id")

    members_parser = subparsers.add_parser(
        "members"
    )
    members_parser.add_argument("kindred_id")
    members_parser.add_argument(
        "--recursive",
        action="store_true",
    )

    memberships_parser = subparsers.add_parser(
        "memberships"
    )
    memberships_parser.add_argument("member_id")
    memberships_parser.add_argument(
        "--direct",
        action="store_true",
    )

    ancestors_parser = subparsers.add_parser(
        "ancestors"
    )
    ancestors_parser.add_argument("kindred_id")

    descendants_parser = subparsers.add_parser(
        "descendants"
    )
    descendants_parser.add_argument("kindred_id")

    dependencies_parser = subparsers.add_parser(
        "dependencies"
    )
    dependencies_parser.add_argument("kindred_id")
    dependencies_parser.add_argument(
        "--recursive",
        action="store_true",
    )

    subparsers.add_parser("graph")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    engine = KindredEngine(
        registry_path=args.registry
    )

    if args.command == "get":
        print_json(
            engine.get(args.kindred_id)
        )

    elif args.command == "members":
        print_json(
            engine.members(
                args.kindred_id,
                recursive=args.recursive,
            )
        )

    elif args.command == "memberships":
        print_json(
            engine.memberships(
                args.member_id,
                inherited=not args.direct,
            )
        )

    elif args.command == "ancestors":
        print_json(
            engine.ancestors(
                args.kindred_id
            )
        )

    elif args.command == "descendants":
        print_json(
            engine.descendants(
                args.kindred_id
            )
        )

    elif args.command == "dependencies":
        print_json(
            engine.dependencies(
                args.kindred_id,
                recursive=args.recursive,
            )
        )

    elif args.command == "graph":
        print_json(engine.graph())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
