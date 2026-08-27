#!/usr/bin/env python3

from pathlib import Path
import sys
import unittest


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from lexicon.kindred.relationship_resolver import (
    KindredRelationshipResolver,
)
from lexicon.kindred.discipline_engine import (
    DisciplineEngine,
    KindredEdge,
)


class KindredRelationshipResolverTests(
    unittest.TestCase
):

    def setUp(
        self,
    ) -> None:
        self.resolver = (
            KindredRelationshipResolver()
        )

    def test_constitutional_relationship_resolves(
        self,
    ) -> None:
        resolved = (
            self.resolver.resolve(
                "relation:depends_on"
            )
        )

        self.assertTrue(
            resolved[
                "authoritative"
            ]
        )

        self.assertEqual(
            resolved[
                "constitutional_id"
            ],
            "relationship:depends_on",
        )

    def test_kindred_alias_does_not_duplicate_authority(
        self,
    ) -> None:
        resolved = (
            self.resolver.resolve(
                "relation:implements"
            )
        )

        self.assertEqual(
            resolved[
                "authority"
            ],
            "constitutional",
        )

    def test_extension_is_explicitly_non_authoritative(
        self,
    ) -> None:
        projection = (
            self.resolver.projection()
        )

        for relation_id in projection[
            "projected_extensions"
        ]:
            resolved = (
                self.resolver.resolve(
                    relation_id
                )
            )

            self.assertFalse(
                resolved[
                    "authoritative"
                ]
            )

    def test_discipline_edge_exposes_authority_resolution(
        self,
    ) -> None:
        engine = DisciplineEngine()

        edge = KindredEdge(
            subject="instance:a",
            relation=(
                "relation:depends_on"
            ),
            object="instance:b",
            basis="focused-test",
        )

        normalized = (
            engine.normalize_edge(
                edge
            )
        )

        self.assertEqual(
            normalized[
                "constitutional_relationship"
            ],
            "relationship:depends_on",
        )

        self.assertTrue(
            normalized[
                "relationship_authoritative"
            ]
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
