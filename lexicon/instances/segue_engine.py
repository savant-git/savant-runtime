#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent

INSTANCE_REGISTRY = ROOT / "instance_registry.yaml"
SEGUE_REGISTRY = ROOT / "segue_registry.yaml"


class SegueEngine:

    def __init__(self) -> None:

        self.instances: dict[
            str,
            dict[str, Any],
        ] = {}

        self.segues: dict[
            str,
            dict[str, Any],
        ] = {}

        self.outgoing: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self.incoming: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self.relation_index: dict[
            str,
            list[str],
        ] = defaultdict(list)

        self.load()

    def load_yaml(
        self,
        path: Path,
    ) -> dict[str, Any]:

        if not path.exists():

            raise FileNotFoundError(
                str(path)
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            data = yaml.safe_load(
                handle
            )

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                f"Invalid YAML root: {path}"
            )

        return data

    def load(self) -> None:

        instance_data = self.load_yaml(
            INSTANCE_REGISTRY
        )

        segue_data = self.load_yaml(
            SEGUE_REGISTRY
        )

        for record in instance_data.get(
            "instances",
            [],
        ):

            if not isinstance(
                record,
                dict,
            ):

                continue

            instance_id = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if instance_id:

                self.instances[
                    instance_id
                ] = record

        for record in segue_data.get(
            "segues",
            [],
        ):

            if not isinstance(
                record,
                dict,
            ):

                continue

            segue_id = str(
                record.get(
                    "id",
                    "",
                )
            ).strip()

            if not segue_id:

                continue

            self.segues[
                segue_id
            ] = record

            source = str(
                record.get(
                    "from",
                    "",
                )
            ).strip()

            target = str(
                record.get(
                    "to",
                    "",
                )
            ).strip()

            relation = str(
                record.get(
                    "relation",
                    "",
                )
            ).strip()

            if source:

                self.outgoing[
                    source
                ].append(
                    segue_id
                )

            if target:

                self.incoming[
                    target
                ].append(
                    segue_id
                )

            if relation:

                self.relation_index[
                    relation
                ].append(
                    segue_id
                )

        for index in (
            self.outgoing,
            self.incoming,
            self.relation_index,
        ):

            for key in index:

                index[key] = sorted(
                    index[key]
                )

    def resolve(
        self,
        segue_id: str,
    ) -> dict[str, Any]:

        if segue_id not in self.segues:

            raise KeyError(
                segue_id
            )

        return self.segues[
            segue_id
        ]

    def normalize_context(
        self,
        context: Any,
    ) -> dict[str, Any]:

        if context is None:

            return {}

        if isinstance(
            context,
            dict,
        ):

            return context

        raise TypeError(
            "Context must be an object"
        )

    def resolve_path_value(
        self,
        context: dict[str, Any],
        path: str,
    ) -> Any:

        current: Any = context

        for part in path.split(
            "."
        ):

            if isinstance(
                current,
                dict,
            ) and part in current:

                current = current[
                    part
                ]

            else:

                return None

        return current

    def evaluate_condition(
        self,
        condition: Any,
        context: dict[str, Any],
    ) -> bool:

        if isinstance(
            condition,
            bool,
        ):

            return condition

        if isinstance(
            condition,
            str,
        ):

            value = self.resolve_path_value(
                context,
                condition,
            )

            return bool(
                value
            )

        if not isinstance(
            condition,
            dict,
        ):

            return False

        if "all" in condition:

            values = condition.get(
                "all"
            )

            if not isinstance(
                values,
                list,
            ):

                return False

            return all(
                self.evaluate_condition(
                    item,
                    context,
                )
                for item in values
            )

        if "any" in condition:

            values = condition.get(
                "any"
            )

            if not isinstance(
                values,
                list,
            ):

                return False

            return any(
                self.evaluate_condition(
                    item,
                    context,
                )
                for item in values
            )

        if "not" in condition:

            return not self.evaluate_condition(
                condition.get(
                    "not"
                ),
                context,
            )

        field = str(
            condition.get(
                "field",
                "",
            )
        ).strip()

        operator = str(
            condition.get(
                "operator",
                "equals",
            )
        ).strip()

        expected = condition.get(
            "value"
        )

        actual = self.resolve_path_value(
            context,
            field,
        )

        if operator == "equals":

            return actual == expected

        if operator == "not_equals":

            return actual != expected

        if operator == "exists":

            return actual is not None

        if operator == "missing":

            return actual is None

        if operator == "truthy":

            return bool(
                actual
            )

        if operator == "falsy":

            return not bool(
                actual
            )

        if operator == "contains":

            try:

                return expected in actual

            except TypeError:

                return False

        if operator == "in":

            try:

                return actual in expected

            except TypeError:

                return False

        if operator == "greater_than":

            try:

                return actual > expected

            except TypeError:

                return False

        if operator == "greater_than_or_equal":

            try:

                return actual >= expected

            except TypeError:

                return False

        if operator == "less_than":

            try:

                return actual < expected

            except TypeError:

                return False

        if operator == "less_than_or_equal":

            try:

                return actual <= expected

            except TypeError:

                return False

        return False

    def is_active(
        self,
        segue: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> bool:

        status = str(
            segue.get(
                "status",
                "active",
            )
        ).strip()

        if status != "active":

            return False

        conditions = segue.get(
            "conditions",
            [],
        )

        if not conditions:

            return True

        if not isinstance(
            conditions,
            list,
        ):

            return False

        normalized_context = (
            self.normalize_context(
                context
            )
        )

        return all(
            self.evaluate_condition(
                condition,
                normalized_context,
            )
            for condition in conditions
        )

    def edge_weight(
        self,
        segue: dict[str, Any],
    ) -> float:

        metadata = segue.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):

            return 1.0

        raw_weight = metadata.get(
            "weight",
            1.0,
        )

        try:

            weight = float(
                raw_weight
            )

        except (
            TypeError,
            ValueError,
        ):

            return 1.0

        if weight < 0:

            return 1.0

        return weight

    def neighbors(
        self,
        instance_id: str,
        context: dict[str, Any] | None = None,
        relation: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:

        if instance_id not in self.instances:

            raise KeyError(
                instance_id
            )

        segue_ids: list[str] = []

        if direction in {
            "outgoing",
            "both",
        }:

            segue_ids.extend(
                self.outgoing.get(
                    instance_id,
                    [],
                )
            )

        if direction in {
            "incoming",
            "both",
        }:

            segue_ids.extend(
                self.incoming.get(
                    instance_id,
                    [],
                )
            )

        results = []

        for segue_id in sorted(
            set(
                segue_ids
            )
        ):

            segue = self.segues[
                segue_id
            ]

            if relation and (
                segue.get(
                    "relation"
                ) != relation
            ):

                continue

            if not self.is_active(
                segue,
                context,
            ):

                continue

            source = segue.get(
                "from"
            )

            target = segue.get(
                "to"
            )

            if source == instance_id:

                neighbor = target

                traversal = "forward"

            else:

                neighbor = source

                traversal = "reverse"

            results.append(
                {
                    "instance": neighbor,
                    "segue": segue_id,
                    "relation": segue.get(
                        "relation"
                    ),
                    "traversal": traversal,
                    "weight": self.edge_weight(
                        segue
                    ),
                }
            )

        return results

    def traverse(
        self,
        start: str,
        depth: int = 1,
        context: dict[str, Any] | None = None,
        relation: str | None = None,
        direction: str = "outgoing",
    ) -> dict[str, Any]:

        if start not in self.instances:

            raise KeyError(
                start
            )

        queue = deque(
            [
                (
                    start,
                    0,
                )
            ]
        )

        visited = {
            start
        }

        nodes = []

        edges = []

        while queue:

            current, level = queue.popleft()

            nodes.append(
                {
                    "id": current,
                    "depth": level,
                    "record": self.instances[
                        current
                    ],
                }
            )

            if level >= depth:

                continue

            for neighbor in self.neighbors(
                current,
                context=context,
                relation=relation,
                direction=direction,
            ):

                edges.append(
                    {
                        "from": current,
                        "to": neighbor[
                            "instance"
                        ],
                        "segue": neighbor[
                            "segue"
                        ],
                        "relation": neighbor[
                            "relation"
                        ],
                        "traversal": neighbor[
                            "traversal"
                        ],
                        "weight": neighbor[
                            "weight"
                        ],
                    }
                )

                target = neighbor[
                    "instance"
                ]

                if target not in visited:

                    visited.add(
                        target
                    )

                    queue.append(
                        (
                            target,
                            level + 1,
                        )
                    )

        return {
            "start": start,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
        }

    def shortest_path(
        self,
        start: str,
        target: str,
        context: dict[str, Any] | None = None,
        relation: str | None = None,
        direction: str = "outgoing",
    ) -> dict[str, Any] | None:

        if start not in self.instances:

            raise KeyError(
                start
            )

        if target not in self.instances:

            raise KeyError(
                target
            )

        queue: list[
            tuple[
                float,
                str,
                list[str],
                list[str],
            ]
        ] = [
            (
                0.0,
                start,
                [start],
                [],
            )
        ]

        best: dict[
            str,
            float,
        ] = {
            start: 0.0
        }

        while queue:

            cost, current, nodes, segues = (
                heapq.heappop(
                    queue
                )
            )

            if current == target:

                return {
                    "start": start,
                    "target": target,
                    "cost": cost,
                    "instances": nodes,
                    "segues": segues,
                }

            if cost > best.get(
                current,
                float("inf"),
            ):

                continue

            for neighbor in self.neighbors(
                current,
                context=context,
                relation=relation,
                direction=direction,
            ):

                next_node = neighbor[
                    "instance"
                ]

                next_cost = (
                    cost
                    + neighbor["weight"]
                )

                if next_cost >= best.get(
                    next_node,
                    float("inf"),
                ):

                    continue

                best[
                    next_node
                ] = next_cost

                heapq.heappush(
                    queue,
                    (
                        next_cost,
                        next_node,
                        [
                            *nodes,
                            next_node,
                        ],
                        [
                            *segues,
                            neighbor[
                                "segue"
                            ],
                        ],
                    ),
                )

        return None

    def paths(
        self,
        start: str,
        target: str,
        max_depth: int = 8,
        context: dict[str, Any] | None = None,
        relation: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:

        if start not in self.instances:

            raise KeyError(
                start
            )

        if target not in self.instances:

            raise KeyError(
                target
            )

        results = []

        stack = [
            (
                start,
                [start],
                [],
                0.0,
            )
        ]

        while stack:

            (
                current,
                node_path,
                segue_path,
                cost,
            ) = stack.pop()

            if (
                len(
                    segue_path
                )
                > max_depth
            ):

                continue

            if current == target:

                results.append(
                    {
                        "instances": node_path,
                        "segues": segue_path,
                        "cost": cost,
                    }
                )

                continue

            if (
                len(
                    segue_path
                )
                == max_depth
            ):

                continue

            neighbors = self.neighbors(
                current,
                context=context,
                relation=relation,
                direction=direction,
            )

            for neighbor in reversed(
                neighbors
            ):

                next_node = neighbor[
                    "instance"
                ]

                if next_node in node_path:

                    continue

                stack.append(
                    (
                        next_node,
                        [
                            *node_path,
                            next_node,
                        ],
                        [
                            *segue_path,
                            neighbor[
                                "segue"
                            ],
                        ],
                        (
                            cost
                            + neighbor[
                                "weight"
                            ]
                        ),
                    )
                )

        return sorted(
            results,
            key=lambda record: (
                record[
                    "cost"
                ],
                len(
                    record[
                        "segues"
                    ]
                ),
                record[
                    "instances"
                ],
            ),
        )

    def apply_effect(
        self,
        state: dict[str, Any],
        effect: Any,
    ) -> None:

        if not isinstance(
            effect,
            dict,
        ):

            return

        operation = str(
            effect.get(
                "operation",
                "set",
            )
        ).strip()

        path = str(
            effect.get(
                "field",
                "",
            )
        ).strip()

        if not path:

            return

        parts = path.split(
            "."
        )

        cursor = state

        for part in parts[:-1]:

            child = cursor.get(
                part
            )

            if not isinstance(
                child,
                dict,
            ):

                child = {}

                cursor[
                    part
                ] = child

            cursor = child

        key = parts[-1]

        if operation == "set":

            cursor[
                key
            ] = effect.get(
                "value"
            )

        elif operation == "delete":

            cursor.pop(
                key,
                None,
            )

        elif operation == "append":

            value = cursor.get(
                key
            )

            if not isinstance(
                value,
                list,
            ):

                value = []

                cursor[
                    key
                ] = value

            value.append(
                effect.get(
                    "value"
                )
            )

        elif operation == "increment":

            current = cursor.get(
                key,
                0,
            )

            amount = effect.get(
                "value",
                1,
            )

            try:

                cursor[
                    key
                ] = current + amount

            except TypeError:

                return

    def execute(
        self,
        segue_id: str,
        context: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        segue = self.resolve(
            segue_id
        )

        normalized_context = (
            self.normalize_context(
                context
            )
        )

        if not self.is_active(
            segue,
            normalized_context,
        ):

            return {
                "executed": False,
                "segue": segue_id,
                "reason": (
                    "inactive_or_conditions_failed"
                ),
                "state": (
                    state
                    if isinstance(
                        state,
                        dict,
                    )
                    else {}
                ),
            }

        resulting_state = (
            dict(
                state
            )
            if isinstance(
                state,
                dict,
            )
            else {}
        )

        effects = segue.get(
            "effects",
            [],
        )

        if isinstance(
            effects,
            list,
        ):

            for effect in effects:

                self.apply_effect(
                    resulting_state,
                    effect,
                )

        return {
            "executed": True,
            "segue": segue_id,
            "from": segue.get(
                "from"
            ),
            "to": segue.get(
                "to"
            ),
            "relation": segue.get(
                "relation"
            ),
            "state": resulting_state,
        }

    def graph(
        self,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        nodes = [
            {
                "id": instance_id,
                "canonical": record.get(
                    "canonical"
                ),
                "status": record.get(
                    "status",
                    "active",
                ),
            }
            for instance_id, record
            in sorted(
                self.instances.items()
            )
        ]

        edges = []

        for segue_id, record in sorted(
            self.segues.items()
        ):

            edges.append(
                {
                    "id": segue_id,
                    "from": record.get(
                        "from"
                    ),
                    "to": record.get(
                        "to"
                    ),
                    "relation": record.get(
                        "relation"
                    ),
                    "direction": record.get(
                        "direction",
                        "directed",
                    ),
                    "weight": self.edge_weight(
                        record
                    ),
                    "active": self.is_active(
                        record,
                        context,
                    ),
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def snapshot(
        self,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        graph = self.graph(
            context
        )

        digest = hashlib.sha256(
            json.dumps(
                graph,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return {
            "instances": len(
                self.instances
            ),
            "segues": len(
                self.segues
            ),
            "relations": len(
                self.relation_index
            ),
            "digest": digest,
        }

    def project(
        self,
        output: Path,
        context: dict[str, Any] | None = None,
    ) -> None:

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        payloads = {
            "segue_graph.json": (
                self.graph(
                    context
                )
            ),
            "segue_snapshot.json": (
                self.snapshot(
                    context
                )
            ),
            "outgoing_index.json": {
                key: value
                for key, value
                in sorted(
                    self.outgoing.items()
                )
            },
            "incoming_index.json": {
                key: value
                for key, value
                in sorted(
                    self.incoming.items()
                )
            },
            "relation_index.json": {
                key: value
                for key, value
                in sorted(
                    self.relation_index.items()
                )
            },
        }

        for filename, payload in payloads.items():

            target = output / filename
            temporary = output / (
                f".{filename}.tmp"
            )

            temporary.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            os.replace(
                temporary,
                target,
            )


def load_json_argument(
    value: str | None,
) -> dict[str, Any]:

    if not value:

        return {}

    path = Path(
        value
    )

    if path.exists():

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    else:

        data = json.loads(
            value
        )

    if not isinstance(
        data,
        dict,
    ):

        raise TypeError(
            "JSON argument must be an object"
        )

    return data


def main() -> int:

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    resolve_parser = subparsers.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "segue_id"
    )

    neighbors_parser = subparsers.add_parser(
        "neighbors"
    )

    neighbors_parser.add_argument(
        "instance_id"
    )

    neighbors_parser.add_argument(
        "--relation"
    )

    neighbors_parser.add_argument(
        "--direction",
        choices=[
            "outgoing",
            "incoming",
            "both",
        ],
        default="outgoing",
    )

    neighbors_parser.add_argument(
        "--context"
    )

    traverse_parser = subparsers.add_parser(
        "traverse"
    )

    traverse_parser.add_argument(
        "start"
    )

    traverse_parser.add_argument(
        "--depth",
        type=int,
        default=1,
    )

    traverse_parser.add_argument(
        "--relation"
    )

    traverse_parser.add_argument(
        "--direction",
        choices=[
            "outgoing",
            "incoming",
            "both",
        ],
        default="outgoing",
    )

    traverse_parser.add_argument(
        "--context"
    )

    path_parser = subparsers.add_parser(
        "path"
    )

    path_parser.add_argument(
        "start"
    )

    path_parser.add_argument(
        "target"
    )

    path_parser.add_argument(
        "--relation"
    )

    path_parser.add_argument(
        "--direction",
        choices=[
            "outgoing",
            "incoming",
            "both",
        ],
        default="outgoing",
    )

    path_parser.add_argument(
        "--context"
    )

    paths_parser = subparsers.add_parser(
        "paths"
    )

    paths_parser.add_argument(
        "start"
    )

    paths_parser.add_argument(
        "target"
    )

    paths_parser.add_argument(
        "--max-depth",
        type=int,
        default=8,
    )

    paths_parser.add_argument(
        "--relation"
    )

    paths_parser.add_argument(
        "--direction",
        choices=[
            "outgoing",
            "incoming",
            "both",
        ],
        default="outgoing",
    )

    paths_parser.add_argument(
        "--context"
    )

    execute_parser = subparsers.add_parser(
        "execute"
    )

    execute_parser.add_argument(
        "segue_id"
    )

    execute_parser.add_argument(
        "--context"
    )

    execute_parser.add_argument(
        "--state"
    )

    graph_parser = subparsers.add_parser(
        "graph"
    )

    graph_parser.add_argument(
        "--context"
    )

    snapshot_parser = subparsers.add_parser(
        "snapshot"
    )

    snapshot_parser.add_argument(
        "--context"
    )

    project_parser = subparsers.add_parser(
        "project"
    )

    project_parser.add_argument(
        "--output",
        default=str(
            ROOT
            / "runtime"
            / "segues"
        ),
    )

    project_parser.add_argument(
        "--context"
    )

    args = parser.parse_args()

    engine = SegueEngine()

    if args.command == "resolve":

        result = engine.resolve(
            args.segue_id
        )

    elif args.command == "neighbors":

        result = engine.neighbors(
            args.instance_id,
            context=load_json_argument(
                args.context
            ),
            relation=args.relation,
            direction=args.direction,
        )

    elif args.command == "traverse":

        result = engine.traverse(
            args.start,
            depth=args.depth,
            context=load_json_argument(
                args.context
            ),
            relation=args.relation,
            direction=args.direction,
        )

    elif args.command == "path":

        result = engine.shortest_path(
            args.start,
            args.target,
            context=load_json_argument(
                args.context
            ),
            relation=args.relation,
            direction=args.direction,
        )

    elif args.command == "paths":

        result = engine.paths(
            args.start,
            args.target,
            max_depth=args.max_depth,
            context=load_json_argument(
                args.context
            ),
            relation=args.relation,
            direction=args.direction,
        )

    elif args.command == "execute":

        result = engine.execute(
            args.segue_id,
            context=load_json_argument(
                args.context
            ),
            state=load_json_argument(
                args.state
            ),
        )

    elif args.command == "graph":

        result = engine.graph(
            load_json_argument(
                args.context
            )
        )

    elif args.command == "snapshot":

        result = engine.snapshot(
            load_json_argument(
                args.context
            )
        )

    elif args.command == "project":

        engine.project(
            Path(
                args.output
            ),
            context=load_json_argument(
                args.context
            ),
        )

        result = {
            "projected": True,
            "output": str(
                Path(
                    args.output
                ).resolve()
            ),
        }

    else:

        raise RuntimeError(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
