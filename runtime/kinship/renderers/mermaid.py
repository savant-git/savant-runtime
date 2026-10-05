#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping


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


def _label(
    value: Any,
) -> str:
    return (
        str(
            value
        )
        .replace(
            "\"",
            "'",
        )
        .replace(
            "\n",
            " ",
        )
        .replace(
            "[",
            "(",
        )
        .replace(
            "]",
            ")",
        )
    )


def render_mermaid(
    payload: Mapping[str, Any],
) -> str:
    nodes = {
        str(node["id"]): node
        for node in payload.get(
            "nodes",
            []
        )
    }

    lines = [
        "flowchart TB",
    ]

    generations = payload.get(
        "generations",
        {},
    )

    for generation, node_ids in (
        sorted(
            generations.items(),
            key=lambda item: int(
                item[0]
            ),
        )
    ):
        subgraph_id = (
            "generation_"
            + str(
                generation
            ).replace(
                "-",
                "m",
            )
        )

        lines.append(
            "  "
            f"subgraph {subgraph_id}"
            "[\"Generation "
            f"{generation}\"]"
        )

        for node_id in node_ids:
            node = nodes[
                str(
                    node_id
                )
            ]

            rendered_id = _node_id(
                str(
                    node_id
                )
            )

            rendered_label = _label(
                f"{node.get('label', node_id)}"
                f"\\n{node_id}"
                f"\\n<{node.get('kind', 'instance')}>"
            )

            if node.get(
                "focus",
                False,
            ):
                lines.append(
                    "    "
                    f"{rendered_id}"
                    "{{{{\"{rendered_label}\"}}}}"
                )

            elif node.get(
                "authority",
                False,
            ):
                lines.append(
                    "    "
                    f"{rendered_id}"
                    "{{\"{rendered_label}\"}}"
                )

            else:
                lines.append(
                    "    "
                    f"{rendered_id}"
                    "[\"{rendered_label}\"]"
                )

        lines.append(
            "  end"
        )

    for edge in payload.get(
        "edges",
        []
    ):
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
            label = _label(
                f"{edge.get('parent_profile', 'parent')}"
                "/"
                f"{edge.get('role', 'generic')}"
                " → "
                f"{edge.get('child_profile', 'child')}"
            )

            lines.append(
                "  "
                f"{source} "
                f"-->|\"{label}\"| "
                f"{target}"
            )

        elif kind == "alliance":
            label = _label(
                edge.get(
                    "alliance_profile",
                    "partner",
                )
            )

            lines.append(
                "  "
                f"{source} "
                f"<-. \"{label}\" .-> "
                f"{target}"
            )

        else:
            label = _label(
                edge.get(
                    "relationship",
                    "derived",
                )
            )

            lines.append(
                "  "
                f"{source} "
                f"-.-|\"{label}\"| "
                f"{target}"
            )

    lines.extend([
        "  classDef focus stroke-width:4px;",
        "  classDef authority stroke-width:2px;",
    ])

    focus_nodes = [
        _node_id(
            str(
                node["id"]
            )
        )
        for node in nodes.values()
        if node.get(
            "focus",
            False,
        )
    ]

    authority_nodes = [
        _node_id(
            str(
                node["id"]
            )
        )
        for node in nodes.values()
        if (
            node.get(
                "authority",
                False,
            )
            and not node.get(
                "focus",
                False,
            )
        )
    ]

    if focus_nodes:
        lines.append(
            "  class "
            + ",".join(
                focus_nodes
            )
            + " focus;"
        )

    if authority_nodes:
        lines.append(
            "  class "
            + ",".join(
                authority_nodes
            )
            + " authority;"
        )

    return "\n".join(
        lines
    ) + "\n"


__all__ = [
    "render_mermaid",
]
