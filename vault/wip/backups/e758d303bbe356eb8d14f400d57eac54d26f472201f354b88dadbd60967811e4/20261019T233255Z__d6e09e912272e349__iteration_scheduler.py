
from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from iteration_controller import (
    next_iteration,
    record,
    transition,
    verify,
)

executor_type = Callable[
    [dict[str, Any]],
    Mapping[str, Any] | Awaitable[Mapping[str, Any]],
]


class execution_error(RuntimeError):
    pass


class iteration_scheduler:
    def __init__(
        self,
        session: Mapping[str, Any],
        executor: executor_type,
    ) -> None:
        if not callable(executor):
            raise TypeError("executor must be callable")

        self.session = verify(session)
        self.executor = executor
        self._lock = asyncio.Lock()
        self._resume = asyncio.Event()
        self._stop = False

        if self.session["state"] == "running":
            self._resume.set()

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            if self.session["state"] != "ready":
                raise execution_error("session is not ready")

            self.session = transition(self.session, "start")
            self._resume.set()
            return dict(self.session)

    async def pause(self) -> dict[str, Any]:
        async with self._lock:
            if self.session["state"] != "running":
                raise execution_error("session is not running")

            self.session = transition(self.session, "pause")
            self._resume.clear()
            return dict(self.session)

    async def resume(self) -> dict[str, Any]:
        async with self._lock:
            if self.session["state"] != "paused":
                raise execution_error("session is not paused")

            self.session = transition(self.session, "resume")
            self._resume.set()
            return dict(self.session)

    async def stop(self) -> None:
        async with self._lock:
            self._stop = True
            self._resume.set()

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self.session)

    async def run(
        self,
        on_update: Callable[
            [dict[str, Any]], Any
        ] | None = None,
    ) -> dict[str, Any]:
        while True:
            await self._resume.wait()

            async with self._lock:
                if self._stop:
                    return dict(self.session)

                state = self.session["state"]

                if state in {"completed", "failed"}:
                    return dict(self.session)

                if state == "paused":
                    self._resume.clear()
                    continue

                if state != "running":
                    raise execution_error(
                        "session must be started before execution"
                    )

                request = next_iteration(self.session)

            started = time.monotonic()

            try:
                outcome = self.executor(request)

                if inspect.isawaitable(outcome):
                    outcome = await outcome

                if not isinstance(outcome, Mapping):
                    raise execution_error(
                        "executor must return a mapping"
                    )

                if "result" not in outcome:
                    raise execution_error(
                        "executor returned no result"
                    )

                evidence = outcome.get("execution")

                if not isinstance(evidence, Mapping) or not evidence:
                    raise execution_error(
                        "executor returned no execution evidence"
                    )

            except Exception:
                async with self._lock:
                    if self.session["state"] in {
                        "running",
                        "paused",
                    }:
                        self.session = transition(
                            self.session,
                            "fail",
                        )
                raise

            async with self._lock:
                self.session = record(
                    self.session,
                    result=outcome["result"],
                    execution=evidence,
                )
                snapshot = dict(self.session)
                finished = snapshot["state"] == "completed"

            if on_update is not None:
                response = on_update(snapshot)

                if inspect.isawaitable(response):
                    await response

            if finished:
                return snapshot

            elapsed = time.monotonic() - started
            remaining = max(
                0.0,
                request["interval_seconds"] - elapsed,
            )

            while remaining > 0:
                async with self._lock:
                    if self._stop:
                        return dict(self.session)

                    paused = self.session["state"] == "paused"

                if paused:
                    await self._resume.wait()
                    continue

                step = min(remaining, 0.1)
                before = time.monotonic()
                await asyncio.sleep(step)
                remaining -= time.monotonic() - before
