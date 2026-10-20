
from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from iteration_controller import create, verify
from iteration_journal import iteration_journal
from iteration_scheduler import iteration_scheduler
from opus_iteration_adapter import opus_iteration_adapter


class service_error(RuntimeError):
    pass


class iteration_service:
    def __init__(
        self,
        *,
        journal_directory: str | Path,
        providers: Sequence[Mapping[str, Any]],
        executor: Any = None,
    ) -> None:
        self.journal = iteration_journal(
            journal_directory
        )

        self.adapter = opus_iteration_adapter(
            providers,
            executor=executor,
        )

        self.sessions: dict[
            str, iteration_scheduler
        ] = {}

        self.tasks: dict[
            str, asyncio.Task
        ] = {}

    async def create_session(
        self,
        *,
        session_id: str,
        goal: str,
        iteration_limit: int,
        interval_seconds: float,
        settings: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if session_id in self.sessions:
            raise service_error(
                "session already exists"
            )

        if self.journal.exists(session_id):
            raise service_error(
                "persistent session already exists"
            )

        session = create(
            session_id=session_id,
            goal=goal,
            iteration_limit=iteration_limit,
            interval_seconds=interval_seconds,
            settings=settings,
        )

        self.journal.save(session)

        self.sessions[session_id] = iteration_scheduler(
            session,
            self.adapter,
        )

        return session

    async def restore(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        if session_id in self.sessions:
            return await self.sessions[
                session_id
            ].snapshot()

        session = self.journal.load(session_id)

        if session["state"] == "running":
            raise service_error(
                "interrupted running session requires "
                "explicit recovery"
            )

        self.sessions[session_id] = iteration_scheduler(
            session,
            self.adapter,
        )

        return session

    def _scheduler(
        self,
        session_id: str,
    ) -> iteration_scheduler:
        scheduler = self.sessions.get(session_id)

        if scheduler is None:
            raise service_error(
                "session is not loaded"
            )

        return scheduler

    async def _persist(
        self,
        session: Mapping[str, Any],
    ) -> None:
        self.journal.save(verify(session))

    async def start(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(session_id)

        if session_id in self.tasks:
            task = self.tasks[session_id]

            if not task.done():
                raise service_error(
                    "session already has an active task"
                )

        state = await scheduler.start()
        await self._persist(state)

        self.tasks[session_id] = asyncio.create_task(
            self._execute(session_id)
        )

        return state

    async def _execute(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(session_id)

        try:
            result = await scheduler.run(
                on_update=self._persist
            )
            await self._persist(result)
            return result
        except BaseException:
            await self._persist(
                await scheduler.snapshot()
            )
            raise

    async def pause(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(session_id)
        state = await scheduler.pause()
        await self._persist(state)
        return state

    async def resume(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        scheduler = self._scheduler(session_id)
        state = await scheduler.resume()
        await self._persist(state)
        return state

    async def status(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        return await self._scheduler(
            session_id
        ).snapshot()

    async def wait(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        task = self.tasks.get(session_id)

        if task is None:
            raise service_error(
                "session has no execution task"
            )

        return await task
