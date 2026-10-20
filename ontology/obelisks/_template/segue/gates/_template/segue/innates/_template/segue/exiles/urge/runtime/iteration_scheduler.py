
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping
from typing import Any

from iteration_controller import (
    configure,
    next_iteration,
    record,
    transition,
    verify,
)


class execution_error(RuntimeError):
    pass


class iteration_scheduler:
    def __init__(
        self,
        session: Mapping[str, Any],
        executor: Callable[..., Any],
    ) -> None:
        if not callable(executor):
            raise TypeError("executor must be callable")

        self.session = verify(session)
        self.executor = executor
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()
        self._running_task: asyncio.Task | None = None

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return verify(self.session)

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(self.session, "start")
            self._wake.set()
            return verify(self.session)

    async def pause(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(self.session, "pause")
            self._wake.set()
            return verify(self.session)

    async def resume(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(self.session, "resume")
            self._wake.set()
            return verify(self.session)

    async def configure(
        self,
        settings: Mapping[str, Any],
    ) -> dict[str, Any]:
        async with self._lock:
            self.session = configure(self.session, settings)
            return verify(self.session)

    async def _wait_running(self) -> bool:
        while True:
            async with self._lock:
                state = self.session["state"]

                if state in ("completed", "failed"):
                    return False

                if state == "running":
                    return True

                if state != "paused":
                    raise execution_error(
                        "session must be started"
                    )

                self._wake.clear()

            await self._wake.wait()

    async def _execute(
        self,
        request: dict[str, Any],
    ) -> Mapping[str, Any]:
        if inspect.iscoroutinefunction(self.executor):
            outcome = await self.executor(request)
        else:
            outcome = await asyncio.to_thread(
                self.executor,
                request,
            )

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
                "execution evidence is required"
            )

        return outcome

    async def _notify(
        self,
        callback: Callable[..., Any] | None,
        state: dict[str, Any],
    ) -> None:
        if callback is None:
            return

        result = callback(state)

        if inspect.isawaitable(result):
            await result

    async def _wait_interval(
        self,
        seconds: float,
    ) -> None:
        remaining = seconds

        while remaining > 0:
            if not await self._wait_running():
                return

            async with self._lock:
                self._wake.clear()

            loop = asyncio.get_running_loop()
            started = loop.time()

            try:
                await asyncio.wait_for(
                    self._wake.wait(),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                return

            remaining = max(
                0.0,
                remaining - (loop.time() - started),
            )

    async def run(
        self,
        on_update: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        current = asyncio.current_task()

        async with self._lock:
            if self._running_task is not None:
                raise execution_error(
                    "scheduler already executing"
                )

            self._running_task = current

        try:
            while await self._wait_running():
                async with self._lock:
                    request = next_iteration(self.session)

                loop = asyncio.get_running_loop()
                started = loop.time()

                try:
                    outcome = await self._execute(request)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    async with self._lock:
                        if self.session["state"] in (
                            "running",
                            "paused",
                        ):
                            self.session = transition(
                                self.session,
                                "fail",
                            )

                        state = verify(self.session)

                    await self._notify(on_update, state)
                    raise

                async with self._lock:
                    paused = self.session["state"] == "paused"

                    if paused:
                        self.session = transition(
                            self.session,
                            "resume",
                        )

                    self.session = record(
                        self.session,
                        result=outcome["result"],
                        execution=outcome["execution"],
                    )

                    if (
                        paused
                        and self.session["state"] == "running"
                    ):
                        self.session = transition(
                            self.session,
                            "pause",
                        )

                    state = verify(self.session)

                await self._notify(on_update, state)

                if state["state"] == "completed":
                    return state

                elapsed = loop.time() - started

                await self._wait_interval(
                    max(
                        0.0,
                        request["interval_seconds"] - elapsed,
                    )
                )

            return await self.snapshot()

        finally:
            async with self._lock:
                self._running_task = None
