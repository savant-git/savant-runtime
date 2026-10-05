#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.dryve.owner_binding import (
    DryveOwnerBinding,
    ExecutionLifecycleReceipt,
    ExecutionLifecycleRequest,
    bind_owners,
)


OWNER = "exile:opus"
MECHANICS_OWNER = "living:dryve"

SCHEMA = "savant://runtime/opus/dryve-lifecycle/1.0.0"


class OpusDryveLifecycleError(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def normalize_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        item = normalize_identifier(value)
        return (item,) if item else ()

    if isinstance(value, Mapping):
        values = value.keys()
    else:
        try:
            values = iter(value)
        except TypeError:
            values = (value,)

    return tuple(
        sorted(
            {
                normalized
                for normalized in (
                    normalize_identifier(item)
                    for item in values
                )
                if normalized
            }
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class OpusProviderExecution:
    execution_id: str
    execution: ExecutionLifecycleRequest
    provider_route: str | None
    model_route: str | None
    dependencies: tuple[str, ...]
    provider_owner: str = OWNER

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/opus/"
                "provider-execution/1.0.0"
            ),
            "owner": OWNER,
            "mechanics_owner": MECHANICS_OWNER,
            "execution_id": self.execution_id,
            "provider_route": self.provider_route,
            "model_route": self.model_route,
            "dependencies": list(
                self.dependencies
            ),
            "execution": (
                self.execution.projection()
            ),
            "provider_execution_owner": (
                self.provider_owner
            ),
            "provider_routing_owner": OWNER,
            "provider_credentials_owner": OWNER,
            "provider_access_authorized_by_dryve": False,
            "provider_selection_authorized_by_dryve": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload


class OpusDryveLifecycle:
    """
    Opus-owned provider execution lifecycle adapter.

    Opus retains provider/model selection, provider routing,
    credentials, inference execution, provider-specific retries,
    and fallback policy.

    Dryve supplies reusable execution-lifecycle mechanics only.
    """

    def __init__(
        self,
        *,
        dryve: DryveOwnerBinding | None = None,
    ) -> None:
        self.dryve = (
            dryve
            if dryve is not None
            else bind_owners()
        )

    def prepare(
        self,
        *,
        execution_id: str,
        operation: str,
        payload: Any,
        provider_route: str | None = None,
        model_route: str | None = None,
        dependencies: Sequence[str] = (),
        lineage: Any = None,
        provenance: Any = None,
        retry_policy: Any = None,
        timeout_policy: Any = None,
        metadata: Any = None,
    ) -> OpusProviderExecution:
        normalized_execution_id = (
            normalize_identifier(
                execution_id
            )
        )

        if not normalized_execution_id:
            raise OpusDryveLifecycleError(
                "execution_id is required"
            )

        normalized_dependencies = (
            normalize_sequence(
                dependencies
            )
        )

        normalized_provider_route = (
            normalize_identifier(
                provider_route
            )
        )

        normalized_model_route = (
            normalize_identifier(
                model_route
            )
        )

        request = (
            self.dryve.opus_request(
                execution_id=(
                    normalized_execution_id
                ),
                operation=operation,
                payload=payload,
                dependencies=(
                    normalized_dependencies
                ),
                lineage=lineage,
                provenance=provenance,
                retry_policy=retry_policy,
                timeout_policy=timeout_policy,
                metadata={
                    "provider_route": (
                        normalized_provider_route
                    ),
                    "model_route": (
                        normalized_model_route
                    ),
                    "opus_metadata": metadata,
                },
            )
        )

        return OpusProviderExecution(
            execution_id=(
                normalized_execution_id
            ),
            execution=request,
            provider_route=(
                normalized_provider_route
            ),
            model_route=(
                normalized_model_route
            ),
            dependencies=(
                normalized_dependencies
            ),
        )

    def lifecycle_receipt(
        self,
        execution: OpusProviderExecution,
        *,
        execution_state: str,
        attempt: int = 1,
        previous_execution_state: str | None = None,
        result: Any = None,
        error: Any = None,
    ) -> ExecutionLifecycleReceipt:
        return self.dryve.receipt(
            execution.execution,
            state=execution_state,
            attempt=attempt,
            previous_state=(
                previous_execution_state
            ),
            result=result,
            error=error,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mechanics_owner": MECHANICS_OWNER,
            "provider_execution_owner": OWNER,
            "provider_routing_owner": OWNER,
            "model_selection_owner": OWNER,
            "provider_credentials_owner": OWNER,
            "provider_retry_policy_owner": OWNER,
            "provider_fallback_policy_owner": OWNER,
            "execution_lifecycle_mechanics": (
                MECHANICS_OWNER
            ),
            "dryve_may_select_provider": False,
            "dryve_may_select_model": False,
            "dryve_may_access_provider_credentials": False,
            "dryve_may_execute_provider_calls": False,
            "dryve_may_define_provider_fallback": False,
            "dryve_may_define_provider_retry_policy": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)
        return payload


def lifecycle() -> OpusDryveLifecycle:
    return OpusDryveLifecycle()


def main() -> int:
    runtime = lifecycle()

    execution = runtime.prepare(
        execution_id="execution:test:opus:dryve",
        operation="text-inference",
        payload={
            "message": "focused-check",
        },
        provider_route="text-inference-route",
        model_route="default-model-route",
        retry_policy={
            "owner": OWNER,
            "maximum_attempts": 1,
        },
        provenance={
            "source": "focused-integration-check",
        },
    )

    receipt = runtime.lifecycle_receipt(
        execution,
        execution_state="ready",
    )

    output = {
        "status": runtime.status(),
        "execution": execution.projection(),
        "receipt": receipt.projection(),
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            output["status"][
                "provider_execution_owner"
            ]
            == OWNER
            and output["status"][
                "execution_lifecycle_mechanics"
            ]
            == MECHANICS_OWNER
            and output["status"][
                "dryve_may_execute_provider_calls"
            ]
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
