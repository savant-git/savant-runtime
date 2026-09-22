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
    "compile_masterplan_opus_binding_workspace.py"
)


def load_module():
    specification = (
        importlib.util.spec_from_file_location(
            "compile_masterplan_opus_binding_workspace",
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


class MasterplanOpusBindingWorkspaceTests(
    unittest.TestCase
):

    def test_nine_workspace_states_or_three(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.WORKSPACE_STATES
            ),
            3,
        )

    def test_nine_source_classes(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.SOURCE_CLASSES
            ),
            9,
        )

        self.assertEqual(
            len(
                set(
                    compiler.SOURCE_CLASSES
                )
            ),
            9,
        )

    def test_nine_capabilities(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.CAPABILITIES
            ),
            9,
        )

    def test_nine_implementation_phases(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.IMPLEMENTATION_PHASES
            ),
            9,
        )

    def test_nine_validation_phases(
        self,
    ) -> None:
        self.assertEqual(
            len(
                compiler.VALIDATION_PHASES
            ),
            9,
        )

    def write_json(
        self,
        path: Path,
        value: dict[str, Any],
    ) -> None:
        path.write_text(
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def fixture(
        self,
        root: Path,
        *,
        plan_state: str = "planned",
        omit_capability: str | None = None,
    ) -> tuple[
        Path,
        dict[str, Any],
        Path,
        dict[str, Any],
    ]:
        runtime_root = (
            root
            / "opus"
        )

        runtime_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        artifacts = []

        capability_plans = []

        for ordinal, capability in enumerate(
            compiler.CAPABILITIES,
            start=1,
        ):
            source_path = (
                runtime_root
                / f"{capability}.py"
            )

            source_path.write_text(
                (
                    "#!/usr/bin/env python3\n"
                    f'CAPABILITY = "{capability}"\n'
                ),
                encoding="utf-8",
            )

            digest = compiler.sha256_bytes(
                source_path.read_bytes()
            )

            capabilities = (
                []
                if capability
                == omit_capability
                else [
                    capability,
                ]
            )

            artifacts.append(
                {
                    "path": str(
                        source_path
                    ),
                    "relative_path": (
                        source_path.relative_to(
                            runtime_root
                        ).as_posix()
                    ),
                    "suffix": ".py",
                    "size": (
                        source_path.stat().st_size
                    ),
                    "sha256": digest,
                    "artifact_class": (
                        compiler.SOURCE_CLASSES[
                            ordinal - 1
                        ]
                    ),
                    "authority_score": 1,
                    "historical_score": 0,
                    "symbols": [],
                    "imports": [],
                    "capabilities": (
                        capabilities
                    ),
                }
            )

            capability_plans.append(
                {
                    "ordinal": ordinal,
                    "capability": capability,
                    "layer": (
                        compiler.IMPLEMENTATION_PHASES[
                            ordinal - 1
                        ]
                    ),
                    "action": "adapt",
                    "requirement": (
                        f"Bind {capability}."
                    ),
                    "source_paths": [
                        str(
                            source_path
                        ),
                    ],
                    "source_present": True,
                    "implementation_required": True,
                    "blockers": [],
                }
            )

        discovery = {
            "selected_candidate": {
                "path": str(
                    runtime_root
                ),
            },
            "selected_artifacts": artifacts,
            "semantic_digest": "discovery",
        }

        plan = {
            "plan_id": "plan:test",
            "semantic_digest": "plan",
            "state": plan_state,
            "task": {
                "id": "TASK-001",
                "title": "Test",
            },
            "capability_plans": (
                capability_plans
            ),
            "blockers": (
                []
                if plan_state
                == "planned"
                else [
                    "plan blocked",
                ]
            ),
        }

        discovery_path = (
            root
            / "discovery.json"
        )

        plan_path = (
            root
            / "plan.json"
        )

        self.write_json(
            discovery_path,
            discovery,
        )

        self.write_json(
            plan_path,
            plan,
        )

        return (
            plan_path,
            plan,
            discovery_path,
            discovery,
        )

    def test_ready_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="savant-workspace-test-",
            dir="/root/savant-runtime",
        ) as raw:
            (
                plan_path,
                plan,
                discovery_path,
                discovery,
            ) = self.fixture(
                Path(
                    raw
                )
            )

            workspace = (
                compiler.build_workspace(
                    plan_path=plan_path,
                    plan=plan,
                    discovery_path=(
                        discovery_path
                    ),
                    discovery=discovery,
                )
            )

            self.assertEqual(
                workspace[
                    "state"
                ],
                "ready",
            )

            self.assertEqual(
                len(
                    workspace[
                        "capability_workspaces"
                    ]
                ),
                9,
            )

            compiler.verify_workspace(
                workspace
            )

    def test_blocked_plan_blocks_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="savant-workspace-test-",
            dir="/root/savant-runtime",
        ) as raw:
            (
                plan_path,
                plan,
                discovery_path,
                discovery,
            ) = self.fixture(
                Path(
                    raw
                ),
                plan_state="blocked",
            )

            workspace = (
                compiler.build_workspace(
                    plan_path=plan_path,
                    plan=plan,
                    discovery_path=(
                        discovery_path
                    ),
                    discovery=discovery,
                )
            )

            self.assertEqual(
                workspace[
                    "state"
                ],
                "blocked",
            )

            self.assertIn(
                "plan blocked",
                workspace[
                    "blockers"
                ],
            )

    def test_missing_capability_blocks_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="savant-workspace-test-",
            dir="/root/savant-runtime",
        ) as raw:
            (
                plan_path,
                plan,
                discovery_path,
                discovery,
            ) = self.fixture(
                Path(
                    raw
                ),
                omit_capability=(
                    "event_publication"
                ),
            )

            workspace = (
                compiler.build_workspace(
                    plan_path=plan_path,
                    plan=plan,
                    discovery_path=(
                        discovery_path
                    ),
                    discovery=discovery,
                )
            )

            self.assertEqual(
                workspace[
                    "state"
                ],
                "blocked",
            )

            self.assertTrue(
                any(
                    "event_publication"
                    in blocker
                    or (
                        "no current source artifact"
                        in blocker
                    )
                    for blocker in workspace[
                        "blockers"
                    ]
                )
            )

    def test_changed_source_blocks_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="savant-workspace-test-",
            dir="/root/savant-runtime",
        ) as raw:
            root = Path(
                raw
            )

            (
                plan_path,
                plan,
                discovery_path,
                discovery,
            ) = self.fixture(
                root
            )

            first_path = Path(
                discovery[
                    "selected_artifacts"
                ][0][
                    "path"
                ]
            )

            first_path.write_text(
                "changed\n",
                encoding="utf-8",
            )

            workspace = (
                compiler.build_workspace(
                    plan_path=plan_path,
                    plan=plan,
                    discovery_path=(
                        discovery_path
                    ),
                    discovery=discovery,
                )
            )

            self.assertEqual(
                workspace[
                    "state"
                ],
                "blocked",
            )

            self.assertIn(
                (
                    "source artifact changed "
                    "after discovery"
                ),
                workspace[
                    "blockers"
                ],
            )

    def test_artifact_identity_is_stable(
        self,
    ) -> None:
        first = compiler.artifact_identity(
            "/root/savant-runtime/a.py",
            "abc",
        )

        second = compiler.artifact_identity(
            "/root/savant-runtime/a.py",
            "abc",
        )

        self.assertEqual(
            first,
            second,
        )

    def test_workspace_withholds_authority(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="savant-workspace-test-",
            dir="/root/savant-runtime",
        ) as raw:
            (
                plan_path,
                plan,
                discovery_path,
                discovery,
            ) = self.fixture(
                Path(
                    raw
                )
            )

            workspace = (
                compiler.build_workspace(
                    plan_path=plan_path,
                    plan=plan,
                    discovery_path=(
                        discovery_path
                    ),
                    discovery=discovery,
                )
            )

            authority = workspace[
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


if __name__ == "__main__":
    unittest.main()
