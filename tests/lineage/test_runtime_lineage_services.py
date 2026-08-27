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


from runtime.palaver.authority.authority_engine import (  # noqa: E402
    compile_authority_index,
)

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)

from runtime.palaver.investigation.investigation_packet_builder import (  # noqa: E402
    build_investigation,
)


def graph_fixture() -> dict:
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
                "id": "policy.alpha",
                "canonical_id": (
                    "policy.alpha"
                ),
                "label": "Policy Alpha",
                "kind": "policy",
                "authority": True,
                "parents": [],
                "children": [
                    "instance.alpha"
                ],
                "mothers": [],
                "fathers": [],
                "daughters": [
                    "instance.alpha"
                ],
                "sons": [],
                "metadata": {},
                "provenance": {
                    "source": "test"
                },
            },
            {
                "id": "instance.alpha",
                "canonical_id": (
                    "instance.alpha"
                ),
                "label": (
                    "Instance Alpha"
                ),
                "kind": "runtime",
                "authority": False,
                "parents": [
                    "policy.alpha"
                ],
                "children": [
                    "projection.alpha"
                ],
                "mothers": [],
                "fathers": [],
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
                    "instance.alpha"
                ],
                "children": [],
                "mothers": [],
                "fathers": [],
                "daughters": [],
                "sons": [],
                "metadata": {
                    "lineage_placeholder": (
                        True
                    )
                },
                "provenance": None,
            },
        ],
        "edges": [
            {
                "id": (
                    "edge.authority"
                ),
                "source": (
                    "policy.alpha"
                ),
                "target": (
                    "instance.alpha"
                ),
                "role": "authority",
                "axis": "governance",
                "continuation": (
                    "preserving"
                ),
                "status": "active",
            },
            {
                "id": (
                    "edge.projection"
                ),
                "source": (
                    "instance.alpha"
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
            },
        ],
    }


def policy_fixture() -> dict:
    return {
        "id": "policy.test",
        "version": "1.0.0",
        "incoming_role_weights": {
            "authority": 100,
            "projection": 1,
        },
        "outgoing_role_weights": {
            "authority": 50,
            "projection": 1,
        },
        "explicit_authority_weight": 150,
        "authority_kinds": [
            "policy"
        ],
        "authority_kind_weight": 75,
        "placeholder_penalty": 200,
        "governing_roles": [
            "authority"
        ],
        "tiers": [
            {
                "id": (
                    "constitutional"
                ),
                "minimum_score": 250,
            },
            {
                "id": "governing",
                "minimum_score": 150,
            },
            {
                "id": (
                    "authoritative"
                ),
                "minimum_score": 75,
            },
            {
                "id": "structural",
                "minimum_score": 1,
            },
            {
                "id": "derivative",
                "minimum_score": 0,
            },
        ],
    }


class RuntimeLineageServiceTests(
    unittest.TestCase
):
    def test_authority_is_projected_from_roles(
        self,
    ) -> None:
        payload = compile_authority_index(
            graph_fixture(),
            structural_payload={
                "fields": []
            },
            policy=policy_fixture(),
        )

        instance = next(
            record
            for record
            in payload["records"]
            if record["id"]
            == "instance.alpha"
        )

        self.assertIn(
            "policy.alpha",
            instance[
                "direct_authority_sources"
            ],
        )

        self.assertGreaterEqual(
            instance[
                "authority_score"
            ],
            75,
        )

    def test_explicit_policy_has_higher_authority(
        self,
    ) -> None:
        payload = compile_authority_index(
            graph_fixture(),
            structural_payload={
                "fields": []
            },
            policy=policy_fixture(),
        )

        records = {
            record["id"]: record
            for record
            in payload["records"]
        }

        self.assertGreater(
            records[
                "policy.alpha"
            ][
                "authority_score"
            ],
            records[
                "projection.alpha"
            ][
                "authority_score"
            ],
        )

    def test_investigation_traverses_role_edges(
        self,
    ) -> None:
        graph = graph_fixture()

        authority = compile_authority_index(
            graph,
            structural_payload={
                "fields": []
            },
            policy=policy_fixture(),
        )

        packet = build_investigation(
            RuntimeGraphIndex(
                graph
            ),
            title=(
                "Authority trace"
            ),
            objective=(
                "trace policy authority"
            ),
            starting_nodes=[
                "instance.alpha"
            ],
            direction="parents",
            roles=[
                "authority"
            ],
            depth=2,
            authority_payload=(
                authority
            ),
        )

        self.assertIn(
            "policy.alpha",
            packet.traversed_nodes,
        )

        self.assertIn(
            "edge.authority",
            packet.traversed_edges,
        )

        self.assertIn(
            "policy.alpha",
            packet.authority_sources,
        )

    def test_investigation_exposes_uncertainty(
        self,
    ) -> None:
        packet = build_investigation(
            RuntimeGraphIndex(
                graph_fixture()
            ),
            title=(
                "Projection trace"
            ),
            objective=(
                "inspect projection"
            ),
            starting_nodes=[
                "projection.alpha"
            ],
            direction="both",
            depth=0,
        )

        self.assertIn(
            "projection.alpha",
            packet.uncertainty_regions,
        )

        self.assertTrue(
            packet.deterministic_hash
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
