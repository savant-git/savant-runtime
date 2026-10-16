#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import json
from threading import RLock
from typing import Any, Callable


schema = (
    "savant://runtime/palaver/"
    "provider-lifecycle/1.0.0"
)

owner = "exile:palaver"
execution_owner = "exile:opus"

authority_effect = "none"


CancelHook = Callable[
    [],
    Any,
]


@dataclass
class _execution:
    request_id: str
    cancel_hook: CancelHook | None
    cancellation_requested: bool = False
    cancellation_propagated: bool = False
    completed: bool = False


class provider_lifecycle:
    def __init__(
        self,
    ) -> None:
        self._lock = RLock()

        self._executions: dict[
            str,
            _execution,
        ] = {}

    def register(
        self,
        *,
        request_id: str,
        cancel_hook: CancelHook | None = None,
    ) -> dict[str, Any]:
        request = str(
            request_id
            or ""
        ).strip()

        if not request:
            raise ValueError(
                "request_id is required"
            )

        if (
            cancel_hook is not None
            and not callable(
                cancel_hook
            )
        ):
            raise TypeError(
                "cancel_hook must be callable"
            )

        with self._lock:
            if request in self._executions:
                raise RuntimeError(
                    "provider execution already "
                    "registered"
                )

            self._executions[
                request
            ] = _execution(
                request_id=
                    request,
                cancel_hook=
                    cancel_hook,
            )

        return {
            "request_id":
                request,
            "registered":
                True,
            "provider_cancellation_available":
                cancel_hook
                is not None,
            "execution_owner":
                execution_owner,
            "authority_effect":
                authority_effect,
        }

    def attach_cancel_hook(
        self,
        *,
        request_id: str,
        cancel_hook: CancelHook,
    ) -> bool:
        if not callable(
            cancel_hook
        ):
            raise TypeError(
                "cancel_hook must be callable"
            )

        request = str(
            request_id
            or ""
        ).strip()

        with self._lock:
            execution = (
                self._executions.get(
                    request
                )
            )

            if execution is None:
                return False

            if execution.completed:
                return False

            execution.cancel_hook = (
                cancel_hook
            )

            should_cancel = (
                execution
                .cancellation_requested
                and not execution
                .cancellation_propagated
            )

        if should_cancel:
            self.cancel(
                request_id=
                    request
            )

        return True

    def cancel(
        self,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        request = str(
            request_id
            or ""
        ).strip()

        with self._lock:
            execution = (
                self._executions.get(
                    request
                )
            )

            if execution is None:
                return {
                    "request_id":
                        request,
                    "known":
                        False,
                    "cancellation_requested":
                        True,
                    "cancellation_propagated":
                        False,
                    "provider_cancellation_available":
                        False,
                    "authority_effect":
                        authority_effect,
                }

            execution.cancellation_requested = (
                True
            )

            hook = (
                execution.cancel_hook
            )

            if (
                hook is None
                or execution.completed
                or execution.cancellation_propagated
            ):
                return {
                    "request_id":
                        request,
                    "known":
                        True,
                    "cancellation_requested":
                        True,
                    "cancellation_propagated":
                        execution
                        .cancellation_propagated,
                    "provider_cancellation_available":
                        hook is not None,
                    "authority_effect":
                        authority_effect,
                }

            execution.cancellation_propagated = (
                True
            )

        try:
            hook()

        except Exception:
            with self._lock:
                current = (
                    self._executions.get(
                        request
                    )
                )

                if current is not None:
                    current.cancellation_propagated = (
                        False
                    )

            raise

        return {
            "request_id":
                request,
            "known":
                True,
            "cancellation_requested":
                True,
            "cancellation_propagated":
                True,
            "provider_cancellation_available":
                True,
            "execution_owner":
                execution_owner,
            "authority_effect":
                authority_effect,
        }

    def complete(
        self,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        request = str(
            request_id
            or ""
        ).strip()

        with self._lock:
            execution = (
                self._executions.pop(
                    request,
                    None,
                )
            )

        if execution is None:
            return {
                "request_id":
                    request,
                "known":
                    False,
                "completed":
                    False,
                "authority_effect":
                    authority_effect,
            }

        execution.completed = True

        return {
            "request_id":
                request,
            "known":
                True,
            "completed":
                True,
            "cancellation_requested":
                execution
                .cancellation_requested,
            "cancellation_propagated":
                execution
                .cancellation_propagated,
            "provider_cancellation_available":
                execution.cancel_hook
                is not None,
            "authority_effect":
                authority_effect,
        }

    def status(
        self,
    ) -> dict[str, Any]:
        with self._lock:
            active = tuple(
                sorted(
                    self._executions
                )
            )

            cancellation_capable = sum(
                1
                for execution
                in self._executions.values()
                if execution.cancel_hook
                is not None
            )

        return {
            "schema":
                schema,
            "owner":
                owner,
            "execution_owner":
                execution_owner,
            "active_count":
                len(
                    active
                ),
            "active_request_ids":
                list(
                    active
                ),
            "provider_cancellation_capable_count":
                cancellation_capable,
            "synthetic_provider_cancellation":
                False,
            "authority_effect":
                authority_effect,
        }


lifecycle = provider_lifecycle()


def selftest() -> dict[str, Any]:
    observed: list[str] = []

    lifecycle.register(
        request_id=
            "request-test",
        cancel_hook=lambda: (
            observed.append(
                "cancelled"
            )
        ),
    )

    cancellation = (
        lifecycle.cancel(
            request_id=
                "request-test"
        )
    )

    completion = (
        lifecycle.complete(
            request_id=
                "request-test"
        )
    )

    if observed != [
        "cancelled"
    ]:
        raise RuntimeError(
            "provider cancellation hook "
            "was not propagated"
        )

    if not cancellation[
        "cancellation_propagated"
    ]:
        raise RuntimeError(
            "cancellation propagation "
            "was not recorded"
        )

    if not completion[
        "completed"
    ]:
        raise RuntimeError(
            "provider lifecycle did "
            "not complete"
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "provider_cancellation_hook":
            True,
        "synthetic_provider_cancellation":
            False,
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
