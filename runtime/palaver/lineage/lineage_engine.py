#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import (
    datetime,
    timezone,
)
import json
import os
from pathlib import Path
import sys
from typing import (
    Any,
    Iterable,
)


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().resolve()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.lineage.adapters import (  # noqa: E402
    ingest_authority_roots,
    ingest_canon_system,
    ingest_filesystem,
)

from runtime.lineage.engine import (  # noqa: E402
    LineageGraph,
    write_projection,
)

from runtime.lineage.projection import (  # noqa: E402
    family_projection,
)

from runtime.lineage.registry import (  # noqa: E402
    DEFAULT_ROLE_REGISTRY,
    LineageRoleRegistry,
)


def _filesystem_legacy_id(
    graph: LineageGraph,
    node_id: str,
) -> str:
    payload = graph.nodes.get(
        node_id,
        {},
    )

    legacy = payload.get(
        "legacy_id"
    )

    if (
        isinstance(
            legacy,
            str,
        )
        and legacy
    ):
        return legacy

    return node_id


def _filesystem_chain(
    graph: LineageGraph,
    node_id: str,
) -> list[str]:
    chain: list[str] = []
    current = node_id
    seen: set[str] = set()

    while current not in seen:
        seen.add(
            current
        )

        chain.append(
            _filesystem_legacy_id(
                graph,
                current,
            )
        )

        parents = (
            graph.incoming_bindings(
                current,
                roles=[
                    "composition"
                ],
            )
        )

        filesystem_parents = [
            binding.parent
            for binding in parents
            if binding.scope
            == "filesystem"
        ]

        if not filesystem_parents:
            break

        current = (
            filesystem_parents[0]
        )

    return chain


