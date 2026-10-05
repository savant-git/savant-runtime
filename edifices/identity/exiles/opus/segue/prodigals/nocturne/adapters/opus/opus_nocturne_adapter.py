#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any


NOCTURNE_ROOT = Path(
    __file__
).resolve().parents[2]

CONTRACTS_ROOT = (
    NOCTURNE_ROOT
    / "contracts"
)

NOCTURNE_RUNTIME = (
    NOCTURNE_ROOT
    / "runtime"
    / "nocturne_runtime.py"
)

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from opus_attachment_contracts import (  # noqa: E402
    AttachmentDecision,
    AttachmentMode,
    AttachmentState,
    AuthorityBoundary,
    NocturneAttachmentRequest,
    NocturneAttachmentResult,
    OpusEnvelope,
    ProvenanceEnvelope,
)


ADAPTER_ID = "adapter.opus.nocturne"
ADAPTER_VERSION = "1.0.0"

VOLATILE_FIELDS = {
    "duration_seconds",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "wall_clock_seconds",
}


def canonical_bytes(
    value: Any,
) -> bytes:
    if hasattr(
        value,
        "model_dump",
    ):
        value = value.model_dump(
            mode="json",
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
    if hasattr(
        value,
        "model_dump",
    ):
        value = value.model_dump(
            mode="json",
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            key: deterministic_projection(
                child
            )
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(
        value,
        list,
    ):
        return [
            deterministic_projection(
                child
            )
            for child in value
        ]

    if isinstance(
        value,
        tuple,
    ):
        return tuple(
            deterministic_projection(
                child
            )
            for child in value
        )

    return value


def build_provenance(
    request: NocturneAttachmentRequest,
    transformations: tuple[str, ...],
) -> ProvenanceEnvelope:
    sources = list(
        request.provenance.sources
    )

    for source in (
        request.envelope.provenance.sources
    ):
        if source not in sources:
            sources.append(
                source
            )

    return ProvenanceEnvelope(
        sources=tuple(
            sources
        ),
        transformations=transformations,
        generated_by=(
            f"{ADAPTER_ID}@{ADAPTER_VERSION}"
        ),
        generated_at=(
            request.provenance.generated_at
        ),
    )


def load_nocturne_module() -> Any:
    if not NOCTURNE_RUNTIME.is_file():
        raise FileNotFoundError(
            f"Nocturne runtime missing: "
            f"{NOCTURNE_RUNTIME}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            "opus_attached_nocturne_runtime",
            NOCTURNE_RUNTIME,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise ImportError(
            "Unable to load Nocturne runtime."
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def evaluate_boundary(
    request: NocturneAttachmentRequest,
) -> tuple[
    bool,
    tuple[str, ...],
]:
    reasons: list[str] = []

    boundary = (
        request.authority_boundary
    )

    if (
        request.envelope.provider_request
        is not None
    ):
        reasons.append(
            "Nocturne attachment cannot receive "
            "an unresolved external provider request."
        )

    if (
        request.mode
        == AttachmentMode.EXECUTE
        and request.envelope.provider_result
        is None
        and request.envelope.provider_request
        is not None
    ):
        reasons.append(
            "Opus must complete provider orchestration "
            "before Nocturne receives provider-derived data."
        )

    forbidden_policy_flags = {
        "allow_nocturne_provider_selection",
        "allow_nocturne_secret_access",
        "allow_nocturne_registry_mutation",
        "allow_nocturne_policy_bypass",
    }

    for flag in forbidden_policy_flags:
        if request.envelope.policy.get(
            flag
        ):
            reasons.append(
                f"Forbidden Opus attachment policy: {flag}"
            )

    if (
        boundary.nocturne_may_select_external_providers
        or boundary.nocturne_may_read_opus_secrets
        or boundary.nocturne_may_mutate_opus_registry
        or boundary.nocturne_may_bypass_opus_policy
    ):
        reasons.append(
            "Authority boundary grants forbidden "
            "Opus powers to Nocturne."
        )

    return (
        not reasons,
        tuple(reasons),
    )


def decide(
    request: NocturneAttachmentRequest,
) -> AttachmentDecision:
    admitted, reasons = (
        evaluate_boundary(
            request
        )
    )

    boundary_value = (
        request.authority_boundary
        .model_dump(
            mode="json",
        )
    )

    request_value = (
        deterministic_projection(
            request
        )
    )

    decision_basis = {
        "attachment_id": (
            request.attachment_id
        ),
        "admitted": admitted,
        "reasons": reasons,
        "authority_boundary": (
            boundary_value
        ),
        "request_digest": digest(
            request_value
        ),
    }

    return AttachmentDecision(
        decision_id=(
            "opus-nocturne-decision-"
            + digest(
                decision_basis
            )[:20]
        ),
        state=(
            AttachmentState.ADMITTED
            if admitted
            else AttachmentState.REJECTED
        ),
        admitted=admitted,
        reasons=reasons,
        authority_boundary_digest=(
            digest(
                boundary_value
            )
        ),
        request_digest=(
            digest(
                request_value
            )
        ),
        provenance=build_provenance(
            request,
            (
                "validate_opus_envelope",
                "validate_authority_boundary",
                "validate_attachment_policy",
                "emit_attachment_decision",
            ),
        ),
    )


def attach(
    request: NocturneAttachmentRequest,
) -> NocturneAttachmentResult:
    started = time.perf_counter()

    decision = decide(
        request
    )

    if not decision.admitted:
        failure = {
            "code": (
                "opus.nocturne.attachment.denied"
            ),
            "message": (
                "Nocturne attachment was denied."
            ),
            "reasons": list(
                decision.reasons
            ),
        }

        body = {
            "attachment_id": (
                request.attachment_id
            ),
            "decision": (
                decision.model_dump(
                    mode="json",
                )
            ),
            "failure": failure,
        }

        return NocturneAttachmentResult(
            operation="attach",
            passed=False,
            attachment_id=(
                request.attachment_id
            ),
            decision=decision,
            failure=failure,
            result_digest=(
                digest(
                    deterministic_projection(
                        body
                    )
                )
            ),
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": False,
                "admitted": False,
            },
            provenance=build_provenance(
                request,
                (
                    "reject_attachment",
                    "preserve_denial_reasons",
                ),
            ),
        )

    try:
        module = (
            load_nocturne_module()
        )

        request_model = getattr(
            module,
            "NocturneRequest",
        )

        compose = getattr(
            module,
            "compose",
        )

        validated = (
            request_model.model_validate(
                request.nocturne_request
            )
        )

        result = compose(
            validated
        )

        result_value = (
            deterministic_projection(
                result
            )
        )

        passed = bool(
            result_value.get(
                "passed",
                False,
            )
        )

        completed_decision = (
            decision.model_copy(
                update={
                    "state": (
                        AttachmentState.COMPLETED
                        if passed
                        else AttachmentState.FAILED
                    )
                }
            )
        )

        body = {
            "attachment_id": (
                request.attachment_id
            ),
            "decision": (
                completed_decision
                .model_dump(
                    mode="json",
                )
            ),
            "nocturne_result": (
                result_value
            ),
        }

        return NocturneAttachmentResult(
            operation="attach",
            passed=passed,
            attachment_id=(
                request.attachment_id
            ),
            decision=(
                completed_decision
            ),
            nocturne_result=(
                result_value
            ),
            failure=(
                None
                if passed
                else {
                    "code": (
                        "opus.nocturne."
                        "composition.failed"
                    ),
                    "message": (
                        "Nocturne returned a "
                        "failed composition."
                    ),
                }
            ),
            result_digest=(
                digest(
                    deterministic_projection(
                        body
                    )
                )
            ),
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": passed,
                "admitted": True,
            },
            provenance=build_provenance(
                request,
                (
                    "admit_attachment",
                    "validate_nocturne_request",
                    "invoke_nocturne",
                    "strip_volatile_telemetry",
                    "emit_attachment_result",
                ),
            ),
        )

    except Exception as exc:
        failure = {
            "code": (
                "opus.nocturne.adapter.failure"
            ),
            "message": str(
                exc
            ),
            "exception_type": (
                type(
                    exc
                ).__name__
            ),
        }

        failed_decision = (
            decision.model_copy(
                update={
                    "state": (
                        AttachmentState.FAILED
                    )
                }
            )
        )

        body = {
            "attachment_id": (
                request.attachment_id
            ),
            "decision": (
                failed_decision
                .model_dump(
                    mode="json",
                )
            ),
            "failure": failure,
        }

        return NocturneAttachmentResult(
            operation="attach",
            passed=False,
            attachment_id=(
                request.attachment_id
            ),
            decision=failed_decision,
            failure=failure,
            result_digest=(
                digest(
                    deterministic_projection(
                        body
                    )
                )
            ),
            metrics={
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": False,
                "admitted": True,
            },
            provenance=build_provenance(
                request,
                (
                    "admit_attachment",
                    "capture_adapter_failure",
                ),
            ),
        )


def example_request() -> NocturneAttachmentRequest:
    generated_at = (
        "2026-07-31T00:00:00+00:00"
    )

    return NocturneAttachmentRequest(
        attachment_id=(
            "opus-nocturne-example"
        ),
        mode=AttachmentMode.PLAN,
        envelope=OpusEnvelope(
            request_id=(
                "opus-example-request"
            ),
            operation=(
                "delegate_local_analysis"
            ),
            payload={
                "subject": (
                    "Nocturne reference "
                    "composition"
                )
            },
            provider_request=None,
            provider_result=None,
            policy={
                "provider_orchestration_owner": (
                    "exile.opus"
                ),
                "attachment_target": (
                    "prodigal.nocturne"
                ),
            },
            provenance=(
                ProvenanceEnvelope(
                    sources=(),
                    transformations=(),
                    generated_by=(
                        "opus-example"
                    ),
                    generated_at=(
                        generated_at
                    ),
                )
            ),
        ),
        authority_boundary=(
            AuthorityBoundary()
        ),
        nocturne_request={
            "request_id": (
                "attached-nocturne-example"
            ),
            "purpose": (
                "Demonstrate authority-preserving "
                "Nocturne attachment to Opus."
            ),
            "policy": {
                "execution_mode": "plan",
                "enabled_quirks": [
                    "veil"
                ],
                "required_quirks": [
                    "veil"
                ],
                "allow_partial_results": True,
                "fail_closed": True,
                "preserve_intermediate_results": True,
                "maximum_stage_failures": 1,
            },
            "veil_request": {
                "request_id": (
                    "attached-veil-example"
                ),
                "destination": (
                    "example.invalid"
                ),
                "purpose": (
                    "Generate a deterministic "
                    "route plan."
                ),
                "execution_mode": "plan",
                "required_hops": 3,
                "maximum_latency_ms": None,
                "avoid_jurisdictions": [],
                "preferred_transports": [],
                "timing_jitter_ms": [
                    100,
                    900
                ],
                "rotation_interval_seconds": 600,
                "policy": {
                    "execution_mode": "plan",
                    "network_access": False,
                    "filesystem_read": False,
                    "filesystem_write": False,
                    "subprocess_access": False,
                    "secret_access": False,
                    "allowed_hosts": [],
                    "allowed_paths": [],
                    "allowed_commands": [],
                    "audit_required": True,
                },
                "provenance": {
                    "sources": [],
                    "transformations": [],
                    "generated_by": (
                        "opus-nocturne-example"
                    ),
                    "generated_at": (
                        generated_at
                    ),
                    "contract_version": (
                        "1.0.0"
                    ),
                },
            },
            "lantern_request": None,
            "scribe_request": None,
            "echo_request": None,
            "provenance": {
                "sources": [],
                "transformations": [],
                "generated_by": (
                    "opus-nocturne-example"
                ),
                "generated_at": (
                    generated_at
                ),
                "contract_version": (
                    "1.0.0"
                ),
            },
        },
        provenance=ProvenanceEnvelope(
            sources=(),
            transformations=(),
            generated_by=(
                "opus-nocturne-example"
            ),
            generated_at=(
                generated_at
            ),
        ),
    )


def load_request(
    path: Path | None,
) -> NocturneAttachmentRequest:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8",
        )

    return (
        NocturneAttachmentRequest
        .model_validate_json(
            raw
        )
    )


def write_result(
    result: NocturneAttachmentResult,
    output: Path | None,
) -> None:
    rendered = json.dumps(
        result.model_dump(
            mode="json",
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
        description=(
            "Authority-preserving Opus to "
            "Nocturne attachment adapter."
        )
    )

    subparsers = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    run_parser = (
        subparsers.add_parser(
            "run"
        )
    )

    run_parser.add_argument(
        "--input",
        type=Path,
    )

    run_parser.add_argument(
        "--output",
        type=Path,
    )

    example_parser = (
        subparsers.add_parser(
            "example"
        )
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
        result = attach(
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
                mode="json",
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
                    "attachment_request": (
                        NocturneAttachmentRequest
                        .model_json_schema()
                    ),
                    "attachment_result": (
                        NocturneAttachmentResult
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
