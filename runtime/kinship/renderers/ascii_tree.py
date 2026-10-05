#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from textwrap import shorten
from typing import Any, Mapping


def _label(
    node: Mapping[str, Any],
    *,
    width: int,
) -> str:
    prefix = "★ " if node.get(
        "focus",
        False,
    ) else ""

    authority = (
        " [A]"
        if node.get(
            "authority",
            False,
        )
        else ""
    )

    kind = str(
        node.get(
            "kind",
            "instance",
        )
    )

    text = (
        f"{prefix}"
        f"{node.get('label', node['id'])}"
        f" <{kind}>"
        f"{authority}"
        f" [{node['id']}]"
    )

    return shorten(
        text,
        width=max(
            20,
            width,
        ),
        placeholder="…",
    )


def render_ascii_tree(
    payload: Mapping[str, Any],
    *,
    width: int = 120,
    include_edge_ledger: bool = True,
    include_determinations: bool = True,
) -> str:
    nodes = {
        str(node["id"]): node
        for node in payload.get(
            "nodes",
            []
        )
    }

    lines: list[str] = []

    title = (
        "SAVANT FUNCTIONAL "
        "FAMILY TREE"
    )

    lines.append(
        title
    )

    lines.append(
        "="
        * min(
            width,
            len(
                title
            ),
        )
    )

    lines.append(
        "focus: "
        + str(
            payload.get(
                "focus",
                ""
            )
        )
    )

    lines.append(
        "projection: "
        + str(
            payload.get(
                "deterministic_hash",
                "",
            )
        )
    )

    lines.append("")

    generations = payload.get(
        "generations",
        {},
    )

    for raw_generation, node_ids in (
        sorted(
            generations.items(),
            key=lambda item: int(
                item[0]
            ),
        )
    ):
        generation = int(
            raw_generation
        )

        if generation < 0:
            heading = (
                f"GENERATION {generation} "
                f"({abs(generation)} "
                "ABOVE)"
            )

        elif generation > 0:
            heading = (
                f"GENERATION +{generation} "
                f"({generation} BELOW)"
            )

        else:
            heading = (
                "GENERATION 0 "
                "(FOCUS / PEERS / "
                "PARTNERS)"
            )

        lines.append(
            heading
        )

        lines.append(
            "-"
            * min(
                width,
                len(
                    heading
                ),
            )
        )

        for node_id in node_ids:
            node = nodes[
                node_id
            ]

            lines.append(
                "  "
                + _label(
                    node,
                    width=(
                        width
                        - 2
                    ),
                )
            )

            relationships = (
                node.get(
                    "relationships_to_focus",
                    []
                )
            )

            labels = sorted({
                str(
                    item.get(
                        "relationship",
                        "",
                    )
                )
                for item in relationships
                if item.get(
                    "relationship"
                )
            })

            if labels:
                lines.append(
                    "    relation: "
                    + ", ".join(
                        labels
                    )
                )

        lines.append("")

    if include_edge_ledger:
        direct_edges = [
            edge
            for edge
            in payload.get(
                "edges",
                []
            )
            if edge.get(
                "kind"
            )
            == "direct_lineage"
        ]

        if direct_edges:
            lines.append(
                "DIRECT LINEAGE"
            )

            lines.append(
                "--------------"
            )

            for edge in direct_edges:
                left = nodes.get(
                    edge["source"],
                    {
                        "label": (
                            edge["source"]
                        )
                    },
                )

                right = nodes.get(
                    edge["target"],
                    {
                        "label": (
                            edge["target"]
                        )
                    },
                )

                relationship = (
                    f"{edge.get('parent_profile', 'parent')}"
                    f"/{edge.get('role', 'generic')}"
                    " → "
                    f"{edge.get('child_profile', 'child')}"
                )

                domain = edge.get(
                    "domain"
                )

                if domain:
                    relationship += (
                        f" @{domain}"
                    )

                lines.append(
                    "  "
                    f"{left.get('label', edge['source'])}"
                    " --["
                    f"{relationship}"
                    "]--> "
                    f"{right.get('label', edge['target'])}"
                )

                lines.append(
                    "    edge: "
                    + str(
                        edge["id"]
                    )
                )

            lines.append("")

        alliance_edges = [
            edge
            for edge
            in payload.get(
                "edges",
                []
            )
            if edge.get(
                "kind"
            )
            == "alliance"
        ]

        if alliance_edges:
            lines.append(
                "ALLIANCES"
            )

            lines.append(
                "---------"
            )

            for edge in alliance_edges:
                left = nodes.get(
                    edge["source"],
                    {
                        "label": (
                            edge["source"]
                        )
                    },
                )

                right = nodes.get(
                    edge["target"],
                    {
                        "label": (
                            edge["target"]
                        )
                    },
                )

                profile = edge.get(
                    "alliance_profile",
                    "partner",
                )

                domains = edge.get(
                    "domains",
                    [],
                )

                suffix = (
                    " @"
                    + ",".join(
                        domains
                    )
                    if domains
                    else ""
                )

                lines.append(
                    "  "
                    f"{left.get('label', edge['source'])}"
                    f" ==[{profile}{suffix}]== "
                    f"{right.get('label', edge['target'])}"
                )

                lines.append(
                    "    alliance: "
                    + str(
                        edge.get(
                            "alliance_id",
                            edge["id"],
                        )
                    )
                )

            lines.append("")

    if include_determinations:
        determinations = (
            payload.get(
                "determinations",
                []
            )
        )

        grouped: dict[
            str,
            list[
                Mapping[
                    str,
                    Any,
                ]
            ],
        ] = defaultdict(list)

        for determination in (
            determinations
        ):
            grouped[
                str(
                    determination[
                        "relative"
                    ]
                )
            ].append(
                determination
            )

        if grouped:
            lines.append(
                "DERIVED RELATIONSHIPS"
            )

            lines.append(
                "---------------------"
            )

            for relative in sorted(
                grouped,
                key=lambda item: (
                    nodes.get(
                        item,
                        {
                            "label": item
                        },
                    )
                    .get(
                        "label",
                        item,
                    )
                    .casefold(),
                    item,
                ),
            ):
                relative_label = (
                    nodes.get(
                        relative,
                        {
                            "label": relative
                        },
                    )
                    .get(
                        "label",
                        relative,
                    )
                )

                labels = [
                    str(
                        item[
                            "relationship"
                        ]
                    )
                    for item
                    in grouped[
                        relative
                    ]
                ]

                lines.append(
                    "  "
                    f"{relative_label}: "
                    + ", ".join(
                        sorted(
                            set(
                                labels
                            )
                        )
                    )
                )

                for item in grouped[
                    relative
                ]:
                    proof = [
                        str(
                            step[
                                "edge_id"
                            ]
                        )
                        for step
                        in item.get(
                            "path",
                            []
                        )
                    ]

                    if proof:
                        lines.append(
                            "    "
                            f"{item['relationship']}"
                            " proof: "
                            + " → ".join(
                                proof
                            )
                        )

            lines.append("")

    lines.append(
        "LEGEND"
    )

    lines.append(
        "------"
    )

    lines.append(
        "  ★ focus node"
    )

    lines.append(
        "  [A] explicit authority"
    )

    lines.append(
        "  --> direct lineage"
    )

    lines.append(
        "  ==  alliance"
    )

    lines.append(
        "  derived relationships "
        "are calculated, not stored"
    )

    return "\n".join(
        lines
    ) + "\n"


__all__ = [
    "render_ascii_tree",
]
