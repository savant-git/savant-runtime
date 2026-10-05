#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
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


from runtime.lineage.engine import (  # noqa: E402
    LineageGraph,
    compile_lineage,
)

from runtime.lineage.model import (  # noqa: E402
    LineageValidationError,
)

from runtime.lineage.registry import (  # noqa: E402
    LineageRoleRegistry,
)


class FunctionalLineageTests(
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
            searched = "\n".join(
                str(candidate)
                for candidate in candidates
            )

            raise FileNotFoundError(
                "authoritative lineage role "
                "registry was not found:\n"
                f"{searched}"
            )

    def graph(
        self,
    ) -> LineageGraph:
        return LineageGraph(
            LineageRoleRegistry.load(
                self.role_path
            )
        )

    def test_multiple_functional_parents_and_symbolic_projection(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_node(
            "source.alpha",
            {
                "id": "source.alpha",
                "data": {
                    "a": 1
                },
            },
        )

        graph.add_node(
            "pattern.alpha",
            {
                "id": "pattern.alpha",
                "structure": {
                    "shape": "recursive"
                },
            },
        )

        graph.add_node(
            "child.alpha",
            {
                "id": "child.alpha",
                "data": {
                    "b": 2
                },
            },
        )

        graph.add_binding(
            {
                "parent": "source.alpha",
                "child": "child.alpha",
                "role": "mother",
                "continuation": "preserving",
            }
        )

        graph.add_binding(
            {
                "parent": "pattern.alpha",
                "child": "child.alpha",
                "role": "father",
                "continuation": "projecting",
            }
        )

        parents = graph.parents(
            "child.alpha"
        )

        self.assertEqual(
            [
                item["role"]
                for item in parents
            ],
            [
                "source",
                "pattern",
            ],
        )

        self.assertEqual(
            parents[0][
                "symbolic_parent_alias"
            ],
            "mother",
        )

        self.assertEqual(
            parents[0][
                "symbolic_child_alias"
            ],
            "daughter",
        )

        self.assertEqual(
            parents[1][
                "symbolic_parent_alias"
            ],
            "father",
        )

        self.assertEqual(
            parents[1][
                "symbolic_child_alias"
            ],
            "son",
        )

    def test_role_inheritance_is_deterministic(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_node(
            "source.alpha",
            {
                "id": "source.alpha",
                "data": {
                    "shared": "source",
                    "a": 1,
                },
            },
        )

        graph.add_node(
            "pattern.alpha",
            {
                "id": "pattern.alpha",
                "structure": {
                    "shape": "recursive"
                },
            },
        )

        graph.add_node(
            "child.alpha",
            {
                "id": "child.alpha",
                "data": {
                    "shared": "child",
                    "b": 2,
                },
            },
        )

        graph.add_binding(
            {
                "parent": "source.alpha",
                "child": "child.alpha",
                "role": "source",
            }
        )

        graph.add_binding(
            {
                "parent": "pattern.alpha",
                "child": "child.alpha",
                "role": "pattern",
            }
        )

        resolved = graph.resolve_node(
            "child.alpha"
        )

        self.assertEqual(
            resolved["data"],
            {
                "a": 1,
                "b": 2,
                "shared": "child",
            },
        )

        self.assertEqual(
            resolved[
                "structure"
            ]["shape"],
            "recursive",
        )

        first_hash = graph.project()[
            "deterministic_hash"
        ]

        second_hash = graph.project()[
            "deterministic_hash"
        ]

        self.assertEqual(
            first_hash,
            second_hash,
        )

    def test_cycle_rejected_within_cycle_domain(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_binding(
            {
                "parent": "a",
                "child": "b",
                "role": "composition",
            }
        )

        with self.assertRaises(
            LineageValidationError
        ):
            graph.add_binding(
                {
                    "parent": "b",
                    "child": "a",
                    "role": "composition",
                }
            )

    def test_selective_regeneration_impact(
        self,
    ) -> None:
        graph = self.graph()

        graph.add_binding(
            {
                "parent": "source",
                "child": "instance",
                "role": "source",
            }
        )

        graph.add_binding(
            {
                "parent": "instance",
                "child": "projection",
                "role": "projection",
            }
        )

        self.assertEqual(
            graph.affected_by(
                [
                    "source"
                ]
            ),
            [
                "instance",
                "projection",
                "source",
            ],
        )

    def test_legacy_projection_is_additive(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(
                temp_dir
            )

            record = {
                "id": "script.example",
                "kind": "instance",
                "lineage": {
                    "composed_from": [
                        "snippet.header",
                        "snippet.body",
                    ]
                },
                "composition": {
                    "children": [
                        "line.child"
                    ]
                },
            }

            (
                root
                / "record.json"
            ).write_text(
                json.dumps(
                    record
                ),
                encoding="utf-8",
            )

            graph = compile_lineage(
                [
                    root
                ],
                role_registry=(
                    self.role_path
                ),
                include_legacy=True,
            )

            roles = [
                item["role"]
                for item
                in graph.parents(
                    "script.example"
                )
            ]

            self.assertEqual(
                roles,
                [
                    "source",
                    "source",
                ],
            )

            self.assertEqual(
                [
                    item["child"]
                    for item
                    in graph.children(
                        "script.example"
                    )
                ],
                [
                    "line.child"
                ],
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
