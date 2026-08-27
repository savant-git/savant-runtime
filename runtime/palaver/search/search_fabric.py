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
).expanduser().absolute()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphError,
    RuntimeGraphIndex,
)


DEFAULT_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)


def _authority_value(
    raw: str,
) -> bool | None:
    normalized = str(
        raw
    ).strip().casefold()

    if normalized == "any":
        return None

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        "authority must be any, "
        "true, or false"
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search and traverse the "
            "role-bearing Savant "
            "runtime graph."
        )
    )

    parser.add_argument(
        "query",
        nargs="*",
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH,
    )

    parser.add_argument(
        "--kind",
        action="append",
        default=None,
    )

    parser.add_argument(
        "--role",
        action="append",
        default=None,
    )

    parser.add_argument(
        "--authority",
        choices=[
            "any",
            "true",
            "false",
        ],
        default="any",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--node",
        default=None,
    )

    parser.add_argument(
        "--direction",
        choices=[
            "parents",
            "children",
            "both",
        ],
        default="both",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--include-edges",
        action="store_true",
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    try:
        index = RuntimeGraphIndex.load(
            args.graph
        )

        query = " ".join(
            args.query
        ).strip()

        authority = (
            _authority_value(
                args.authority
            )
        )

        results = index.search(
            query,
            kinds=args.kind,
            roles=args.role,
            authority=authority,
            limit=max(
                0,
                args.limit,
            ),
        )

        payload: dict[
            str,
            Any,
        ] = {
            "schema": (
                "savant."
                "runtime_search.v2"
            ),
            "source": (
                "runtime_graph"
            ),
            "source_runtime_hash": (
                index.deterministic_hash
            ),
            "source_lineage_hash": (
                index.source_lineage_hash
            ),
            "query": query.casefold(),
            "filters": {
                "kinds": (
                    args.kind
                    or []
                ),
                "roles": (
                    args.role
                    or []
                ),
                "authority": (
                    args.authority
                ),
                "limit": max(
                    0,
                    args.limit,
                ),
            },
            "count": len(
                results
            ),
            "results": results,
        }

        if args.node:
            node_id = (
                index.resolve_node_id(
                    args.node
                )
            )

            payload[
                "node"
            ] = index.node(
                node_id
            )

            payload[
                "family"
            ] = index.family(
                node_id
            )

            payload[
                "traversal"
            ] = index.traverse(
                node_id,
                direction=(
                    args.direction
                ),
                roles=args.role,
                max_depth=max(
                    0,
                    args.depth,
                ),
                include_start=True,
            )

            if args.include_edges:
                payload[
                    "incoming_edges"
                ] = index.incoming_edges(
                    node_id,
                    roles=args.role,
                    active_only=False,
                )

                payload[
                    "outgoing_edges"
                ] = index.outgoing_edges(
                    node_id,
                    roles=args.role,
                    active_only=False,
                )

        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except (
        OSError,
        UnicodeError,
        ValueError,
        RuntimeGraphError,
    ) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(
                        exc
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
