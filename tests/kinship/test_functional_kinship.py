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


from runtime.kinship.algebra import KinshipAlgebra  # noqa: E402
from runtime.kinship.graph import KinshipGraph  # noqa: E402
from runtime.kinship.projection import FamilyTreeProjector  # noqa: E402
from runtime.kinship.registry import KinshipRegistry  # noqa: E402
from runtime.kinship.renderers import render_family_tree  # noqa: E402


def fixture(
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
                "label": "Source Alpha",
                "kind": "source",
                "authority": True,
            },
            {
                "id": "pattern.alpha",
                "label": (
                    "Pattern Alpha"
                ),
                "kind": "template",
                "authority": True,
            },
            {
                "id": "child.one",
                "label": "Child One",
                "kind": "runtime",
            },
            {
                "id": "child.two",
                "label": "Child Two",
                "kind": "runtime",
            },
            {
                "id": "grandchild.one",
                "label": (
                    "Grandchild One"
                ),
                "kind": "projection",
            },
            {
                "id": "partner.alpha",
                "label": (
                    "Partner Alpha"
                ),
                "kind": "service",
            },
        ],
        "edges": [
            {
                "id": "edge.source.one",
                "source": "source.alpha",
                "target": "child.one",
                "role": "source",
                "axis": "substance",
                "continuation": (
                    "preserving"
                ),
                "scope": "test",
                "status": "active",
                "kinship": {
                    "parent_profile": (
                        "mother"
                    ),
                    "child_profile": (
                        "daughter"
                    ),
                    "generation_event": (
                        "generation.alpha"
                    )
                }
            },
            {
                "id": "edge.pattern.one",
                "source": "pattern.alpha",
                "target": "child.one",
                "role": "pattern",
                "axis": "form",
                "continuation": (
                    "projecting"
                ),
                "scope": "test",
                "status": "active",
                "kinship": {
                    "parent_profile": (
                        "father"
                    ),
                    "child_profile": (
                        "son"
                    ),
                    "generation_event": (
                        "generation.alpha"
                    )
                }
            },
            {
                "id": "edge.source.two",
                "source": "source.alpha",
                "target": "child.two",
                "role": "source",
                "axis": "substance",
                "continuation": (
                    "preserving"
                ),
                "scope": "test",
                "status": "active",
                "kinship": {
                    "parent_profile": (
                        "mother"
                    ),
                    "child_profile": (
                        "daughter"
                    ),
                    "generation_event": (
                        "generation.alpha"
                    )
                }
            },
            {
                "id": "edge.pattern.two",
                "source": "pattern.alpha",
                "target": "child.two",
                "role": "pattern",
                "axis": "form",
                "continuation": (
                    "projecting"
                ),
                "scope": "test",
                "status": "active",
                "kinship": {
                    "parent_profile": (
                        "father"
                    ),
                    "child_profile": (
                        "son"
                    ),
                    "generation_event": (
                        "generation.alpha"
                    )
                }
            },
            {
                "id": "edge.grandchild",
                "source": "child.one",
                "target": "grandchild.one",
                "role": "projection",
                "axis": (
                    "representation"
                ),
                "continuation": (
                    "projecting"
                ),
                "scope": "test",
                "status": "active"
            }
        ],
        "alliances": [
            {
                "id": "alliance.alpha",
                "partners": [
                    "child.one",
                    "partner.alpha"
                ],
                "alliance_profile": (
                    "spouse"
                ),
                "domains": [
                    "operation"
                ],
                "status": "active",
                "contract": {
                    "compatibility": (
                        "strict"
                    ),
                    "dissolution_policy": (
                        "preserve_children"
                    )
                }
            }
        ]
    }


class FunctionalKinshipTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ) -> None:
        cls.registry = (
            KinshipRegistry.load()
        )

        cls.graph = (
            KinshipGraph
            .from_runtime_graph(
                fixture(),
                registry=(
                    cls.registry
                ),
            )
        )

        cls.algebra = KinshipAlgebra(
            cls.graph,
            cls.registry,
        )

    def test_direct_parent_profiles(
        self,
    ) -> None:
        relationships = {
            item.relationship
            for item
            in self.algebra.determine(
                "child.one",
                "source.alpha",
            )
        }

        self.assertIn(
            "mother",
            relationships,
        )

    def test_full_sibling_and_twin(
        self,
    ) -> None:
        relationships = {
            item.relationship
            for item
            in self.algebra.determine(
                "child.one",
                "child.two",
            )
        }

        self.assertIn(
            "full_sibling",
            relationships,
        )

        self.assertIn(
            "twin",
            relationships,
        )

        self.assertIn(
            "maternal_sibling",
            relationships,
        )

        self.assertIn(
            "paternal_sibling",
            relationships,
        )

    def test_grandparent(
        self,
    ) -> None:
        relationships = {
            item.relationship
            for item
            in self.algebra.determine(
                "grandchild.one",
                "source.alpha",
            )
        }

        self.assertIn(
            "grandmother",
            relationships,
        )

    def test_alliance(
        self,
    ) -> None:
        relationships = {
            item.relationship
            for item
            in self.algebra.determine(
                "child.one",
                "partner.alpha",
            )
        }

        self.assertIn(
            "spouse",
            relationships,
        )

    def test_projection_is_deterministic(
        self,
    ) -> None:
        projector = FamilyTreeProjector(
            self.graph,
            self.registry,
        )

        left = projector.project(
            "child.one"
        )

        right = projector.project(
            "child.one"
        )

        self.assertEqual(
            left.deterministic_hash,
            right.deterministic_hash,
        )

    def test_all_renderers(
        self,
    ) -> None:
        payload = (
            FamilyTreeProjector(
                self.graph,
                self.registry,
            )
            .project(
                "child.one"
            )
            .to_dict()
        )

        for format_name in (
            "ascii",
            "json",
            "dot",
            "mermaid",
        ):
            rendered = (
                render_family_tree(
                    payload,
                    format_name=(
                        format_name
                    ),
                )
            )

            self.assertTrue(
                rendered.strip()
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
