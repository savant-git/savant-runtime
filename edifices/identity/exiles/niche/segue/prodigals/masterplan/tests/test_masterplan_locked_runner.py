#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pytest


TOOLS_ROOT = (
    Path("/root/savant-runtime")
    / "tools"
    / "niche"
    / "masterplan"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(
            TOOLS_ROOT
        ),
    )


from run_masterplan_locked import (  # noqa: E402
    build_environment,
    validate_command,
)


class FakeLock:
    owner = "test-owner"
    operation = "test-operation"
    _lock_id = "lock-test"


def test_empty_command_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        validate_command(
            []
        )


def test_missing_absolute_command_is_rejected() -> None:
    with pytest.raises(
        FileNotFoundError
    ):
        validate_command(
            [
                (
                    "/root/savant-runtime/"
                    "bin/does-not-exist"
                )
            ]
        )


def test_environment_exposes_lock_context() -> None:
    environment = build_environment(
        FakeLock(),
        "a" * 64,
    )

    assert (
        environment[
            "SAVANT_MASTERPLAN_LOCKED"
        ]
        == "1"
    )

    assert (
        environment[
            "SAVANT_MASTERPLAN_LOCK_ID"
        ]
        == "lock-test"
    )

    assert (
        environment[
            "SAVANT_MASTERPLAN_LOCK_OWNER"
        ]
        == "test-owner"
    )

    assert (
        environment[
            "SAVANT_MASTERPLAN_OPERATION"
        ]
        == "test-operation"
    )

    assert (
        environment[
            "SAVANT_MASTERPLAN_EXPECTED_DIGEST"
        ]
        == "a" * 64
    )
