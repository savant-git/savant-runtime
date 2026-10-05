#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "compile_masterplan_opus_queue.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "compile_masterplan_opus_queue",
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

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


compiler = load_module()


class MasterplanOpusQueueTests(
    unittest.TestCase
):

    def test_nine_queue_states(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.QUEUE_STATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.QUEUE_STATES
                )
            ),
            9,
        )

    def test_nine_execution_policies(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.EXECUTION_POLICIES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.EXECUTION_POLICIES
                )
            ),
            9,
        )

    def test_nine_response_sections(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.RESPONSE_SECTIONS
            ),
            9,
        )

    def test_nine_assignments(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.ASSIGNMENT_ORDER
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.ASSIGNMENT_ORDER
                )
            ),
            9,
        )

    def test_nine_provider_capabilities(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.PROVIDER_CAPABILITIES
            ),
            9,
        )

    def test_nine_forbidden_effects(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.FORBIDDEN_EFFECTS
            ),
            9,
        )

    def test_assignment_graph_is_valid(
        self,
    ) -> None:
        compiler.validate_assignment_graph()

    def test_integration_depends_on_all_prior_assignments(
        self,
    ) -> None:
        self.assertEqual(
            compiler.ASSIGNMENT_DEPENDENCIES[
                "integration"
            ],
            compiler.ASSIGNMENT_ORDER[
                :-1
            ],
        )

    def sample_packet(
        self,
    ) -> dict[str, object]:
        assignments = []

        for ordinal, key in enumerate(
            compiler.ASSIGNMENT_ORDER,
            start=1,
        ):
            assignments.append(
                {
                    "id": (
                        f"opus-assignment:"
                        f"TASK-001:"
                        f"{ordinal:02d}:"
                        f"{key}"
                    ),
                    "ordinal": ordinal,
                    "key": key,
                    "title": (
                        f"{key.title()} analysis"
                    ),
                    "purpose": (
                        f"Analyze {key}."
                    ),
                    "dependency_ids": [],
                    "requirements": {},
                }
            )

        return {
            "packet_id": (
                "masterplan-opus-packet:test"
            ),
            "packet_digest": "abc",
            "selected_task": {
                "id": "TASK-001",
                "title": "Test task",
            },
            "authority": {
                "authority_effect": "none",
            },
            "opus_policy": {
                "provider_outputs_are_authority": False,
            },
            "assignments": assignments,
        }

    def test_assignment_index(
        self,
    ) -> None:
        index = compiler.assignment_index(
            self.sample_packet()
        )

        self.assertEqual(
            tuple(
                index
            ),
            compiler.ASSIGNMENT_ORDER,
        )

    def test_request_is_deterministic(
        self,
    ) -> None:
        packet = self.sample_packet()

        assignment = packet[
            "assignments"
        ][0]

        first = compiler.build_request(
            packet=packet,
            assignment=assignment,
            dependency_keys=(),
        )

        second = compiler.build_request(
            packet=packet,
            assignment=assignment,
            dependency_keys=(),
        )

        self.assertEqual(
            first,
            second,
        )

        compiler.validate_request(
            first
        )

    def test_request_forbids_authority(
        self,
    ) -> None:
        packet = self.sample_packet()

        request = compiler.build_request(
            packet=packet,
            assignment=packet[
                "assignments"
            ][0],
            dependency_keys=(),
        )

        self.assertIs(
            request[
                "policy"
            ][
                "provider_output_authority"
            ],
            False,
        )

        self.assertEqual(
            request[
                "policy"
            ][
                "authority_effect"
            ],
            "none",
        )

    def test_compile_queue_has_nine_records(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original_resolver = (
                compiler.resolve_packet_path
            )

            compiler.resolve_packet_path = (
                lambda: Path(
                    "/root/savant-runtime/"
                    "packet.json"
                )
            )

            try:
                queue, paths = (
                    compiler.compile_queue(
                        self.sample_packet(),
                        Path(
                            raw
                        ),
                    )
                )
            finally:
                compiler.resolve_packet_path = (
                    original_resolver
                )

            self.assertEqual(
                queue[
                    "record_count"
                ],
                9,
            )

            self.assertEqual(
                len(
                    queue[
                        "records"
                    ]
                ),
                9,
            )

            self.assertEqual(
                len(paths),
                18,
            )

            compiler.verify_queue(
                queue
            )

    def test_record_dependencies_use_record_ids(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original_resolver = (
                compiler.resolve_packet_path
            )

            compiler.resolve_packet_path = (
                lambda: Path(
                    "/root/savant-runtime/"
                    "packet.json"
                )
            )

            try:
                queue, _ = (
                    compiler.compile_queue(
                        self.sample_packet(),
                        Path(
                            raw
                        ),
                    )
                )
            finally:
                compiler.resolve_packet_path = (
                    original_resolver
                )

            records = {
                record[
                    "assignment"
                ][
                    "key"
                ]: record
                for record in queue[
                    "records"
                ]
            }

            implementation = records[
                "implementation"
            ]

            self.assertEqual(
                implementation[
                    "dependencies"
                ][
                    "assignment_keys"
                ],
                [
                    "authority",
                    "dependencies",
                ],
            )

            self.assertEqual(
                len(
                    implementation[
                        "dependencies"
                    ][
                        "record_ids"
                    ]
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
