#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "living:dryve"
NICHE_OWNER = "exile:niche"
OPUS_OWNER = "exile:opus"

SCHEMA = "savant://runtime/dryve/owner-binding/1.0.0"


class DryveOwnerBindingError(RuntimeError):
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
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return text or None


def normalize_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(
        value,
        str,
    ):
        item = normalize_identifier(
            value
        )

        return (
            (item,)
            if item
            else ()
        )

    if isinstance(
        value,
        Mapping,
    ):
        values = value.keys()
    else:
        try:
            values = iter(
                value
            )
        except TypeError:
            values = (
                value,
            )

    result = {
        item
        for item in (
            normalize_identifier(
                value
            )
            for value in values
        )
        if item
    }

    return tuple(
        sorted(
            result
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionLifecycleRequest:
    execution_id: str
    owner: str
    operation: str
    payload: Any
    dependencies: tuple[str, ...]
    lineage: Any
    provenance: Any
    retry_policy: Any
    timeout_policy: Any
    metadata: Any

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/dryve/"
                "execution-request/1.0.0"
            ),
            "execution_id": (
                self.execution_id
            ),
            "owner": self.owner,
            "operation": (
                self.operation
            ),
            "payload": self.payload,
            "dependencies": list(
                self.dependencies
            ),
            "lineage": self.lineage,
            "provenance": (
                self.provenance
            ),
            "retry_policy": (
                self.retry_policy
            ),
            "timeout_policy": (
                self.timeout_policy
            ),
            "metadata": self.metadata,
            "execution_lifecycle_owner": (
                OWNER
            ),
            "task_governance_owner": (
                NICHE_OWNER
            ),
            "provider_execution_owner": (
                OPUS_OWNER
            ),
            "task_transition_authorized": (
                False
            ),
            "provider_access_authorized": (
                False
            ),
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionLifecycleReceipt:
    execution_id: str
    owner: str
    state: str
    attempt: int
    previous_state: str | None
    result: Any
    error: Any
    request_digest: str

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/dryve/"
                "execution-receipt/1.0.0"
            ),
            "execution_id": (
                self.execution_id
            ),
            "owner": self.owner,
            "state": self.state,
            "attempt": self.attempt,
            "previous_state": (
                self.previous_state
            ),
            "result": self.result,
            "error": self.error,
            "request_digest": (
                self.request_digest
            ),
            "execution_lifecycle_owner": (
                OWNER
            ),
            "task_transition_authorized": (
                False
            ),
            "provider_access_authorized": (
                False
            ),
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class DryveOwnerBinding:
    """
    Reusable execution-lifecycle mechanics.

    Dryve may model and report execution lifecycle state.

    Niche retains:
      - task authority
      - task scheduling
      - task priority
      - task dependency governance
      - task state transitions

    Opus retains:
      - provider/model selection
      - external AI execution
      - credentials
      - retries/fallback specific to providers
      - provider lineage
    """

    STATES = (
        "planned",
        "ready",
        "running",
        "waiting",
        "retrying",
        "succeeded",
        "failed",
        "cancelled",
        "expired",
    )

    OWNERS = (
        NICHE_OWNER,
        OPUS_OWNER,
    )

    def request(
        self,
        *,
        execution_id: str,
        owner: str,
        operation: str,
        payload: Any,
        dependencies: Sequence[
            str
        ] = (),
        lineage: Any = None,
        provenance: Any = None,
        retry_policy: Any = None,
        timeout_policy: Any = None,
        metadata: Any = None,
    ) -> ExecutionLifecycleRequest:
        normalized_execution_id = (
            normalize_identifier(
                execution_id
            )
        )

        normalized_owner = (
            normalize_identifier(
                owner
            )
        )

        normalized_operation = (
            normalize_identifier(
                operation
            )
        )

        if not normalized_execution_id:
            raise DryveOwnerBindingError(
                "execution_id is required"
            )

        if normalized_owner not in (
            self.OWNERS
        ):
            raise DryveOwnerBindingError(
                "owner must be exile:niche "
                "or exile:opus"
            )

        if not normalized_operation:
            raise DryveOwnerBindingError(
                "operation is required"
            )

        return ExecutionLifecycleRequest(
            execution_id=(
                normalized_execution_id
            ),
            owner=normalized_owner,
            operation=(
                normalized_operation
            ),
            payload=payload,
            dependencies=(
                normalize_sequence(
                    dependencies
                )
            ),
            lineage=lineage,
            provenance=provenance,
            retry_policy=retry_policy,
            timeout_policy=(
                timeout_policy
            ),
            metadata=metadata,
        )

    def receipt(
        self,
        request: ExecutionLifecycleRequest,
        *,
        state: str,
        attempt: int = 1,
        previous_state: str | None = None,
        result: Any = None,
        error: Any = None,
    ) -> ExecutionLifecycleReceipt:
        normalized_state = (
            normalize_identifier(
                state
            )
        )

        if normalized_state not in (
            self.STATES
        ):
            raise DryveOwnerBindingError(
                "invalid lifecycle state: "
                f"{state}"
            )

        if attempt < 1:
            raise DryveOwnerBindingError(
                "attempt must be >= 1"
            )

        if previous_state is not None:
            normalized_previous = (
                normalize_identifier(
                    previous_state
                )
            )

            if normalized_previous not in (
                self.STATES
            ):
                raise DryveOwnerBindingError(
                    "invalid previous state: "
                    f"{previous_state}"
                )
        else:
            normalized_previous = None

        return ExecutionLifecycleReceipt(
            execution_id=(
                request.execution_id
            ),
            owner=request.owner,
            state=normalized_state,
            attempt=attempt,
            previous_state=(
                normalized_previous
            ),
            result=result,
            error=error,
            request_digest=(
                request.projection()[
                    "digest"
                ]
            ),
        )

    def niche_request(
        self,
        *,
        execution_id: str,
        operation: str,
        payload: Any,
        dependencies: Sequence[
            str
        ] = (),
        lineage: Any = None,
        provenance: Any = None,
        metadata: Any = None,
    ) -> ExecutionLifecycleRequest:
        return self.request(
            execution_id=execution_id,
            owner=NICHE_OWNER,
            operation=operation,
            payload=payload,
            dependencies=dependencies,
            lineage=lineage,
            provenance=provenance,
            metadata=metadata,
        )

    def opus_request(
        self,
        *,
        execution_id: str,
        operation: str,
        payload: Any,
        dependencies: Sequence[
            str
        ] = (),
        lineage: Any = None,
        provenance: Any = None,
        retry_policy: Any = None,
        timeout_policy: Any = None,
        metadata: Any = None,
    ) -> ExecutionLifecycleRequest:
        return self.request(
            execution_id=execution_id,
            owner=OPUS_OWNER,
            operation=operation,
            payload=payload,
            dependencies=dependencies,
            lineage=lineage,
            provenance=provenance,
            retry_policy=retry_policy,
            timeout_policy=(
                timeout_policy
            ),
            metadata=metadata,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "governing_verb": "acts",
            "states": list(
                self.STATES
            ),
            "supported_owners": list(
                self.OWNERS
            ),
            "dryve_owns_execution_lifecycle": (
                True
            ),
            "dryve_owns_task_governance": (
                False
            ),
            "dryve_may_transition_tasks": (
                False
            ),
            "niche_owns_task_governance": (
                True
            ),
            "niche_owns_task_transitions": (
                True
            ),
            "dryve_owns_provider_execution": (
                False
            ),
            "dryve_may_access_providers": (
                False
            ),
            "dryve_may_access_secrets": (
                False
            ),
            "opus_owns_provider_execution": (
                True
            ),
            "opus_owns_provider_routing": (
                True
            ),
            "opus_owns_provider_credentials": (
                True
            ),
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def bind_owners(
) -> DryveOwnerBinding:
    return DryveOwnerBinding()


def main() -> int:
    binding = bind_owners()

    niche = binding.niche_request(
        execution_id=(
            "execution:test:niche"
        ),
        operation="task-work",
        payload={
            "task_id": "task:test",
        },
        provenance={
            "source": (
                "focused-self-check"
            ),
        },
    )

    opus = binding.opus_request(
        execution_id=(
            "execution:test:opus"
        ),
        operation=(
            "text-inference"
        ),
        payload={
            "route": (
                "text_inference_route"
            ),
        },
        retry_policy={
            "owner": OPUS_OWNER,
        },
        provenance={
            "source": (
                "focused-self-check"
            ),
        },
    )

    result = {
        "status": (
            binding.status()
        ),
        "niche": (
            binding.receipt(
                niche,
                state="ready",
            ).projection()
        ),
        "opus": (
            binding.receipt(
                opus,
                state="ready",
            ).projection()
        ),
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            result[
                "status"
            ][
                "dryve_owns_task_governance"
            ]
            is False
            and result[
                "status"
            ][
                "niche_owns_task_governance"
            ]
            is True
            and result[
                "status"
            ][
                "dryve_owns_provider_execution"
            ]
            is False
            and result[
                "status"
            ][
                "opus_owns_provider_execution"
            ]
            is True
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
