#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "build_masterplan_opus_packet.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "build_masterplan_opus_packet",
            MODULE_PATH,
        )
    )

    if specification is None:
        raise RuntimeError(
            "unable to create module specification"
        )

    if specification.loader is None:
        raise RuntimeError(
            "module specification lacks loader"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


packet_builder = load_module()


class MasterplanOpusPacketTests(
    unittest.TestCase
):

    def test_nine_assignments(
        self,
    ) -> None:
        self.assertEqual(
            len(
                packet_builder
                .ANALYSIS_ASSIGNMENTS
            ),
            9,
        )

        keys = [
            assignment[0]
            for assignment
            in packet_builder
            .ANALYSIS_ASSIGNMENTS
        ]

        self.assertEqual(
            len(keys),
            len(set(keys)),
        )

    def test_nine_response_sections(
        self,
    ) -> None:
        self.assertEqual(
            len(
                packet_builder
                .REQUIRED_RESPONSE_SECTIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    packet_builder
                    .REQUIRED_RESPONSE_SECTIONS
                )
            ),
            9,
        )

    def test_nine_forbidden_actions(
        self,
    ) -> None:
        self.assertEqual(
            len(
                packet_builder
                .FORBIDDEN_AI_ACTIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    packet_builder
                    .FORBIDDEN_AI_ACTIONS
                )
            ),
            9,
        )

    def test_nine_allowed_actions(
        self,
    ) -> None:
        self.assertEqual(
            len(
                packet_builder
                .ALLOWED_AI_ACTIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    packet_builder
                    .ALLOWED_AI_ACTIONS
                )
            ),
            9,
        )

    def test_task_index(
        self,
    ) -> None:
        graph = {
            "records": [
                {
                    "id": "TASK-001",
                    "kind": "task",
                    "scope": {
                        "depends_on": [],
                    },
                },
                {
                    "id": "EVENT-001",
                    "kind": "event",
                },
            ],
        }

        index = (
            packet_builder
            .graph_task_index(
                graph
            )
        )

        self.assertEqual(
            list(index),
            [
                "TASK-001",
            ],
        )

    def test_dependency_closure_order(
        self,
    ) -> None:
        first = {
            "id": "TASK-001",
            "kind": "task",
            "scope": {
                "depends_on": [],
            },
        }

        second = {
            "id": "TASK-002",
            "kind": "task",
            "scope": {
                "depends_on": [
                    "TASK-001",
                ],
            },
        }

        third = {
            "id": "TASK-003",
            "kind": "task",
            "scope": {
                "depends_on": [
                    "TASK-002",
                ],
            },
        }

        closure = (
            packet_builder
            .dependency_closure(
                third,
                {
                    "TASK-001": first,
                    "TASK-002": second,
                    "TASK-003": third,
                },
            )
        )

        self.assertEqual(
            [
                task["id"]
                for task in closure
            ],
            [
                "TASK-001",
                "TASK-002",
            ],
        )

    def test_dependency_cycle_fails(
        self,
    ) -> None:
        first = {
            "id": "TASK-001",
            "kind": "task",
            "scope": {
                "depends_on": [
                    "TASK-002",
                ],
            },
        }

        second = {
            "id": "TASK-002",
            "kind": "task",
            "scope": {
                "depends_on": [
                    "TASK-001",
                ],
            },
        }

        with self.assertRaises(
            packet_builder.PacketError
        ):
            (
                packet_builder
                .dependency_closure(
                    first,
                    {
                        "TASK-001": first,
                        "TASK-002": second,
                    },
                )
            )

    def test_assignment_digest_is_stable(
        self,
    ) -> None:
        task = {
            "id": "TASK-001",
        }

        first = (
            packet_builder
            .build_assignment(
                ordinal=1,
                key="authority",
                title="Authority analysis",
                purpose="Analyze authority.",
                task=task,
                dependency_ids=(),
                graph_digest="abc",
            )
        )

        second = (
            packet_builder
            .build_assignment(
                ordinal=1,
                key="authority",
                title="Authority analysis",
                purpose="Analyze authority.",
                task=task,
                dependency_ids=(),
                graph_digest="abc",
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_packet_forbids_ai_authority(
        self,
    ) -> None:
        self.assertIn(
            "manufacture_authority",
            packet_builder
            .FORBIDDEN_AI_ACTIONS,
        )

        self.assertIn(
            "accept_own_proposal",
            packet_builder
            .FORBIDDEN_AI_ACTIONS,
        )

        self.assertIn(
            "promote_inference_directly_to_authority",
            packet_builder
            .FORBIDDEN_AI_ACTIONS,
        )


if __name__ == "__main__":
    unittest.main()
