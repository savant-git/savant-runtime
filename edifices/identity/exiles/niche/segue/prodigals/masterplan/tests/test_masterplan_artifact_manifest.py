#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path("/root/savant-runtime")

TOOLS_ROOT = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_ROOT),
    )


from build_masterplan_artifact_manifest import (  # noqa: E402
    ManifestError,
    build_manifest,
    semantic_digest,
    verify_manifest,
)


def authority() -> dict:
    return {
        "state": "accepted",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 1,
        "source": "test",
        "accepted_by": "project-owner",
        "accepted_at": (
            "2026-08-01T00:00:00+00:00"
        ),
        "confidence": 1.0,
    }


def provenance() -> dict:
    return {
        "sources": [],
        "transformations": [],
        "generated_by": "test",
        "generated_at": (
            "2026-08-01T00:00:00+00:00"
        ),
        "contract_version": "1.0.0",
    }


def graph(
    output: str,
) -> dict:
    return {
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(),
        "records": [
            {
                "id": "SAV-P4A-022",
                "kind": "task",
                "title": (
                    "Content-addressed "
                    "output manifests"
                ),
                "description": "",
                "priority": {
                    "band": "P4A",
                    "ordinal": 22,
                    "authority_locked": False,
                    "rationale": "test",
                },
                "status": "active",
                "authority": authority(),
                "purpose": "test",
                "scope": {},
                "acceptance": [
                    "manifest is deterministic"
                ],
                "evidence_requirements": [],
                "outputs": [
                    output
                ],
                "risks": [],
                "security": {},
                "lineage": {},
                "provenance": provenance(),
                "extensions": {},
            }
        ],
        "segues": [],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }


def configure_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: dict,
) -> Path:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    runtime_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    graph_path = (
        runtime_root
        / "authority"
        / "task-graph"
        / "masterplan.json"
    )

    graph_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    graph_path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    module = sys.modules[
        "build_masterplan_artifact_manifest"
    ]

    monkeypatch.setattr(
        module,
        "ROOT",
        runtime_root,
    )

    monkeypatch.setattr(
        module,
        "GRAPH_PATH",
        graph_path,
    )

    monkeypatch.setattr(
        module,
        "MANIFEST_ROOT",
        (
            runtime_root
            / "authority"
            / "task-graph"
            / "manifests"
        ),
    )

    monkeypatch.setattr(
        module,
        "REPORT_ROOT",
        (
            runtime_root
            / "reports"
            / "niche"
            / "masterplan"
            / "manifests"
        ),
    )

    monkeypatch.setattr(
        module,
        "RUNTIME_ROOT",
        (
            runtime_root
            / "runtime"
            / "masterplan"
            / "manifests"
        ),
    )

    return runtime_root


def runtime_output(
    runtime_root: Path,
    name: str,
) -> Path:
    output = (
        runtime_root
        / "artifacts"
        / name
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output


def test_equal_inputs_produce_equal_manifest_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    output = runtime_output(
        runtime_root,
        "artifact.txt",
    )

    output.write_text(
        "stable",
        encoding="utf-8",
    )

    value = graph(
        str(output)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    first = build_manifest(
        value,
        "SAV-P4A-022",
    )

    second = build_manifest(
        copy.deepcopy(value),
        "SAV-P4A-022",
    )

    assert (
        first["manifest_id"]
        == second["manifest_id"]
    )

    assert (
        first["content_digest"]
        == second["content_digest"]
    )


def test_artifact_change_changes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    output = runtime_output(
        runtime_root,
        "artifact.txt",
    )

    output.write_text(
        "first",
        encoding="utf-8",
    )

    value = graph(
        str(output)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    first = build_manifest(
        value,
        "SAV-P4A-022",
    )

    output.write_text(
        "second",
        encoding="utf-8",
    )

    second = build_manifest(
        value,
        "SAV-P4A-022",
    )

    assert (
        first["manifest_id"]
        != second["manifest_id"]
    )


def test_missing_output_is_recorded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    missing = runtime_output(
        runtime_root,
        "missing.txt",
    )

    value = graph(
        str(missing)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    manifest = build_manifest(
        value,
        "SAV-P4A-022",
    )

    assert (
        manifest["statistics"][
            "missing_output_count"
        ]
        == 1
    )

    assert (
        manifest["artifacts"][0][
            "exists"
        ]
        is False
    )


def test_manifest_verification_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    output = runtime_output(
        runtime_root,
        "artifact.txt",
    )

    output.write_text(
        "stable",
        encoding="utf-8",
    )

    value = graph(
        str(output)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    manifest = build_manifest(
        value,
        "SAV-P4A-022",
    )

    result = verify_manifest(
        manifest,
        value,
    )

    assert result[
        "passed"
    ] is True


def test_tampered_manifest_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    output = runtime_output(
        runtime_root,
        "artifact.txt",
    )

    output.write_text(
        "stable",
        encoding="utf-8",
    )

    value = graph(
        str(output)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    manifest = build_manifest(
        value,
        "SAV-P4A-022",
    )

    manifest[
        "artifacts"
    ][0][
        "sha256"
    ] = "0" * 64

    result = verify_manifest(
        manifest,
        value,
    )

    assert result[
        "passed"
    ] is False


def test_directory_manifest_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    output = runtime_output(
        runtime_root,
        "artifact-directory",
    )

    output.mkdir()

    (
        output
        / "a.txt"
    ).write_text(
        "a",
        encoding="utf-8",
    )

    (
        output
        / "b.txt"
    ).write_text(
        "b",
        encoding="utf-8",
    )

    value = graph(
        str(output)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    first = build_manifest(
        value,
        "SAV-P4A-022",
    )

    second = build_manifest(
        copy.deepcopy(value),
        "SAV-P4A-022",
    )

    assert (
        first["content_digest"]
        == second["content_digest"]
    )

    assert (
        first["artifacts"][0][
            "kind"
        ]
        == "directory"
    )


def test_output_outside_runtime_root_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = (
        tmp_path
        / "savant-runtime"
    )

    outside = (
        tmp_path
        / "outside.txt"
    )

    outside.write_text(
        "outside",
        encoding="utf-8",
    )

    value = graph(
        str(outside)
    )

    configure_runtime(
        tmp_path,
        monkeypatch,
        value,
    )

    with pytest.raises(
        ManifestError
    ):
        build_manifest(
            value,
            "SAV-P4A-022",
        )


def test_unknown_task_fails() -> None:
    with pytest.raises(
        KeyError
    ):
        build_manifest(
            graph(
                "/root/savant-runtime/none"
            ),
            "SAV-UNKNOWN",
        )


def test_semantic_digest_is_order_stable() -> None:
    first = {
        "b": 2,
        "a": 1,
    }

    second = {
        "a": 1,
        "b": 2,
    }

    assert semantic_digest(
        first
    ) == semantic_digest(
        second
    )
