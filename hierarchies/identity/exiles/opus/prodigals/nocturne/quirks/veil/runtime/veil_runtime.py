#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(__file__).resolve().parent
SUBJECT_ROOT = RUNTIME_ROOT.parent
CONTRACTS_ROOT = SUBJECT_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from veil_contracts import (  # noqa: E402
    AuthorityState,
    DECLARED_CAPABILITIES,
    FailureRecord,
    ProvenanceEnvelope,
    VeilProjection,
    VeilRequest,
    VeilResult,
)


RUNTIME_ID = 'quirk.nocturne.veil.runtime'
RUNTIME_VERSION = "1.0.0"
AUTHORITATIVE_PURPOSE = 'Circuit rotation, traffic mixing, timing obfuscation, and identity blending across the Tor network.'

VOLATILE_FIELDS = {
    "duration_seconds",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}


def canonical_bytes(
    value: Any,
) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json"
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json"
        )

    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def build_provenance(
    request: VeilRequest,
    transformations: tuple[str, ...],
) -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        sources=request.provenance.sources,
        transformations=transformations,
        generated_by=f"{RUNTIME_ID}@{RUNTIME_VERSION}",
        generated_at=request.provenance.generated_at,
    )


def run(
    request: VeilRequest,
) -> VeilResult:
    started = time.perf_counter()

    provenance = build_provenance(
        request,
        (
            "validate_request",
            "resolve_declared_capabilities",
            "project_authoritative_primitives",
            "emit_deterministic_result",
        ),
    )

    try:
        admitted = tuple(
            sorted(
                request.policy.allowed_capabilities
            )
        )

        projection_body = {
            "subject_id": 'quirk.nocturne.veil',
            "request_id": request.request_id,
            "operation": request.operation,
            "purpose": request.purpose,
            "payload_digest": digest(
                deterministic_projection(
                    request.payload
                )
            ),
            "admitted_capabilities": admitted,
            "authority": AuthorityState.PROPOSED.value,
        }

        projection_digest = digest(
            projection_body
        )

        projection = VeilProjection(
            projection_id=(
                f"veil-projection-"
                f"{projection_digest[:20]}"
            ),
            subject_id='quirk.nocturne.veil',
            request_id=request.request_id,
            operation=request.operation,
            purpose=request.purpose,
            payload_digest=projection_body[
                "payload_digest"
            ],
            admitted_capabilities=admitted,
            authority=AuthorityState.PROPOSED,
            deterministic=True,
            provenance=provenance,
        )

        result_body = {
            "operation": "run",
            "passed": True,
            "request_id": request.request_id,
            "projection": deterministic_projection(
                projection
            ),
        }

        return VeilResult(
            operation="run",
            passed=True,
            request_id=request.request_id,
            projection=projection,
            result_digest=digest(
                result_body
            ),
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "declared_capability_count": len(
                    DECLARED_CAPABILITIES
                ),
                "admitted_capability_count": len(
                    admitted
                ),
                "passed": True,
            },
            provenance=provenance,
        )

    except Exception as exc:
        failure_body = {
            "request_id": request.request_id,
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }

        failure = FailureRecord(
            failure_id=(
                f"veil-failure-"
                f"{digest(failure_body)[:20]}"
            ),
            code='quirk.nocturne.veil.runtime.failure',
            message=str(exc),
            stage="run",
            recoverable=True,
            details={
                "exception_type": type(exc).__name__,
            },
            provenance=provenance,
        )

        return VeilResult(
            operation="run",
            passed=False,
            request_id=request.request_id,
            failure=failure,
            result_digest=digest(
                {
                    "operation": "run",
                    "passed": False,
                    "request_id": request.request_id,
                    "failure": deterministic_projection(
                        failure
                    ),
                }
            ),
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": False,
            },
            provenance=provenance,
        )


def example_request() -> VeilRequest:
    generated_at = (
        "2026-08-01T00:00:00+00:00"
    )

    return VeilRequest(
        request_id='veil-example-request',
        purpose=AUTHORITATIVE_PURPOSE,
        operation="project",
        payload={
            "subject": 'quirk.nocturne.veil',
        },
        policy={
            "execution_mode": "plan",
            "allowed_capabilities": [],
            "fail_closed": True,
            "deterministic": True,
            "network_access": False,
            "filesystem_read": False,
            "filesystem_write": False,
            "subprocess_access": False,
            "secret_access": False,
        },
        authority=AuthorityState.OBSERVED,
        provenance={
            "sources": [],
            "transformations": [],
            "generated_by": 'veil-example',
            "generated_at": generated_at,
            "contract_version": "1.0.0",
        },
    )


def load_request(
    path: Path | None,
) -> VeilRequest:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8"
        )

    return VeilRequest.model_validate_json(
        raw
    )


def write_result(
    result: VeilResult,
    output: Path | None,
) -> None:
    rendered = json.dumps(
        result.model_dump(
            mode="json"
        ),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if output is None:
        print(
            rendered,
            end="",
        )
        return

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        rendered,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Circuit rotation, traffic mixing, timing obfuscation, and identity blending across the Tor network.'
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run"
    )

    run_parser.add_argument(
        "--input",
        type=Path,
    )

    run_parser.add_argument(
        "--output",
        type=Path,
    )

    example_parser = subparsers.add_parser(
        "example"
    )

    example_parser.add_argument(
        "--output",
        type=Path,
    )

    subparsers.add_parser(
        "schema"
    )

    args = parser.parse_args()

    if args.command == "run":
        result = run(
            load_request(
                args.input
            )
        )

        write_result(
            result,
            args.output,
        )

        return (
            0
            if result.passed
            else 1
        )

    if args.command == "example":
        request = example_request()

        rendered = json.dumps(
            request.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"

        if args.output is None:
            print(
                rendered,
                end="",
            )
        else:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            args.output.write_text(
                rendered,
                encoding="utf-8",
            )

        return 0

    if args.command == "schema":
        print(
            json.dumps(
                {
                    "request": (
                        VeilRequest
                        .model_json_schema()
                    ),
                    "result": (
                        VeilResult
                        .model_json_schema()
                    ),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
