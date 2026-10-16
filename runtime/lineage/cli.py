#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

PACKAGE_ROOT = Path(
    __file__
).resolve().parents[2]

for candidate in (
    ROOT,
    PACKAGE_ROOT,
):
    if str(candidate) not in sys.path:
        sys.path.insert(
            0,
            str(candidate),
        )


from runtime.lineage.engine import (  # noqa: E402
    LineageGraph,
    compile_lineage,
    write_projection,
)

from runtime.lineage.model import (  # noqa: E402
    LineageError,
)

from runtime.lineage.registry import (  # noqa: E402
    DEFAULT_ROLE_REGISTRY,
    LineageRoleRegistry,
)


DEFAULT_INPUT = (
    ROOT
    / "ontology"
    / "obelisks"
    / "segue"
    / "authority_graph"
)

DEFAULT_OUTPUT = (
    ROOT
    / "vault"
    / "lineage"
    / "functional_lineage_graph.json"
)


def _json(
    value: Any,
) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _load_projection(
    path: Path,
    registry_path: Path,
) -> LineageGraph:
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    registry = LineageRoleRegistry.load(
        registry_path
    )

    return LineageGraph.from_projection(
        payload,
        registry=registry,
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile, validate, query, "
            "and resolve Savant "
            "functional lineage."
        )
    )

    parser.add_argument(
        "--roles",
        type=Path,
        default=DEFAULT_ROLE_REGISTRY,
        help=(
            "authoritative lineage "
            "role registry"
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    compile_parser = sub.add_parser(
        "compile"
    )

    compile_parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[
            DEFAULT_INPUT
        ],
    )

    compile_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    compile_parser.add_argument(
        "--include-legacy",
        action="store_true",
    )

    compile_parser.add_argument(
        "--strict",
        action="store_true",
    )

    validate_parser = sub.add_parser(
        "validate"
    )

    validate_parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[
            DEFAULT_INPUT
        ],
    )

    validate_parser.add_argument(
        "--include-legacy",
        action="store_true",
    )

    validate_parser.add_argument(
        "--strict",
        action="store_true",
    )

    query_parser = sub.add_parser(
        "query"
    )

    query_parser.add_argument(
        "node"
    )

    query_parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    query_parser.add_argument(
        "--role",
        action="append",
        default=None,
    )

    impact_parser = sub.add_parser(
        "impact"
    )

    impact_parser.add_argument(
        "nodes",
        nargs="+",
    )

    impact_parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    impact_parser.add_argument(
        "--channel",
        default="regeneration",
    )

    resolve_parser = sub.add_parser(
        "resolve"
    )

    resolve_parser.add_argument(
        "node"
    )

    resolve_parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    resolve_parser.add_argument(
        "--shallow",
        action="store_true",
    )

    roles_parser = sub.add_parser(
        "roles"
    )

    roles_parser.add_argument(
        "--symbolic",
        action="store_true",
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    try:
        if args.command in {
            "compile",
            "validate",
        }:
            graph = compile_lineage(
                args.inputs,
                role_registry=args.roles,
                include_legacy=(
                    args.include_legacy
                ),
            )

            report = graph.validate()

            if args.command == "validate":
                _json(
                    report
                )
            else:
                projection = write_projection(
                    graph,
                    args.output,
                )

                _json(
                    {
                        "output": str(
                            args.output
                        ),
                        "deterministic_hash": (
                            projection[
                                "deterministic_hash"
                            ]
                        ),
                        **report,
                    }
                )

            if (
                report["errors"]
                or (
                    args.strict
                    and report["warnings"]
                )
            ):
                return 1

            return 0

        if args.command == "roles":
            registry = (
                LineageRoleRegistry.load(
                    args.roles
                )
            )

            payload = registry.to_dict()

            if args.symbolic:
                payload = {
                    role.name: {
                        "parent": (
                            registry
                            .symbolic_parent_alias(
                                role.name
                            )
                        ),
                        "inverse": role.inverse,
                    }
                    for role
                    in registry.roles()
                }

            _json(
                payload
            )

            return 0

        graph = _load_projection(
            args.graph,
            args.roles,
        )

        if args.command == "query":
            _json(
                {
                    "node": args.node,
                    "parents": graph.parents(
                        args.node,
                        roles=args.role,
                    ),
                    "children": graph.children(
                        args.node,
                        roles=args.role,
                    ),
                    "ancestors": graph.ancestors(
                        args.node,
                        roles=args.role,
                    ),
                    "descendants": graph.descendants(
                        args.node,
                        roles=args.role,
                    ),
                }
            )

            return 0

        if args.command == "impact":
            _json(
                {
                    "changed": sorted(
                        set(args.nodes)
                    ),
                    "channel": args.channel,
                    "affected": graph.affected_by(
                        args.nodes,
                        channel=args.channel,
                    ),
                }
            )

            return 0

        if args.command == "resolve":
            _json(
                graph.resolve_node(
                    args.node,
                    recursive=(
                        not args.shallow
                    ),
                )
            )

            return 0

    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        LineageError,
    ) as exc:
        print(
            f"lineage error: {exc}",
            file=sys.stderr,
        )

        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
