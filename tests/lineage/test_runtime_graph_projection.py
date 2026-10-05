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


from runtime.lineage.engine import LineageGraph  # noqa: E402

from runtime.lineage.registry import (  # noqa: E402
    LineageRoleRegistry,
)

from runtime.palaver.graph.runtime_graph_engine import (  # noqa: E402
    project_runtime_graph,
)


class RuntimeGraphProjectionTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ) -> None:
        candidates = (
            (
                LOCAL_ROOT
                / "authority_graph"
                / "roles"
                / "lineage_role_registry.json"
            ),
            (
                ROOT
                / "authority_graph"
                / "roles"
                / "lineage_role_registry.json"
            ),
        )

        cls.role_path = next(
            (
                candidate
                for candidate in candidates
                if candidate.is_file()
            ),
            None,
        )

        if cls.role_path is None:
            raise FileNotFoundError(
                "lineage role registry "
                "was not found"
            )

    def graph(
        self,
    ) -> LineageGraph:
        return LineageGraph(
            LineageRoleRegistry.load(
                self.role_path
            )
        )

    def test_runtime_graph_projects_role_bearing_edges(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_node(
            "fs:.",
            {
                "id": "fs:.",
                "legacy_id": (
                    "savant-runtime"
                ),
                "kind": (
                    "filesystem_directory"
                ),
                "label": (
                    "savant-runtime"
                ),
                "authority": True,
            },
        )

        graph.add_node(
            "fs:runtime",
            {
                "id": "fs:runtime",
                "legacy_id": "runtime",
                "kind": (
                    "filesystem_directory"
                ),
                "label": "runtime",
                "authority": True,
            },
        )

        graph.add_binding({
            "parent": "fs:.",
            "child": "fs:runtime",
            "role": "composition",
            "continuation": (
                "preserving"
            ),
            "scope": "filesystem",
        })

        projection = (
            project_runtime_graph(
                graph,
                source_lineage_hash=(
                    "lineage-hash"
                ),
            )
        )

        self.assertEqual(
            projection["schema"],
            "savant.runtime_graph.v2",
        )

        self.assertEqual(
            projection[
                "source_lineage_hash"
            ],
            "lineage-hash",
        )

        self.assertEqual(
            projection["node_count"],
            2,
        )

        self.assertEqual(
            projection["edge_count"],
            1,
        )

        edge = projection[
            "edges"
        ][0]

        self.assertEqual(
            edge["source"],
            "savant-runtime",
        )

        self.assertEqual(
            edge["target"],
            "runtime",
        )

        self.assertEqual(
            edge["kind"],
            "contains",
        )

        self.assertEqual(
            edge["role"],
            "composition",
        )

        self.assertEqual(
            edge[
                "symbolic_child_alias"
            ],
            "daughter",
        )

    def test_colliding_legacy_ids_do_not_merge_nodes(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_node(
            "fs:runtime",
            {
                "id": "fs:runtime",
                "legacy_id": "runtime",
                "kind": (
                    "filesystem_directory"
                ),
            },
        )

        graph.add_node(
            "runtime",
            {
                "id": "runtime",
                "kind": (
                    "semantic_instance"
                ),
            },
        )

        projection = (
            project_runtime_graph(
                graph
            )
        )

        ids = {
            node["id"]
            for node
            in projection["nodes"]
        }

        self.assertEqual(
            len(ids),
            2,
        )

        self.assertIn(
            "fs:runtime",
            ids,
        )

        self.assertIn(
            "runtime",
            ids,
        )

    def test_symbolic_family_arrays_are_derived(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_node(
            "source.alpha",
            {
                "id": "source.alpha"
            },
        )

        graph.add_node(
            "pattern.alpha",
            {
                "id": "pattern.alpha"
            },
        )

        graph.add_node(
            "child.alpha",
            {
                "id": "child.alpha"
            },
        )

        graph.add_binding({
            "parent": "source.alpha",
            "child": "child.alpha",
            "role": "source",
            "continuation": (
                "preserving"
            ),
        })

        graph.add_binding({
            "parent": "pattern.alpha",
            "child": "child.alpha",
            "role": "pattern",
            "continuation": (
                "projecting"
            ),
        })

        projection = (
            project_runtime_graph(
                graph
            )
        )

        child = next(
            node
            for node
            in projection["nodes"]
            if node["id"]
            == "child.alpha"
        )

        self.assertEqual(
            child["mothers"],
            [
                "source.alpha"
            ],
        )

        self.assertEqual(
            child["fathers"],
            [
                "pattern.alpha"
            ],
        )

        source = next(
            node
            for node
            in projection["nodes"]
            if node["id"]
            == "source.alpha"
        )

        pattern = next(
            node
            for node
            in projection["nodes"]
            if node["id"]
            == "pattern.alpha"
        )

        self.assertEqual(
            source["daughters"],
            [
                "child.alpha"
            ],
        )

        self.assertEqual(
            pattern["sons"],
            [
                "child.alpha"
            ],
        )

    def test_runtime_projection_hash_is_deterministic(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_binding({
            "parent": "source",
            "child": "instance",
            "role": "source",
        })

        first = (
            project_runtime_graph(
                graph,
                source_lineage_hash=(
                    "same-source"
                ),
            )
        )

        second = (
            project_runtime_graph(
                graph,
                source_lineage_hash=(
                    "same-source"
                ),
            )
        )

        self.assertEqual(
            first[
                "deterministic_hash"
            ],
            second[
                "deterministic_hash"
            ],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
