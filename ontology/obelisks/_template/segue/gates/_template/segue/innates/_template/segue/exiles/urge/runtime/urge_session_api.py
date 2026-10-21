
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping
from typing import Any


class session_api_error(ValueError):
    pass


class urge_session_api:
    def __init__(self, service: Any) -> None:
        self.service = service

    @staticmethod
    def _identity(value: Any) -> str:
        if not isinstance(value, str):
            raise session_api_error(
                "session identity must be a string"
            )

        try:
            identity = uuid.UUID(
                hex=value
            )
        except (ValueError, AttributeError) as exc:
            raise session_api_error(
                "invalid session identity"
            ) from exc

        if identity.hex != value:
            raise session_api_error(
                "noncanonical session identity"
            )

        return value

    @staticmethod
    def _settings(
        value: Any,
    ) -> dict[str, Any]:
        if value is None:
            return {}

        if not isinstance(value, Mapping):
            raise session_api_error(
                "settings must be an object"
            )

        settings = dict(value)

        method = settings.get(
            "method",
            "combine",
        )

        if method not in {
            "combine",
            "sequential",
        }:
            raise session_api_error(
                "unsupported opus method"
            )

        primary = settings.get(
            "primary_persona"
        )

        if primary is not None and (
            not isinstance(primary, str)
            or not primary.strip()
        ):
            raise session_api_error(
                "invalid primary persona"
            )

        supplemental = settings.get(
            "supplemental_personas",
            [],
        )

        if (
            not isinstance(supplemental, list)
            or not all(
                isinstance(item, str)
                and item.strip()
                for item in supplemental
            )
        ):
            raise session_api_error(
                "invalid supplemental personas"
            )

        return settings

    async def create(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise session_api_error(
                "request must be an object"
            )

        goal = request.get("goal")

        if (
            not isinstance(goal, str)
            or not goal.strip()
            or len(goal) > 16000
        ):
            raise session_api_error(
                "invalid goal"
            )

        limit = request.get(
            "iteration_limit",
            3,
        )

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 20
        ):
            raise session_api_error(
                "iteration limit must be 1 through 20"
            )

        interval = request.get(
            "interval_seconds",
            1.0,
        )

        if (
            isinstance(interval, bool)
            or not isinstance(interval, (int, float))
            or not 0 <= interval <= 3600
        ):
            raise session_api_error(
                "invalid iteration interval"
            )

        identity = uuid.uuid4().hex

        return await self.service.create_session(
            session_id=identity,
            goal=goal,
            iteration_limit=limit,
            interval_seconds=float(interval),
            settings=self._settings(
                request.get("settings")
            ),
        )

    async def _loaded(
        self,
        identity: str,
    ) -> str:
        identity = self._identity(
            identity
        )

        if identity not in self.service.sessions:
            await self.service.restore(
                identity
            )

        return identity

    async def status(
        self,
        identity: str,
    ) -> dict[str, Any]:
        identity = await self._loaded(
            identity
        )

        return await self.service.status(
            identity
        )

    async def history(
        self,
        identity: str,
    ) -> list[dict[str, Any]]:
        identity = await self._loaded(
            identity
        )

        return await self.service.history(
            identity
        )

    async def control(
        self,
        identity: str,
        action: str,
    ) -> dict[str, Any]:
        identity = await self._loaded(
            identity
        )

        if action not in {
            "start",
            "pause",
            "resume",
        }:
            raise session_api_error(
                "unsupported control action"
            )

        operation = getattr(
            self.service,
            action,
        )

        return await operation(
            identity
        )

    async def evidence(
        self,
        identity: str,
    ) -> dict[str, Any]:
        identity = await self._loaded(
            identity
        )

        status, history = await asyncio.gather(
            self.service.status(identity),
            self.service.history(identity),
        )

        return {
            "session_id": identity,
            "status": status,
            "history": history,
            "recorded_iterations": len(history),
            "source": "urge_iteration_service",
            "synthetic_results": False,
        }
