#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


MODULE_PATH = Path(
    "/root/savant-runtime/tools/niche/masterplan/"
    "compile_masterplan_opus_binding_plan.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "compile_masterplan_opus_binding_plan",
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


planner = load_module()


class MasterplanOpusBindingPlanTests(
    unittest.TestCase
):

    def test_nine_binding_layers(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.BINDING_LAYERS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.BINDING_LAYERS
                )
            ),
            9,
        )

    def test_nine_binding_actions(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.BINDING_ACTIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.BINDING_ACTIONS
                )
            ),
            9,
        )

    def test_nine_capabilities(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.CAPABILITY_TO_LAYER
            ),
            9,
        )

        self.assertEqual(
            set(
                planner.CAPABILITY_TO_LAYER
            ),
            set(
                planner.CAPABILITY_REQUIREMENTS
            ),
        )

    def test_nine_lifecycle_transitions(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.LIFECYCLE_TRANSITIONS
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.LIFECYCLE_TRANSITIONS
                )
            ),
            9,
        )

    def test_nine_validation_gates(
        self,
    ) -> None:
        self.assertEqual(
            len(
                planner.VALIDATION_GATES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    planner.VALIDATION_GATES
                )
            ),
            9,
        )

    def sample_discovery(
        self,
        complete: bool,
    ) -> dict[str, object]:
        matrix = {
            capability: (
                [
                    (
                        "/root/savant-runtime/"
                        f"opus/{capability}.py"
                    )
                ]
                if complete
                else []
            )
            for capability
            in planner.CAPABILITY_TO_LAYER
        }

        return {
            "selection_state": "selected",
            "selected_candidate": {
                "path": (
                    "/root/savant-runtime/"
                    "edifices/identity/"
                    "exiles/opus"
                ),
            },
            "capability_matrix": matrix,
            "semantic_digest": "abc",
        }

    def sample_queue(
        self,
    ) -> dict[str, object]:
        return {
            "queue_id": (
                "masterplan-opus-queue:test"
            ),
            "queue_digest": "def",
            "record_count": 9,
            "task": {
                "id": "TASK-001",
                "title": "Test task",
            },
        }

    def write_fixture(
        self,
        root: Path,
        name: str,
        value: dict[str, Any],
    ) -> Path:
        path = (
            root
            / name
        )

        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return path

    def build_fixture_plan(
        self,
        *,
        discovery: dict[str, object],
        queue: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(
            prefix=(
                "savant-masterplan-"
                "opus-binding-plan-test-"
            ),
            dir=(
                "/root/savant-runtime"
            ),
        ) as raw_directory:
            fixture_root = Path(
                raw_directory
            )

            discovery_path = self.write_fixture(
                fixture_root,
                "discovery.json",
                discovery,
            )

            queue_value = (
                queue
                if queue is not None
                else self.sample_queue()
            )

            queue_path = self.write_fixture(
                fixture_root,
                "queue.json",
                queue_value,
            )

            return planner.build_plan(
                discovery_path=discovery_path,
                discovery=discovery,
                queue_path=queue_path,
                queue=queue_value,
            )

    def test_complete_discovery_plans(
        self,
    ) -> None:
        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                True
            ),
        )

        self.assertEqual(
            plan[
                "state"
            ],
            "planned",
        )

        self.assertEqual(
            plan[
                "blockers"
            ],
            [],
        )

        self.assertEqual(
            len(
                plan[
                    "capability_plans"
                ]
            ),
            9,
        )

        planner.verify_plan(
            plan
        )

    def test_missing_capabilities_block(
        self,
    ) -> None:
        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                False
            ),
        )

        self.assertEqual(
            plan[
                "state"
            ],
            "blocked",
        )

        self.assertEqual(
            len(
                plan[
                    "blockers"
                ]
            ),
            9,
        )

        self.assertTrue(
            all(
                item[
                    "implementation_required"
                ]
                is True
                for item in plan[
                    "capability_plans"
                ]
            )
        )

        planner.verify_plan(
            plan
        )

    def test_unselected_runtime_blocks(
        self,
    ) -> None:
        discovery = self.sample_discovery(
            True
        )

        discovery[
            "selection_state"
        ] = "authority_required"

        discovery[
            "selected_candidate"
        ] = None

        plan = self.build_fixture_plan(
            discovery=discovery,
        )

        self.assertEqual(
            plan[
                "state"
            ],
            "blocked",
        )

        self.assertIn(
            (
                "current Opus runtime is "
                "not uniquely selected"
            ),
            plan[
                "blockers"
            ],
        )

        self.assertIn(
            (
                "selected Opus runtime path "
                "is unavailable"
            ),
            plan[
                "blockers"
            ],
        )

        planner.verify_plan(
            plan
        )

    def test_invalid_queue_cardinality_blocks(
        self,
    ) -> None:
        queue = self.sample_queue()

        queue[
            "record_count"
        ] = 3

        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                True
            ),
            queue=queue,
        )

        self.assertEqual(
            plan[
                "state"
            ],
            "blocked",
        )

        self.assertIn(
            (
                "Masterplan Opus queue does not "
                "contain exactly nine work records"
            ),
            plan[
                "blockers"
            ],
        )

    def test_capability_plans_preserve_source_paths(
        self,
    ) -> None:
        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                True
            ),
        )

        for capability_plan in plan[
            "capability_plans"
        ]:
            self.assertTrue(
                capability_plan[
                    "source_present"
                ]
            )

            self.assertEqual(
                len(
                    capability_plan[
                        "source_paths"
                    ]
                ),
                1,
            )

            self.assertEqual(
                capability_plan[
                    "action"
                ],
                "adapt",
            )

    def test_missing_capabilities_require_extension(
        self,
    ) -> None:
        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                False
            ),
        )

        for capability_plan in plan[
            "capability_plans"
        ]:
            self.assertFalse(
                capability_plan[
                    "source_present"
                ]
            )

            self.assertEqual(
                capability_plan[
                    "action"
                ],
                "extend",
            )

            self.assertTrue(
                capability_plan[
                    "blockers"
                ]
            )

    def test_authority_remains_withheld(
        self,
    ) -> None:
        plan = self.build_fixture_plan(
            discovery=self.sample_discovery(
                True
            ),
        )

        authority = plan[
            "authority"
        ]

        self.assertEqual(
            authority[
                "effect"
            ],
            "none",
        )

        self.assertIs(
            authority[
                "implementation_authorized"
            ],
            False,
        )

        self.assertIs(
            authority[
                "provider_execution_authorized"
            ],
            False,
        )

        self.assertIs(
            authority[
                "task_transition_authorized"
            ],
            False,
        )

        self.assertIs(
            authority[
                "evidence_admission_authorized"
            ],
            False,
        )

    def test_provenance_uses_existing_fixture_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix=(
                "savant-masterplan-"
                "opus-binding-provenance-test-"
            ),
            dir=(
                "/root/savant-runtime"
            ),
        ) as raw_directory:
            fixture_root = Path(
                raw_directory
            )

            discovery = self.sample_discovery(
                True
            )

            queue = self.sample_queue()

            discovery_path = self.write_fixture(
                fixture_root,
                "discovery.json",
                discovery,
            )

            queue_path = self.write_fixture(
                fixture_root,
                "queue.json",
                queue,
            )

            plan = planner.build_plan(
                discovery_path=discovery_path,
                discovery=discovery,
                queue_path=queue_path,
                queue=queue,
            )

            sources = plan[
                "provenance"
            ][
                "sources"
            ]

            self.assertEqual(
                sources[
                    0
                ][
                    "path"
                ],
                str(
                    discovery_path
                ),
            )

            self.assertEqual(
                sources[
                    1
                ][
                    "path"
                ],
                str(
                    queue_path
                ),
            )

            self.assertEqual(
                sources[
                    0
                ][
                    "sha256"
                ],
                planner.sha256_bytes(
                    discovery_path.read_bytes()
                ),
            )

            self.assertEqual(
                sources[
                    1
                ][
                    "sha256"
                ],
                planner.sha256_bytes(
                    queue_path.read_bytes()
                ),
            )

    def test_semantic_digest_is_stable(
        self,
    ) -> None:
        first = planner.semantic_digest(
            {
                "b": 2,
                "a": 1,
            }
        )

        second = planner.semantic_digest(
            {
                "a": 1,
                "b": 2,
            }
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
