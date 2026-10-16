
from __future__ import annotations

from threading import Condition
from typing import Any, Callable


schema = "savant://runtime/urge/session-control/1.1.0"
owner = "exile:urge"


class session_control_error(RuntimeError):
    pass


class session_cancelled(BaseException):
    pass


class controller:
    def __init__(self) -> None:
        self._condition = Condition()
        self._status = "ready"
        self._revision = 0

    def _snapshot(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "status": self._status,
            "revision": self._revision,
            "terminal": self._status in (
                "completed",
                "cancelled",
                "failed",
            ),
        }

    def projection(self) -> dict[str, Any]:
        with self._condition:
            return self._snapshot()

    def start(self) -> dict[str, Any]:
        with self._condition:
            if self._status != "ready":
                raise session_control_error(
                    "execution is not ready"
                )

            self._status = "running"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def pause(self) -> dict[str, Any]:
        with self._condition:
            if self._status != "running":
                raise session_control_error(
                    "execution is not running"
                )

            self._status = "paused"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def resume(self) -> dict[str, Any]:
        with self._condition:
            if self._status != "paused":
                raise session_control_error(
                    "execution is not paused"
                )

            self._status = "running"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def cancel(self) -> dict[str, Any]:
        with self._condition:
            if self._status in (
                "completed",
                "cancelled",
                "failed",
            ):
                raise session_control_error(
                    "execution is already terminal"
                )

            self._status = "cancelled"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def complete(self) -> dict[str, Any]:
        with self._condition:
            if self._status != "running":
                raise session_control_error(
                    "execution cannot complete"
                )

            self._status = "completed"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def fail(self) -> dict[str, Any]:
        with self._condition:
            if self._status not in (
                "ready",
                "running",
                "paused",
            ):
                raise session_control_error(
                    "execution is already terminal"
                )

            self._status = "failed"
            self._revision += 1
            self._condition.notify_all()
            return self._snapshot()

    def checkpoint(self) -> None:
        with self._condition:
            while self._status == "paused":
                self._condition.wait()

            if self._status == "cancelled":
                raise session_cancelled(
                    "execution was cancelled"
                )

            if self._status != "running":
                raise session_control_error(
                    "execution is not running"
                )

    def guarded(
        self,
        callback: Callable[..., Any],
    ) -> Callable[..., Any]:
        if not callable(callback):
            raise TypeError(
                "callback must be callable"
            )

        def invoke(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            self.checkpoint()
            return callback(*args, **kwargs)

        return invoke


__all__ = [
    "controller",
    "owner",
    "schema",
    "session_cancelled",
    "session_control_error",
]
