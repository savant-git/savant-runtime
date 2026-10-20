
from __future__ import annotations

import asyncio
import inspect
import time
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
        self._stop = False
        self._running_task: asyncio.Task | None = None

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return verify(self.session)

    async def start(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(
                self.session, "start"
            )
            self._wake.set()
            return verify(self.session)

    async def pause(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(
                self.session, "pause"
            )
            self._wake.set()
            return verify(self.session)

    async def resume(self) -> dict[str, Any]:
        async with self._lock:
            self.session = transition(
                self.session, "resume"
            )
            self._wake.set()
            return verify(self.session)

    async def configure(
        self,
        settings: Mapping[str, Any],
    ) -> dict[str, Any]:
        async with self._lock:
            self.session = configure(
                self.session, settings
            )
            return verify(self.session)

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            self._stop = True
            self._wake.set()
            return verify(self.session)

    async def _notify(
        self,
        callback: Callable[..., Any] | None,
        snapshot: dict[str, Any],
    ) -> None:
        if callback is None:
            return

        value = callback(snapshot)

        if inspect.isawaitable(value):
            await value

    async def _execute(
        self,
        request: dict[str, Any],
    ) -> Mapping[str, Any]:
        if inspect.iscoroutinefunction(self.executor):
            result = await self.executor(request)
        else:
            result = await asyncio.to_thread(
                self.executor, request
            )

            if inspect.isawaitable(result):
                result = await result

        if not isinstance(result, Mapping):
            raise execution_error(
                "executor must return a mapping"
            )

        if "result" not in result:
            raise execution_error(
                "executor returned no result"
            )

        evidence = result.get("execution")

        if (
            not isinstance(evidence, Mapping)
            or not evidence
        ):
            raise execution_error(
                "executor returned no execution evidence"
            )

        return result

    async def _wait_until_running(self) -> bool:
        while True:
            async with self._lock:
                if self._stop:
                    return False

                state = self.session["state"]

                if state in {"completed", "failed"}:
                    return False

                if state == "running":
                    return True

                if state != "paused":
                    raise execution_error(
                        "session must be started"
                    )

                self._wake.clear()

            await self._wake.wait()

    async def _interval(
        self,
        seconds: float,
    ) -> bool:
        remaining = seconds

        while remaining > 0:
            if not await self._wait_until_running():
                return False

            async with self._lock:
                self._wake.clear()

            started = time.monotonic()

            try:
                await asyncio.wait_for(
                    self._wake.wait(),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                return True

            elapsed = time.monotonic() - started

            async with self._lock:
                if self._stop:
                    return False

                if self.session["state"] == "paused":
                    remaining = max(
                        0.0, remaining - elapsed
                    )
                elif self.session["state"] == "running":
                    remaining = max(
                        0.0, remaining - elapsed
                    )
                else:
                    return False

        return True

    async def run(
        self,
        on_update: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        current = asyncio.current_task()

        async with self._lock:
            if (
                self._running_task is not None
                and not self._running_task.done()
            ):
                raise execution_error(
                    "scheduler is already executing"
                )

            self._running_task = current

        try:
            while await self._wait_until_running():
                async with self._lock:
                    request = next_iteration(
                        self.session
                    )

                started = time.monotonic()

                try:
                    outcome = await self._execute(
                        request
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    async with self._lock:
                        if self.session["state"] in {
                            "running", "paused"
                        }:
                            self.session = transition(
                                self.session, "fail"
                            )

                        snapshot = verify(
                            self.session
                        )

                    await self._notify(
                        on_update, snapshot
                    )
                    raise

                async with self._lock:
                    if self._stop:
                        return verify(self.session)

                    if self.session["state"] == "paused":
                        self.session = transition(
                            self.session, "resume"
                        )
                        self.session = record(
                            self.session,
                            result=outcome["result"],
                            execution=outcome["execution"],
                        )

                        if self.session["state"] == "running":
                            self.session = transition(
                                self.session, "pause"
                            )
                    else:
                        self.session = record(
                            self.session,
                            result=outcome["result"],
                            execution=outcome["execution"],
                        )

                    snapshot = verify(
                        self.session
                    )

                await self._notify(
                    on_update, snapshot
                )

                if snapshot["state"] == "completed":
                    return snapshot

                elapsed = time.monotonic() - started
                remaining = max(
                    0.0,
                    request["interval_seconds"] - elapsed,
                )

                if not await self._interval(remaining):
                    break

            return await self.snapshot()

        finally:
            async with self._lock:
                if self._running_task is current:
                    self._running_task = None
