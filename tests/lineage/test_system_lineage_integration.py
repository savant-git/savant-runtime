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


from runtime.lineage.adapters.authority import (  # noqa: E402
    ingest_authority_roots,
)

from runtime.lineage.adapters.filesystem import (  # noqa: E402
    ingest_filesystem,
)

from runtime.lineage.engine import (  # noqa: E402
    LineageGraph,
)

from runtime.lineage.projection import (  # noqa: E402
    family_projection,
)

from runtime.lineage.registry import (  # noqa: E402
    LineageRoleRegistry,
)


class SystemLineageIntegrationTests(
    unittest.TestCase
):
    def setUp(
        self,
    ) -> None:
        self.role_index = (
            LOCAL_ROOT
            / "authority_graph"
            / "roles"
            / (
                "lineage_"
                "role_registry.json"
            )
        )

        if not self.role_index.exists():
            self.role_index = (
                ROOT
                / "authority_graph"
                / "roles"
                / (
                    "lineage_"
                    "role_registry.json"
                )
            )

    def graph(
        self,
    ) -> LineageGraph:
        return LineageGraph(
            LineageRoleRegistry.load(
                self.role_index
            )
        )

    def test_filesystem_projects_daughters_and_sons(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            (
                root
                / "runtime"
                / "module"
            ).mkdir(
                parents=True
            )

            (
                root
                / "runtime"
                / "module"
                / "engine.py"
            ).write_text(
                "print('ok')\n",
                encoding="utf-8",
            )

            graph = self.graph()

            ingest_filesystem(
                graph,
                root,
                scan_roots=[
                    "runtime"
                ],
            )

            runtime_family = (
                family_projection(
                    graph,
                    "fs:runtime",
                )
            )

            module_family = (
                family_projection(
                    graph,
                    (
                        "fs:runtime/"
                        "module"
                    ),
                )
            )

            self.assertIn(
                (
                    "fs:runtime/"
                    "module"
                ),
                runtime_family[
                    "daughters"
                ],
            )

            self.assertIn(
                (
                    "fs:runtime/"
                    "module/engine.py"
                ),
                module_family[
                    "sons"
                ],
            )

    def test_authority_chain_uses_pattern_parents(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(
                temporary
            )

            documents = [
                {
                    "id": (
                        "meta:universal"
                    ),
                    "kind": (
                        "meta_archetype"
                    ),
                },
                {
                    "id": (
                        "archetype:"
                        "universal"
                    ),
                    "kind": (
                        "archetype"
                    ),
                    "meta_archetype": (
                        "meta:universal"
                    ),
                },
                {
                    "id": (
                        "template:base"
                    ),
                    "kind": (
                        "template"
                    ),
                    "archetype": (
                        "archetype:"
                        "universal"
                    ),
                },
            ]

            for (
                index,
                document,
            ) in enumerate(
                documents
            ):
                (
                    root
                    / f"{index}.json"
                ).write_text(
                    json.dumps(
                        document
                    ),
                    encoding="utf-8",
                )

            graph = self.graph()

            ingest_authority_roots(
                graph,
                [
                    root
                ],
            )

            family = (
                family_projection(
                    graph,
                    "template:base",
                )
            )

            self.assertEqual(
                family["fathers"],
                [
                    (
                        "archetype:"
                        "universal"
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
