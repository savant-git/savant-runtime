#!/usr/bin/env python3
from __future__ import annotations

import json
import multiprocessing
import sys
import time
from pathlib import Path

import pytest


SUBJECT_ROOT = Path(
    "/root/savant-runtime/edifices/identity/"
    "exiles/niche/prodigals/masterplan"
)

RUNTIME_ROOT = (
    SUBJECT_ROOT
    / "runtime"
)

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(RUNTIME_ROOT),
    )


from masterplan_lock import (  # noqa: E402
    LockPaths,
    MasterplanLock,
    MasterplanLockTimeout,
    MasterplanStaleWriteError,
    deterministic_projection,
    digest,
)


def write_graph(
    path: Path,
    value: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "graph_id": "savant.masterplan",
                "value": value,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def graph_semantic_digest(
    path: Path,
) -> str:
    return digest(
        deterministic_projection(
            json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        )
    )


def hold_lock(
    lock_path: str,
    metadata_path: str,
    ready: multiprocessing.Event,
    release: multiprocessing.Event,
) -> None:
    paths = LockPaths(
        lock=Path(lock_path),
        metadata=Path(
            metadata_path
        ),
    )

    lock = MasterplanLock(
        owner="holder",
        operation="test.hold",
        timeout_seconds=2.0,
        paths=paths,
    )

    lock.acquire()

    ready.set()

    release.wait(
        timeout=5.0
    )

    lock.release(
        passed=True,
    )


def test_equal_metadata_produces_equal_semantic_digest(
    tmp_path: Path,
) -> None:
    paths = LockPaths(
        lock=(
            tmp_path
            / "masterplan.lock"
        ),
        metadata=(
            tmp_path
            / "masterplan.lock.json"
        ),
    )

    first = MasterplanLock(
        owner="test",
        operation="test.operation",
        paths=paths,
    )

    first._lock_id = "lock-fixed"
    first._acquired_at = (
        "2026-08-01T00:00:00+00:00"
    )
    first._pre_graph_digest = (
        "0" * 64
    )

    second = MasterplanLock(
        owner="test",
        operation="test.operation",
        paths=paths,
    )

    second._lock_id = "lock-fixed"
    second._acquired_at = (
        "2026-08-02T00:00:00+00:00"
    )
    second._pre_graph_digest = (
        "0" * 64
    )

    first_value = first._metadata_payload(
        state="held",
    )

    second_value = second._metadata_payload(
        state="held",
    )

    assert digest(
        deterministic_projection(
            first_value
        )
    ) == digest(
        deterministic_projection(
            second_value
        )
    )


def test_second_writer_times_out(
    tmp_path: Path,
) -> None:
    paths = LockPaths(
        lock=(
            tmp_path
            / "masterplan.lock"
        ),
        metadata=(
            tmp_path
            / "masterplan.lock.json"
        ),
    )

    ready = multiprocessing.Event()
    release = multiprocessing.Event()

    process = multiprocessing.Process(
        target=hold_lock,
        args=(
            str(paths.lock),
            str(paths.metadata),
            ready,
            release,
        ),
    )

    process.start()

    assert ready.wait(
        timeout=3.0
    )

    contender = MasterplanLock(
        owner="contender",
        operation="test.contend",
        timeout_seconds=0.2,
        poll_seconds=0.02,
        paths=paths,
    )

    with pytest.raises(
        MasterplanLockTimeout
    ):
        contender.acquire()

    release.set()

    process.join(
        timeout=3.0
    )

    assert (
        process.exitcode
        == 0
    )


def test_expected_digest_rejects_stale_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_path = (
        tmp_path
        / "masterplan.json"
    )

    write_graph(
        graph_path,
        1,
    )

    runtime_module = sys.modules[
        "masterplan_lock"
    ]

    monkeypatch.setattr(
        runtime_module,
        "GRAPH_PATH",
        graph_path,
    )

    paths = LockPaths(
        lock=(
            tmp_path
            / "masterplan.lock"
        ),
        metadata=(
            tmp_path
            / "masterplan.lock.json"
        ),
    )

    lock = MasterplanLock(
        owner="stale-writer",
        operation="test.stale",
        expected_graph_digest=(
            "f" * 64
        ),
        timeout_seconds=1.0,
        paths=paths,
    )

    with pytest.raises(
        MasterplanStaleWriteError
    ):
        lock.acquire()


def test_precondition_detects_external_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_path = (
        tmp_path
        / "masterplan.json"
    )

    write_graph(
        graph_path,
        1,
    )

    runtime_module = sys.modules[
        "masterplan_lock"
    ]

    monkeypatch.setattr(
        runtime_module,
        "GRAPH_PATH",
        graph_path,
    )

    paths = LockPaths(
        lock=(
            tmp_path
            / "masterplan.lock"
        ),
        metadata=(
            tmp_path
            / "masterplan.lock.json"
        ),
    )

    expected = graph_semantic_digest(
        graph_path
    )

    lock = MasterplanLock(
        owner="writer",
        operation="test.precondition",
        expected_graph_digest=(
            expected
        ),
        paths=paths,
    )

    lock.acquire()

    try:
        write_graph(
            graph_path,
            2,
        )

        with pytest.raises(
            MasterplanStaleWriteError
        ):
            lock.validate_graph_precondition()

    finally:
        lock.release(
            passed=False,
        )


def test_lock_metadata_records_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_path = (
        tmp_path
        / "masterplan.json"
    )

    write_graph(
        graph_path,
        1,
    )

    runtime_module = sys.modules[
        "masterplan_lock"
    ]

    monkeypatch.setattr(
        runtime_module,
        "GRAPH_PATH",
        graph_path,
    )

    paths = LockPaths(
        lock=(
            tmp_path
            / "masterplan.lock"
        ),
        metadata=(
            tmp_path
            / "masterplan.lock.json"
        ),
    )

    lock = MasterplanLock(
        owner="project-owner",
        operation="test.metadata",
        paths=paths,
    )

    lock.acquire()

    try:
        metadata = json.loads(
            paths.metadata.read_text(
                encoding="utf-8",
            )
        )

        assert (
            metadata["owner"]
            == "project-owner"
        )

        assert (
            metadata["operation"]
            == "test.metadata"
        )

        assert (
            metadata["state"]
            == "held"
        )

        assert metadata[
            "lock_id"
        ].startswith(
            "lock-"
        )

    finally:
        lock.release(
            passed=True,
        )
