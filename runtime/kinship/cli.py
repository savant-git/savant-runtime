#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


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


from runtime.kinship.graph import KinshipGraph  # noqa: E402
from runtime.kinship.projection import FamilyTreeProjector  # noqa: E402
from runtime.kinship.registry import (  # noqa: E402
    DEFAULT_KINSHIP_REGISTRY,
    KinshipRegistry,
)
from runtime.kinship.renderers import (  # noqa: E402
    SUPPORTED_FORMATS,
    render_family_tree,
)


DEFAULT_RUNTIME_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)


def read_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"JSON file missing: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            f"JSON root must be an object: {path}"
        )

    return dict(
        payload
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Derive and render a "
            "domain-aware Savant "
            "functional family tree."
        )
    )

    parser.add_argument(
        "focus",
        help=(
            "Node ID, canonical ID, "
            "path, or unique label."
        ),
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_RUNTIME_GRAPH,
    )

    parser.add_argument(
        "--registry",
        type=Path,
        default=(
            DEFAULT_KINSHIP_REGISTRY
        ),
    )

    parser.add_argument(
        "--format",
        choices=sorted(
            SUPPORTED_FORMATS
        ),
        default="ascii",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--domain",
        default=None,
    )

    parser.add_argument(
        "--include-inactive",
        action="store_true",
    )

    parser.add_argument(
        "--direct-only",
        action="store_true",
    )

    parser.add_argument(
        "--no-derived-edges",
        action="store_true",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=120,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser


def main(
) -> int:
    args = build_parser().parse_args()

    try:
        runtime_payload = read_json(
            args.graph
        )

        registry = KinshipRegistry.load(
            args.registry
        )

        graph = (
            KinshipGraph
            .from_runtime_graph(
                runtime_payload,
                registry=registry,
            )
        )

        projector = FamilyTreeProjector(
            graph,
            registry,
        )

        projection = projector.project(
            args.focus,
            max_depth=max(
                1,
                args.depth,
            ),
            active_only=(
                not args
                .include_inactive
            ),
            domain=args.domain,
            include_extended=(
                not args.direct_only
            ),
            include_derived_edges=(
                not args
                .no_derived_edges
            ),
        )

        payload = projection.to_dict()

        rendered = render_family_tree(
            payload,
            format_name=args.format,
            width=max(
                40,
                args.width,
            ),
        )

        if args.output is not None:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            args.output.write_text(
                rendered,
                encoding="utf-8",
            )

            print(
                json.dumps(
                    {
                        "output": str(
                            args.output
                        ),
                        "format": (
                            args.format
                        ),
                        "focus": (
                            projection.focus
                        ),
                        "node_count": (
                            len(
                                projection.nodes
                            )
                        ),
                        "edge_count": (
                            len(
                                projection.edges
                            )
                        ),
                        "deterministic_hash": (
                            projection
                            .deterministic_hash
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )

        else:
            sys.stdout.write(
                rendered
            )

        return 0

    except Exception as exc:
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
