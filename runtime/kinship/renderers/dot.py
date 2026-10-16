#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping


def _escape(
    value: Any,
) -> str:
    return (
        str(
            value
        )
        .replace(
            "\\",
            "\\\\",
        )
        .replace(
            "\"",
            "\\\"",
        )
        .replace(
            "\n",
            "\\n",
        )
    )


def _node_id(
    value: str,
) -> str:
    return (
        "n_"
        + "".join(
            character
            if character.isalnum()
            else "_"
            for character in value
        )
    )


def render_dot(
    payload: Mapping[str, Any],
) -> str:
    nodes = payload.get(
        "nodes",
        [],
    )

    edges = payload.get(
        "edges",
        [],
    )

    generations = payload.get(
        "generations",
        {},
    )

    lines = [
        "digraph SavantFunctionalFamily {",
        "  graph [",
        "    rankdir=TB,",
        "    compound=true,",
        "    splines=polyline,",
        "    overlap=false,",
        "    nodesep=0.55,",
        "    ranksep=0.9,",
        "    fontname=\"monospace\",",
        "    labelloc=\"t\",",
        "    label=\"Savant Functional Family Tree\"",
        "  ];",
        "  node [",
        "    shape=box,",
        "    style=\"rounded\",",
        "    fontname=\"monospace\",",
        "    fontsize=10",
        "  ];",
        "  edge [",
        "    fontname=\"monospace\",",
        "    fontsize=9",
        "  ];",
    ]

    for node in nodes:
        node_id = _node_id(
            str(
                node["id"]
            )
        )

        label = (
            f"{node.get('label', node['id'])}"
            "\\n"
            f"{node['id']}"
            "\\n"
            f"<{node.get('kind', 'instance')}>"
        )

        attributes = [
            f'label="{_escape(label)}"',
        ]

        if node.get(
            "focus",
            False,
        ):
            attributes.extend([
                "penwidth=3",
                "shape=doubleoctagon",
            ])

        elif node.get(
            "authority",
            False,
        ):
            attributes.extend([
                "penwidth=2",
                "shape=octagon",
            ])

        lines.append(
            "  "
            f"{node_id} "
            "["
            + ", ".join(
                attributes
            )
            + "];"
        )

    for generation, node_ids in (
        sorted(
            generations.items(),
            key=lambda item: int(
                item[0]
            ),
        )
    ):
        rendered = "; ".join(
            _node_id(
                str(node_id)
            )
            for node_id
            in node_ids
        )

        lines.append(
            "  { "
            f"rank=same; {rendered}; "
            "}"
        )

    for edge in edges:
        source = _node_id(
            str(
                edge["source"]
            )
        )

        target = _node_id(
            str(
                edge["target"]
            )
        )

        kind = edge.get(
            "kind"
        )

        if kind == "direct_lineage":
            label = (
                f"{edge.get('parent_profile', 'parent')}"
                "/"
                f"{edge.get('role', 'generic')}"
                " → "
                f"{edge.get('child_profile', 'child')}"
            )

            if edge.get(
                "domain"
            ):
                label += (
                    "\\n@"
                    + str(
                        edge["domain"]
                    )
                )

            attributes = [
                f'label="{_escape(label)}"',
                "style=solid",
                "penwidth=1.6",
            ]

        elif kind == "alliance":
            label = str(
                edge.get(
                    "alliance_profile",
                    "partner",
                )
            )

            attributes = [
                f'label="{_escape(label)}"',
                "dir=both",
                "arrowhead=none",
                "arrowtail=none",
                "style=dashed",
                "penwidth=2",
                "constraint=false",
            ]

        else:
            label = str(
                edge.get(
                    "relationship",
                    "derived",
                )
            )

            attributes = [
                f'label="{_escape(label)}"',
                "dir=none",
                "style=dotted",
                "constraint=false",
            ]

        lines.append(
            "  "
            f"{source} -> {target} "
            "["
            + ", ".join(
                attributes
            )
            + "];"
        )

    lines.append(
        "}"
    )

    return "\n".join(
        lines
    ) + "\n"


__all__ = [
    "render_dot",
]
