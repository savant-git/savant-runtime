
from __future__ import annotations

from typing import Any, Callable, Mapping

from .iteration import engine, job
from .session_coordinator import (
    coordinator,
    session_coordinator_error,
)


schema = "savant://runtime/urge/session-api/1.0.0"
owner = "exile:urge"


class session_api_error(ValueError):
    pass


class session_api:
    def __init__(
        self,
        *,
        sessions: coordinator,
        resolve_work: Callable[
            [Mapping[str, Any]],
            tuple[job, engine],
        ],
    ) -> None:
        if not isinstance(sessions, coordinator):
            raise session_api_error(
                "sessions must be an urge coordinator"
            )

        if not callable(resolve_work):
            raise session_api_error(
                "resolve_work must be callable"
            )

        self._sessions = sessions
        self._resolve_work = resolve_work

    def dispatch(
        self,
        *,
        action: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(action, str):
            raise session_api_error(
                "action must be a string"
            )

        if not isinstance(payload, Mapping):
            raise session_api_error(
                "payload must be an object"
            )

        session_id = payload.get("session_id")

        if (
            not isinstance(session_id, str)
            or not session_id.strip()
            or session_id != session_id.strip()
        ):
            raise session_api_error(
                "session_id must be a canonical string"
            )

        try:
            if action == "start":
                work, runner = self._resolve_work(
                    payload
                )

                if not isinstance(work, job):
                    raise session_api_error(
                        "resolver did not return an urge job"
                    )

                if not isinstance(runner, engine):
                    raise session_api_error(
                        "resolver did not return an urge engine"
                    )

                state = self._sessions.start(
                    session_id=session_id,
                    work=work,
                    runner=runner,
                    initial_payload=payload.get(
                        "initial_payload"
                    ),
                )

            elif action == "snapshot":
                state = self._sessions.snapshot(
                    session_id
                )

            elif action == "pause":
                state = self._sessions.pause(
                    session_id
                )

            elif action == "resume":
                state = self._sessions.resume(
                    session_id
                )

            elif action == "cancel":
                state = self._sessions.cancel(
                    session_id
                )

            elif action == "release":
                self._sessions.release(
                    session_id
                )

                return {
                    "ok": True,
                    "schema": schema,
                    "owner": owner,
                    "action": action,
                    "session_id": session_id,
                    "released": True,
                }

            else:
                raise session_api_error(
                    "unsupported session action"
                )

        except session_coordinator_error as exc:
            raise session_api_error(
                str(exc)
            ) from exc

        return {
            "ok": True,
            "schema": schema,
            "owner": owner,
            "action": action,
            "session": state,
        }

    def safe_dispatch(
        self,
        *,
        action: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            return self.dispatch(
                action=action,
                payload=payload,
            )

        except (
            session_api_error,
            TypeError,
            ValueError,
        ) as exc:
            return {
                "ok": False,
                "schema": schema,
                "owner": owner,
                "action": action,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
