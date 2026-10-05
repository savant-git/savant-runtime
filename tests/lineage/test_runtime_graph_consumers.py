#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(
    "/root/savant-runtime"
)

LOCAL_ROOT = Path(
    __file__
).resolve().parents[2]

for candidate in (
    ROOT,
    LOCAL_ROOT,
):
    if str(candidate) not in sys.path:
        sys.path.insert(
            0,
            str(candidate),
        )


from runtime.palaver.fields.structural_fields import (  # noqa: E402
    compile_structural_fields,
)

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)

from runtime.palaver.topology.topology_compiler import (  # noqa: E402
    compile_topology,
)


def example_graph(
) -> dict:
    return {
        "schema": (
            "savant."
            "runtime_graph.v2"
        ),
        "deterministic_hash": (
            "runtime-hash"
        ),
        "source_lineage_hash": (
            "lineage-hash"
        ),
        "nodes": [
            {
                "id": "source.alpha",
                "canonical_id": (
                    "source.alpha"
                ),
                "label": (
                    "Source Alpha"
                ),
                "kind": "authority",
                "authority": True,
                "parents": [],
                "mothers": [],
                "fathers": [],
                "children": [
                    "child.alpha"
                ],
                "daughters": [
                    "child.alpha"
                ],
                "sons": [],
                "metadata": {},
                "provenance": {
                    "source": "test"
                },
            },
            {
                "id": "pattern.alpha",
                "canonical_id": (
                    "pattern.alpha"
                ),
                "label": (
                    "Pattern Alpha"
                ),
                "kind": "template",
                "authority": True,
                "parents": [],
                "mothers": [],
                "fathers": [],
                "children": [
                    "child.alpha"
                ],
                "daughters": [],
                "sons": [
                    "child.alpha"
                ],
                "metadata": {},
                "provenance": {
                    "source": "test"
                },
            },
            {
                "id": "child.alpha",
                "canonical_id": (
                    "child.alpha"
                ),
                "legacy_id": (
                    "child"
                ),
                "label": (
                    "Child Alpha"
                ),
                "path": (
                    "runtime/child"
                ),
                "kind": "runtime",
                "authority": False,
                "parents": [
                    "source.alpha",
                    "pattern.alpha",
                ],
                "mothers": [
                    "source.alpha"
                ],
                "fathers": [
                    "pattern.alpha"
                ],
                "children": [
                    "projection.alpha"
                ],
                "daughters": [],
                "sons": [
                    "projection.alpha"
                ],
                "metadata": {},
                "provenance": {
                    "source": "test"
                },
            },
            {
                "id": (
                    "projection.alpha"
                ),
                "canonical_id": (
                    "projection.alpha"
                ),
                "label": (
                    "Projection Alpha"
                ),
                "kind": "projection",
                "authority": False,
                "parents": [
                    "child.alpha"
                ],
                "mothers": [],
                "fathers": [],
                "children": [],
                "daughters": [],
                "sons": [],
                "metadata": {},
                "provenance": {
                    "source": "test"
                },
            },
        ],
        "edges": [
            {
                "id": "edge.source",
                "source": (
                    "source.alpha"
                ),
                "target": (
                    "child.alpha"
                ),
                "role": "source",
                "axis": "substance",
                "continuation": (
                    "preserving"
                ),
                "status": "active",
                "inheritance": {
                    "mode": "merge",
                    "fields": [
                        "data"
                    ],
                },
                "propagation": {
                    "enabled": True,
                    "channels": [
                        "projection",
                        "regeneration",
                    ],
                },
            },
            {
                "id": "edge.pattern",
                "source": (
                    "pattern.alpha"
                ),
                "target": (
                    "child.alpha"
                ),
                "role": "pattern",
                "axis": "form",
                "continuation": (
                    "projecting"
                ),
                "status": "active",
                "inheritance": {
                    "mode": "merge",
                    "fields": [
                        "schema"
                    ],
                },
                "propagation": {
                    "enabled": True,
                    "channels": [
                        "validation"
                    ],
                },
            },
            {
                "id": "edge.project",
                "source": (
                    "child.alpha"
                ),
                "target": (
                    "projection.alpha"
                ),
                "role": "projection",
                "axis": (
                    "representation"
                ),
                "continuation": (
                    "projecting"
                ),
                "status": "active",
                "inheritance": {
                    "mode": "reference",
                    "fields": [],
                },
                "propagation": {
                    "enabled": True,
                    "channels": [
                        "projection"
                    ],
                },
            },
        ],
    }


class RuntimeGraphConsumerTests(
    unittest.TestCase
):
    def test_index_resolves_all_identity_surfaces(
        self,
    ) -> None:
        index = RuntimeGraphIndex(
            example_graph()
        )

        self.assertEqual(
            index.resolve_node_id(
                "child.alpha"
            ),
            "child.alpha",
        )

        self.assertEqual(
            index.resolve_node_id(
                "child"
            ),
            "child.alpha",
        )

        self.assertEqual(
            index.resolve_node_id(
                "runtime/child"
            ),
            "child.alpha",
        )

    def test_role_filtered_traversal(
        self,
    ) -> None:
        index = RuntimeGraphIndex(
            example_graph()
        )

        parents = index.traverse(
            "child.alpha",
            direction="parents",
            roles=[
                "source"
            ],
            max_depth=1,
        )

        self.assertEqual(
            [
                item["id"]
                for item in parents
            ],
            [
                "source.alpha"
            ],
        )

        children = index.traverse(
            "child.alpha",
            direction="children",
            roles=[
                "projection"
            ],
            max_depth=1,
        )

        self.assertEqual(
            [
                item["id"]
                for item in children
            ],
            [
                "projection.alpha"
            ],
        )

    def test_structural_fields_use_lineage_roles(
        self,
    ) -> None:
        payload = (
            compile_structural_fields(
                example_graph()
            )
        )

        child = next(
            item
            for item
            in payload["fields"]
            if item["id"]
            == "child.alpha"
        )

        self.assertGreater(
            child[
                "source_mass"
            ],
            0,
        )

        self.assertGreater(
            child[
                "pattern_mass"
            ],
            0,
        )

        self.assertEqual(
            child[
                "mother_count"
            ],
            1,
        )

        self.assertEqual(
            child[
                "father_count"
            ],
            1,
        )

        self.assertGreater(
            child[
                "inheritance_load"
            ],
            0,
        )

    def test_topology_exposes_role_roots_and_components(
        self,
    ) -> None:
        payload = compile_topology(
            example_graph()
        )

        self.assertEqual(
            payload[
                "component_count"
            ],
            1,
        )

        self.assertEqual(
            payload[
                "role_roots"
            ][
                "source"
            ],
            [
                "source.alpha"
            ],
        )

        self.assertEqual(
            payload[
                "role_leaves"
            ][
                "projection"
            ],
            [
                "projection.alpha"
            ],
        )

        self.assertEqual(
            payload[
                "family_counts"
            ][
                "nodes_with_mothers"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
