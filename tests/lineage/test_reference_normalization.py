#!/usr/bin/env python3
from __future__ import annotations

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


from runtime.lineage.adapters.common import (  # noqa: E402
    add_binding_once,
)

from runtime.lineage.adapters.filesystem import (  # noqa: E402
    ingest_filesystem,
)

from runtime.lineage.engine import (  # noqa: E402
    LineageGraph,
)

from runtime.lineage.references import (  # noqa: E402
    filesystem_reference_id,
    resolve_reference,
)

from runtime.lineage.registry import (  # noqa: E402
    LineageRoleRegistry,
)


class ReferenceNormalizationTests(
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

    def test_absolute_runtime_path_becomes_filesystem_id(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            ).absolute()

            target = (
                root
                / "ontology"
                / "authority"
                / "record.json"
            )

            target.parent.mkdir(
                parents=True
            )

            target.write_text(
                "{}\n",
                encoding="utf-8",
            )

            resolution = (
                resolve_reference(
                    str(target),
                    root=root,
                )
            )

            self.assertEqual(
                resolution.canonical,
                (
                    "fs:ontology/"
                    "authority/"
                    "record.json"
                ),
            )

            self.assertTrue(
                resolution.changed
            )

    def test_runtime_relative_path_becomes_filesystem_id(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            ).absolute()

            target = (
                root
                / "ontology"
                / "authority"
                / "record.json"
            )

            target.parent.mkdir(
                parents=True
            )

            target.write_text(
                "{}\n",
                encoding="utf-8",
            )

            resolution = (
                resolve_reference(
                    (
                        "ontology/"
                        "authority/"
                        "record.json"
                    ),
                    root=root,
                )
            )

            self.assertEqual(
                resolution.canonical,
                (
                    "fs:ontology/"
                    "authority/"
                    "record.json"
                ),
            )

    def test_semantic_reference_remains_semantic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            ).absolute()

            resolution = (
                resolve_reference(
                    "edifice:identity:4",
                    root=root,
                )
            )

            self.assertEqual(
                resolution.canonical,
                "edifice:identity:4",
            )

            self.assertFalse(
                resolution.changed
            )

            self.assertEqual(
                resolution.kind,
                "semantic",
            )

    def test_path_binding_converges_with_filesystem_node(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            ).absolute()

            target = (
                root
                / "ontology"
                / "authority"
                / "record.json"
            )

            target.parent.mkdir(
                parents=True
            )

            target.write_text(
                "{}\n",
                encoding="utf-8",
            )

            graph = self.graph()

            graph.add_node(
                "semantic:absolute",
                {
                    "id": (
                        "semantic:absolute"
                    )
                },
            )

            graph.add_node(
                "semantic:relative",
                {
                    "id": (
                        "semantic:relative"
                    )
                },
            )

            add_binding_once(
                graph,
                parent=str(target),
                child=(
                    "semantic:absolute"
                ),
                role="source",
                reference_root=root,
            )

            add_binding_once(
                graph,
                parent=(
                    "ontology/"
                    "authority/"
                    "record.json"
                ),
                child=(
                    "semantic:relative"
                ),
                role="source",
                reference_root=root,
            )

            ingest_filesystem(
                graph,
                root,
                scan_roots=[
                    "ontology"
                ],
            )

            expected = (
                filesystem_reference_id(
                    target,
                    root=root,
                )
            )

            self.assertEqual(
                graph.parents(
                    "semantic:absolute"
                )[0]["parent"],
                expected,
            )

            self.assertEqual(
                graph.parents(
                    "semantic:relative"
                )[0]["parent"],
                expected,
            )

            warnings = graph.validate()[
                "warnings"
            ]

            self.assertFalse(
                any(
                    expected in warning
                    for warning in warnings
                )
            )

    def test_genuine_semantic_reference_remains_visible(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            ).absolute()

            graph = self.graph()

            graph.add_node(
                "semantic:child",
                {
                    "id": "semantic:child"
                },
            )

            add_binding_once(
                graph,
                parent=(
                    "edifice:identity:4"
                ),
                child="semantic:child",
                role="source",
                reference_root=root,
            )

            warnings = graph.validate()[
                "warnings"
            ]

            self.assertIn(
                (
                    "unresolved node "
                    "reference: "
                    "edifice:identity:4"
                ),
                warnings,
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
