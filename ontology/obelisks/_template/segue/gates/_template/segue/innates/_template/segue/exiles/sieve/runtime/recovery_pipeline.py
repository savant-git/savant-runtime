#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


schema = "savant://runtime/sieve/recovery-pipeline/2.0.1"
owner = "sieve"
authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/"
    "segue/gates/_template/segue/innates/_template/"
    "segue/exiles/sieve/runtime"
)

source_custody_path = runtime_root / "source_custody.py"
chatgpt_export_path = runtime_root / "chatgpt_export.py"
candidate_projection_path = runtime_root / "candidate_projection.py"
evolution_reconciliation_path = runtime_root / "evolution_reconciliation.py"
modernization_gate_path = runtime_root / "modernization_gate.py"
source_targeting_path = runtime_root / "source_targeting.py"
convergence_path = runtime_root / "convergence.py"


class recovery_pipeline_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            hasher.update(block)

    return hasher.hexdigest()


def run_json(
    command: list[str],
    *,
    output_path: Path | None = None,
) -> Mapping[str, Any]:
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if process.returncode != 0:
        raise recovery_pipeline_error(
            "stage failed\n"
            f"command: {' '.join(command)}\n"
            f"exit: {process.returncode}\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )

    stdout = process.stdout.strip()

    if stdout:
        try:
            value = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise recovery_pipeline_error(
                "stage returned invalid json on stdout\n"
                f"command: {' '.join(command)}\n"
                f"stdout:\n{process.stdout}\n"
                f"stderr:\n{process.stderr}"
            ) from exc

        if not isinstance(value, Mapping):
            raise recovery_pipeline_error(
                "stage stdout json must be an object"
            )

        return value

    if output_path is not None and output_path.is_file():
        try:
            value = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise recovery_pipeline_error(
                "stage emitted no stdout and its "
                "output file contains invalid json\n"
                f"command: {' '.join(command)}\n"
                f"output: {output_path}"
            ) from exc

        if not isinstance(value, Mapping):
            raise recovery_pipeline_error(
                "stage output json must be an object"
            )

        return value

    raise recovery_pipeline_error(
        "stage succeeded but produced no readable json result\n"
        f"command: {' '.join(command)}\n"
        f"stdout:\n{process.stdout}\n"
        f"stderr:\n{process.stderr}"
    )


def required_runtime_files() -> tuple[Path, ...]:
    return (
        source_custody_path,
        chatgpt_export_path,
        candidate_projection_path,
        evolution_reconciliation_path,
        modernization_gate_path,
        source_targeting_path,
        convergence_path,
    )


def runtime_identity() -> dict[str, Any]:
    files: list[dict[str, Any]] = []

    for path in required_runtime_files():
        if not path.is_file():
            raise recovery_pipeline_error(
                f"required runtime file unavailable: {path}"
            )

        files.append(
            {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": file_digest(path),
            }
        )

    projection = {
        "files": files,
    }

    return {
        "files": files,
        "digest": digest(projection),
    }


def output_paths(
    output_root: Path,
) -> dict[str, Path]:
    return {
        "custody": (
            output_root
            / "receipts"
            / "source-custody.json"
        ),
        "messages": (
            output_root
            / "projections"
            / "source-messages.jsonl"
        ),
        "candidates": (
            output_root
            / "candidates"
            / "savant-candidates.jsonl"
        ),
        "reconciled": (
            output_root
            / "candidates"
            / "reconciled-candidates.jsonl"
        ),
        "clusters": (
            output_root
            / "projections"
            / "evidence-clusters.json"
        ),
        "pipeline_receipt": (
            output_root
            / "receipts"
            / "recovery-pipeline.json"
        ),
    }


def ensure_output_tree(
    output_root: Path,
) -> None:
    for name in (
        "receipts",
        "candidates",
        "code",
        "quarantine",
        "projections",
    ):
        (
            output_root / name
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


def output_identity(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise recovery_pipeline_error(
            f"declared stage output was not created: {path}"
        )

    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": file_digest(path),
    }


def stage_receipt(
    *,
    name: str,
    command: list[str],
    result: Mapping[str, Any],
    outputs: list[Path],
) -> dict[str, Any]:
    output_projection = [
        output_identity(path)
        for path in outputs
    ]

    projection = {
        "name": name,
        "result": dict(result),
        "outputs": output_projection,
    }

    return {
        "name": name,
        "command": command,
        "result": dict(result),
        "outputs": output_projection,
        "stage_digest": digest(projection),
    }


def execute_pipeline(
    *,
    export_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    export_root = export_root.resolve()
    output_root = output_root.resolve()

    if not export_root.is_dir():
        raise recovery_pipeline_error(
            "export root must be an extracted directory: "
            f"{export_root}"
        )

    ensure_output_tree(output_root)

    paths = output_paths(output_root)
    runtime = runtime_identity()
    stages: list[dict[str, Any]] = []

    custody_command = [
        sys.executable,
        str(source_custody_path),
        "--source",
        str(export_root),
        "--output",
        str(paths["custody"]),
    ]

    custody_result = run_json(
        custody_command,
        output_path=paths["custody"],
    )

    stages.append(
        stage_receipt(
            name="source-custody",
            command=custody_command,
            result=custody_result,
            outputs=[
                paths["custody"],
            ],
        )
    )

    export_command = [
        sys.executable,
        str(chatgpt_export_path),
        "--export-root",
        str(export_root),
        "--output",
        str(paths["messages"]),
    ]

    export_result = run_json(
        export_command,
    )

    stages.append(
        stage_receipt(
            name="chatgpt-export",
            command=export_command,
            result=export_result,
            outputs=[
                paths["messages"],
            ],
        )
    )

    candidate_command = [
        sys.executable,
        str(candidate_projection_path),
        "--source",
        str(paths["messages"]),
        "--output",
        str(paths["candidates"]),
    ]

    candidate_result = run_json(
        candidate_command,
    )

    stages.append(
        stage_receipt(
            name="candidate-projection",
            command=candidate_command,
            result=candidate_result,
            outputs=[
                paths["candidates"],
            ],
        )
    )

    reconciliation_command = [
        sys.executable,
        str(evolution_reconciliation_path),
        "--source",
        str(paths["candidates"]),
        "--output",
        str(paths["reconciled"]),
        "--clusters-output",
        str(paths["clusters"]),
    ]

    reconciliation_result = run_json(
        reconciliation_command,
    )

    stages.append(
        stage_receipt(
            name="evolution-reconciliation",
            command=reconciliation_command,
            result=reconciliation_result,
            outputs=[
                paths["reconciled"],
                paths["clusters"],
            ],
        )
    )

    counts = {
        "source_files": custody_result.get(
            "file_count"
        ),
        "source_bytes": custody_result.get(
            "total_bytes"
        ),
        "messages": export_result.get(
            "message_count"
        ),
        "conversations": export_result.get(
            "conversation_count"
        ),
        "candidate_input_records": (
            candidate_result.get(
                "input_records"
            )
        ),
        "retained_candidates": (
            candidate_result.get(
                "retained_candidates"
            )
        ),
        "reconciled_candidates": (
            reconciliation_result.get(
                "candidate_count"
            )
        ),
        "evidence_clusters": (
            reconciliation_result.get(
                "cluster_count"
            )
        ),
        "code_fences": (
            reconciliation_result.get(
                "code_fence_count"
            )
        ),
    }

    receipt = {
        "schema": schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "export_root": str(export_root),
        "output_root": str(output_root),
        "runtime": runtime,
        "stages": stages,
        "counts": counts,
        "boundaries": {
            "source_mutated": False,
            "canon_mutated": False,
            "runtime_mutated_by_recovered_content": False,
            "authority_created": False,
            "historical_material_implemented": False,
            "automatic_admission": False,
            "automatic_modernization": False,
            "automatic_implementation": False,
        },
        "next_gate": {
            "name": (
                "semantic-authority-modernization"
            ),
            "default": "blocked",
            "requirements": [
                "authority-resolution",
                "owner-resolution",
                "supersession-resolution",
                "conflict-resolution",
                "essential-identity-preservation",
                "valid-behavior-preservation",
                "massive-current-savant-modernization",
                "compatibility-verification",
                "implementation-authorization",
            ],
        },
    }

    digest_projection = dict(receipt)

    digest_projection.pop(
        "export_root",
        None,
    )
    digest_projection.pop(
        "output_root",
        None,
    )

    receipt["projection_digest"] = digest(
        digest_projection
    )

    paths[
        "pipeline_receipt"
    ].write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return receipt


def selftest() -> dict[str, Any]:
    expected_names = {
        path.name
        for path in required_runtime_files()
    }

    checks = {
        "authority_none": (
            authority_effect == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "required_dependency_count": (
            len(required_runtime_files())
            == 7
        ),
        "custody_present": (
            "source_custody.py"
            in expected_names
        ),
        "export_present": (
            "chatgpt_export.py"
            in expected_names
        ),
        "candidate_present": (
            "candidate_projection.py"
            in expected_names
        ),
        "reconciliation_present": (
            "evolution_reconciliation.py"
            in expected_names
        ),
        "modernization_gate_present": (
            "modernization_gate.py"
            in expected_names
        ),
        "targeting_present": (
            "source_targeting.py"
            in expected_names
        ),
        "convergence_present": (
            "convergence.py"
            in expected_names
        ),
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "recovery-pipeline-selftest/2.0.1"
        ),
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--export-root",
    )

    parser.add_argument(
        "--output-root",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

    else:
        if not arguments.export_root:
            parser.error(
                "--export-root is required"
            )

        if not arguments.output_root:
            parser.error(
                "--output-root is required"
            )

        result = execute_pipeline(
            export_root=Path(
                arguments.export_root
            ),
            output_root=Path(
                arguments.output_root
            ),
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
