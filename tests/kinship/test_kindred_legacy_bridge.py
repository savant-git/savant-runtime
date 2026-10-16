#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lexicon.kindred.legacy_bridge import (
    LegacyKindredBridge,
)


class LegacyKindredBridgeTests(
    unittest.TestCase
):

    def setUp(self) -> None:
        self.bridge = (
            LegacyKindredBridge()
        )

    def test_parent_projects_containment(
        self,
    ) -> None:
        record = {
            "id": "instance:child",
            "parent": "instance:parent",
        }

        projection = (
            self.bridge.project(
                record
            )
        )

        relations = {
            edge["relation"]
            for edge in projection[
                "edges"
            ]
        }

        self.assertIn(
            "relation:contained_by",
            relations,
        )

        self.assertIn(
            "relation:contains",
            relations,
        )

    def test_dependencies_project_inverse(
        self,
    ) -> None:
        record = {
            "id": "instance:a",
            "dependencies": [
                "instance:b",
            ],
        }

        projection = (
            self.bridge.project(
                record
            )
        )

        relations = {
            edge["relation"]
            for edge in projection[
                "edges"
            ]
        }

        self.assertIn(
            "relation:depends_on",
            relations,
        )

        self.assertIn(
            "relation:required_by",
            relations,
        )

    def test_supersession_projects_inverse(
        self,
    ) -> None:
        record = {
            "id": "instance:new",
            "supersedes": [
                "instance:old",
            ],
        }

        projection = (
            self.bridge.project(
                record
            )
        )

        relations = {
            edge["relation"]
            for edge in projection[
                "edges"
            ]
        }

        self.assertIn(
            "relation:supersedes",
            relations,
        )

        self.assertIn(
            "relation:superseded_by",
            relations,
        )

    def test_provenance_projects_source(
        self,
    ) -> None:
        record = {
            "id": "instance:a",
            "provenance": {
                "sources": [
                    "canon/a.md",
                ],
            },
        }

        direct = (
            self.bridge.direct_edges(
                record
            )
        )

        self.assertTrue(
            any(
                edge.relation
                == "relation:sourced_from"
                and edge.object
                == "source:canon/a.md"
                for edge in direct
            )
        )

    def test_source_record_is_not_mutated(
        self,
    ) -> None:
        record = {
            "id": "instance:a",
            "parent": "instance:b",
            "children": [
                "instance:c",
            ],
        }

        before = repr(record)

        self.bridge.project(
            record
        )

        self.assertEqual(
            repr(record),
            before,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