def _compatibility_index(
    graph: LineageGraph,
    *,
    generated_at: str,
    deterministic_hash: str,
    adapter_report: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    records: list[
        dict[str, Any]
    ] = []

    role_counts: Counter[
        str
    ] = Counter()

    axis_counts: Counter[
        str
    ] = Counter()

    continuation_counts: Counter[
        str
    ] = Counter()

    for binding in (
        graph.bindings.values()
    ):
        role_counts[
            binding.role
        ] += 1

        axis_counts[
            binding.axis
        ] += 1

        continuation_counts[
            binding.continuation
        ] += 1

    for node_id in sorted(
        graph.nodes
    ):
        payload = graph.nodes[
            node_id
        ]

        family = family_projection(
            graph,
            node_id,
        )

        records.append({
            "node": node_id,
            "legacy_node": (
                _filesystem_legacy_id(
                    graph,
                    node_id,
                )
            ),
            "kind": payload.get(
                "kind",
                "instance",
            ),
            "lineage": (
                _filesystem_chain(
                    graph,
                    node_id,
                )
                if node_id.startswith(
                    "fs:"
                )
                else family[
                    "parent_ids"
                ]
            ),
            "parents": family[
                "parent_ids"
            ],
            "mothers": family[
                "mothers"
            ],
            "fathers": family[
                "fathers"
            ],
            "children": family[
                "child_ids"
            ],
            "daughters": family[
                "daughters"
            ],
            "sons": family[
                "sons"
            ],
            "parent_roles": family[
                "parent_roles"
            ],
            "child_roles": family[
                "child_roles"
            ],
            "child_modes": family[
                "child_modes"
            ],
        })

    return {
        "schema": (
            "savant."
            "lineage_index.v2"
        ),
        "generated_at": (
            generated_at
        ),
        "deterministic_hash": (
            deterministic_hash
        ),
        "count": len(
            records
        ),
        "binding_count": len(
            graph.bindings
        ),
        "role_counts": dict(
            sorted(
                role_counts.items()
            )
        ),
        "axis_counts": dict(
            sorted(
                axis_counts.items()
            )
        ),
        "continuation_counts": dict(
            sorted(
                continuation_counts.items()
            )
        ),
        "adapters": adapter_report,
        "records": records,
    }


def build_runtime_lineage(
    *,
    root: Path | str = ROOT,
    role_registry: Path | str = (
        DEFAULT_ROLE_REGISTRY
    ),
    authority_roots: Iterable[
        Path | str
    ] | None = None,
    canon_roots: Iterable[
        Path | str
    ] | None = None,
    include_filesystem: bool = True,
    filesystem_limit: int = 0,
) -> tuple[
    LineageGraph,
    dict[str, Any],
]:
    runtime_root = Path(
        root
    ).expanduser().resolve()

    registry = (
        LineageRoleRegistry.load(
            role_registry
        )
    )

    graph = LineageGraph(
        registry
    )

    resolved_authority_roots = tuple(
        authority_roots
        if authority_roots is not None
        else (
            runtime_root
            / "authority_graph",

            runtime_root
            / "canon",

            runtime_root
            / "ontology",
        )
    )

    resolved_canon_roots = tuple(
        canon_roots
        if canon_roots is not None
        else (
            runtime_root
            / "canon-system"
            / "authority",
        )
    )

    adapter_report: dict[
        str,
        Any,
    ] = {}

    adapter_report[
        "authority"
    ] = ingest_authority_roots(
        graph,
        resolved_authority_roots,
    )

    try:
        adapter_report[
            "canon"
        ] = ingest_canon_system(
            graph,
            resolved_canon_roots,
        )
    except RuntimeError as exc:
        adapter_report[
            "canon"
        ] = {
            "documents": 0,
            "emitted": 0,
            "warning": str(exc),
        }

    if include_filesystem:
        adapter_report[
            "filesystem"
        ] = {
            "nodes": (
                ingest_filesystem(
                    graph,
                    runtime_root,
                    limit=(
                        filesystem_limit
                    ),
                )
            )
        }
    else:
        adapter_report[
            "filesystem"
        ] = {
            "nodes": 0,
            "disabled": True,
        }

    return (
        graph,
        adapter_report,
    )


def compile_runtime_lineage(
    *,
    root: Path | str = ROOT,
    role_registry: Path | str = (
        DEFAULT_ROLE_REGISTRY
    ),
    graph_output: Path | str | None = None,
    index_output: Path | str | None = None,
    include_filesystem: bool = True,
    filesystem_limit: int = 0,
) -> dict[str, Any]:
    runtime_root = Path(
        root
    ).expanduser().resolve()

    graph_target = Path(
        graph_output
        or (
            runtime_root
            / "vault"
            / "lineage"
            / (
                "functional_"
                "lineage_graph.json"
            )
        )
    )

    index_target = Path(
        index_output
        or (
            runtime_root
            / "vault"
            / "lineage"
            / "lineage_index.json"
        )
    )

    (
        graph,
        adapter_report,
    ) = build_runtime_lineage(
        root=runtime_root,
        role_registry=(
            role_registry
        ),
        include_filesystem=(
            include_filesystem
        ),
        filesystem_limit=(
            filesystem_limit
        ),
    )

    validation = graph.validate()

    projection = write_projection(
        graph,
        graph_target,
    )

    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    compatibility = (
        _compatibility_index(
            graph,
            generated_at=(
                generated_at
            ),
            deterministic_hash=(
                projection[
                    "deterministic_hash"
                ]
            ),
            adapter_report=(
                adapter_report
            ),
        )
    )

    index_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_target.write_text(
        json.dumps(
            compatibility,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "valid": validation[
            "valid"
        ],
        "errors": validation[
            "errors"
        ],
        "warnings": validation[
            "warnings"
        ],
        "node_count": len(
            graph.nodes
        ),
        "binding_count": len(
            graph.bindings
        ),
        "deterministic_hash": (
            projection[
                "deterministic_hash"
            ]
        ),
        "graph_output": str(
            graph_target
        ),
        "index_output": str(
            index_target
        ),
        "adapters": adapter_report,
    }


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile every Savant "
            "edifice into one "
            "role-bearing functional "
            "lineage graph."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
    )

    parser.add_argument(
        "--roles",
        type=Path,
        default=(
            DEFAULT_ROLE_REGISTRY
        ),
    )

    parser.add_argument(
        "--graph-output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--index-output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--no-filesystem",
        action="store_true",
    )

    parser.add_argument(
        "--filesystem-limit",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    report = compile_runtime_lineage(
        root=args.root,
        role_registry=args.roles,
        graph_output=(
            args.graph_output
        ),
        index_output=(
            args.index_output
        ),
        include_filesystem=(
            not args.no_filesystem
        ),
        filesystem_limit=max(
            0,
            args.filesystem_limit,
        ),
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if report["errors"]:
        return 1

    if (
        args.strict
        and report["warnings"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
