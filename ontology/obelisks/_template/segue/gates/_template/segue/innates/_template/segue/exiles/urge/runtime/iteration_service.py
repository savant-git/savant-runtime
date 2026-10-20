
from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from envoy_opus_binding import envoy_opus_binding
from iteration_controller import create, verify
from iteration_journal import iteration_journal
from iteration_projection import project, timeline
from iteration_scheduler import iteration_scheduler


class service_error(RuntimeError):
    pass


class iteration_service:
    def __init__(
        self,
        *,
        journal_directory: str | Path,
        providers: Sequence[Mapping[str, Any]],
    ) -> None:
        self.journal = iteration_journal(
            journal_directory
        )
        self.executor = envoy_opus_binding(
            providers
        )
        self.sessions: dict[
            str, iteration_scheduler
        ] = {}
        self.tasks: dict[
            str, asyncio.Task
        ] = {}
        self.failures: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def _scheduler(
        self,
        session_id: str,
    ) -> iteration_scheduler:
        scheduler = self.sessions.get(
            session_id
        )

        if scheduler is None:
            raise service_error(
                "session is not loaded"
            )

        return scheduler

    async def create_session(
        self,
        *,
        session_id: str,
        goal: str,
        iteration_limit: int,
        interval_seconds: float,
        settings: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._lock:
            if (
                session_id in self.sessions
                or self.journal.exists(session_id)
            ):
                raise service_error(
                    "session already exists"
                )

            session = create(
                session_id=session_id,
                goal=goal,
                iteration_limit=iteration_limit,
                interval_seconds=interval_seconds,
                settings=settings,
            )

            self.journal.save(session)

            self.sessions[session_id] = (
                iteration_scheduler(
                    session,
                    self.executor,
                )
            )

            return session

    async def restore(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        async with self._lock:
            if session_id in self.sessions:
                return await self.sessions[
                    session_id
                ].snapshot()

            session = self.journal.load(
                session_id
            )

            if session["state"] == "running":
                raise service_error(
                    "interrupted session requires "
                    "explicit recovery"
                )

            self.sessions[session_id] = (
                iteration_scheduler(
                    session,
                    self.executor,
                )
            )

            return session

    async def _persist(
        self,
        session: Mapping[str, Any],
    ) -> None:
        self.journal.save(
            verify(session)
        )

    async def _execute(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(
            session_id
        )

        try:
            result = await scheduler.run(
                on_update=self._persist
            )
            await self._persist(result)
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.failures[session_id] = (
                f"{type(exc).__name__}: {exc}"
            )
            await self._persist(
                await scheduler.snapshot()
            )
            raise

    def _finished(
        self,
        session_id: str,
        task: asyncio.Task,
    ) -> None:
        if task.cancelled():
            self.failures[session_id] = (
                "execution task cancelled"
            )
            return

        exception = task.exception()

        if exception is not None:
            self.failures[session_id] = (
                f"{type(exception).__name__}: "
                f"{exception}"
            )

    async def start(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(
            session_id
        )

        existing = self.tasks.get(
            session_id
        )

        if existing is not None and not existing.done():
            raise service_error(
                "session already executing"
            )

        state = await scheduler.start()
        await self._persist(state)

        task = asyncio.create_task(
            self._execute(session_id)
        )

        task.add_done_callback(
            lambda finished: self._finished(
                session_id, finished
            )
        )

        self.tasks[session_id] = task
        return state

    async def pause(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        state = await self._scheduler(
            session_id
        ).pause()

        await self._persist(state)
        return state

    async def resume(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        state = await self._scheduler(
            session_id
        ).resume()

        await self._persist(state)
        return state

    async def configure(
        self,
        session_id: str,
        settings: Mapping[str, Any],
    ) -> dict[str, Any]:
        state = await self._scheduler(
            session_id
        ).configure(settings)

        await self._persist(state)
        return state

    async def status(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        state = await self._scheduler(
            session_id
        ).snapshot()

        result = project(state)
        result["failure"] = self.failures.get(
            session_id
        )
        return result

    async def history(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        state = await self._scheduler(
            session_id
        ).snapshot()

        return timeline(state)

    async def wait(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        task = self.tasks.get(
            session_id
        )

        if task is None:
            raise service_error(
                "session has no execution task"
            )

        return await task
