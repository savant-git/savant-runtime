from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime.straub.datrix import StraubDatrix

try:
    from .conversation_transport import (
        conversation_event,
        conversation_event_buffer,
        project_event,
        session_id,
    )
except ImportError:
    from conversation_transport import (
        conversation_event,
        conversation_event_buffer,
        project_event,
        session_id,
    )

schema = "savant://runtime/palaver/session-store/1.1.0"
owner = "exile:palaver"
schema_version = 2

default_datrix = Path(
    "/root/savant-runtime/runtime/state/palaver/sessions.datrix"
)
default_database = default_datrix

SESSION_REVISION_KIND = "palaver.session.revision"
EVENT_KIND = "palaver.session.event"
RECEIPT_KIND = "palaver.session.receipt"


class session_store_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _now() -> float:
    return time.time()


class session_store:
    def __init__(
        self,
        path: Path | str = default_database,
    ) -> None:
        self.path = Path(path).resolve()
        self.database = self.path
        self.database_path = self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        StraubDatrix.open(self.path)

    def _open_datrix(self) -> StraubDatrix:
        return StraubDatrix.open(self.path)

    @staticmethod
    def _records(
        datrix: StraubDatrix,
        kind: str,
    ) -> tuple[dict[str, Any], ...]:
        projection = datrix.query().search(
            {
                "kinds": [kind],
                "include_invalid": False,
            }
        )
        return tuple(
            dict(record)
            for record in projection.get("results", ())
            if isinstance(record, Mapping)
        )

    @staticmethod
    def _payload(record: Mapping[str, Any]) -> dict[str, Any]:
        value = record.get("payload", {})
        if not isinstance(value, Mapping):
            raise session_store_error(
                "stored Palaver datrix payload is invalid"
            )
        return dict(value)

    def close(self) -> None:
        return None

    def _session_revisions(
        self,
        identifier: str,
        datrix: StraubDatrix,
    ) -> list[dict[str, Any]]:
        revisions: list[dict[str, Any]] = []
        for record in self._records(
            datrix,
            SESSION_REVISION_KIND,
        ):
            payload = self._payload(record)
            if payload.get("session_id") == identifier:
                revisions.append(payload)
        revisions.sort(
            key=lambda item: (
                int(item.get("revision", 0)),
                str(item.get("revision_id", "")),
            )
        )
        return revisions

    def _current_session(
        self,
        identifier: str,
        datrix: StraubDatrix,
    ) -> dict[str, Any] | None:
        revisions = self._session_revisions(
            identifier,
            datrix,
        )
        if not revisions:
            return None
        record = revisions[-1].get("session")
        if not isinstance(record, Mapping):
            raise session_store_error(
                "stored Palaver session projection is invalid"
            )
        return dict(record)

    def _append_session_revision(
        self,
        datrix: StraubDatrix,
        session_record: Mapping[str, Any],
    ) -> dict[str, Any]:
        identifier = session_id(
            session_record.get("session_id")
        )
        revisions = self._session_revisions(
            identifier,
            datrix,
        )
        revision = (
            int(revisions[-1].get("revision", 0)) + 1
            if revisions
            else 1
        )
        projected = dict(session_record)
        semantic = digest(
            {
                "session_id": identifier,
                "state": projected["state"],
                "task_binding": projected["task_binding"],
                "context_sources": projected["context_sources"],
                "workspace_state": projected["workspace_state"],
                "usage_summary": projected["usage_summary"],
                "replay_metadata": projected["replay_metadata"],
            }
        )
        projected["semantic_digest"] = semantic
        identity = {
            "session_id": identifier,
            "revision": revision,
            "session": projected,
        }
        revision_digest = digest(identity)
        revision_id = (
            "palaver-session-revision:"
            + revision_digest[:32]
        )
        datrix.registry.substantiate(
            {
                "id": revision_id,
                "kind": SESSION_REVISION_KIND,
                "status": str(projected["state"]),
                "authority": {
                    "owner": owner,
                    "authoritative": False,
                },
                "payload": {
                    "session_id": identifier,
                    "revision": revision,
                    "revision_id": revision_id,
                    "session": projected,
                },
                "metadata": {
                    "profile": "chronicle",
                    "logical_session_id": identifier,
                    "revision": revision,
                },
                "dependencies": [],
                "relationships": [],
                "provenance": {
                    "owner": owner,
                    "source": "palaver",
                },
                "lineage": {
                    "logical_session_id": identifier,
                    "revision": revision,
                    "previous_revision_id": (
                        revisions[-1].get("revision_id")
                        if revisions
                        else None
                    ),
                },
                "extensions": {
                    "palaver_schema": schema,
                },
            }
        )
        return projected

    def ensure_session(
        self,
        session: Any,
        *,
        state: str = "active",
    ) -> str:
        identifier = session_id(session)
        with self._lock:
            datrix = self._open_datrix()
            if self._current_session(identifier, datrix) is not None:
                return identifier
            now = _now()
            self._append_session_revision(
                datrix,
                {
                    "session_id": identifier,
                    "created_at": now,
                    "updated_at": now,
                    "state": state,
                    "task_binding": None,
                    "context_sources": [],
                    "workspace_state": {},
                    "usage_summary": {},
                    "replay_metadata": {},
                },
            )
            datrix.checkpoint()
        return identifier

    def load_session(
        self,
        session: Any,
    ) -> dict[str, Any] | None:
        identifier = session_id(session)
        with self._lock:
            return self._current_session(
                identifier,
                self._open_datrix(),
            )

    def update_session(
        self,
        session: Any,
        *,
        state: Any = None,
        task_binding: Any = None,
        context_sources: Any = None,
        workspace_state: Any = None,
        usage_summary: Any = None,
        replay_metadata: Any = None,
        replace_task_binding: bool = False,
    ) -> dict[str, Any]:
        identifier = self.ensure_session(session)
        with self._lock:
            datrix = self._open_datrix()
            current = self._current_session(
                identifier,
                datrix,
            )
            if current is None:
                raise session_store_error(
                    "Palaver session does not exist"
                )
            updated = dict(current)
            if state is not None:
                updated["state"] = str(state).strip()
            if not updated["state"]:
                raise session_store_error(
                    "session state cannot be empty"
                )
            if replace_task_binding:
                updated["task_binding"] = task_binding
            if context_sources is not None:
                updated["context_sources"] = context_sources
            if workspace_state is not None:
                updated["workspace_state"] = workspace_state
            if usage_summary is not None:
                updated["usage_summary"] = usage_summary
            if replay_metadata is not None:
                updated["replay_metadata"] = replay_metadata
            updated["updated_at"] = _now()
            projected = self._append_session_revision(
                datrix,
                updated,
            )
            datrix.checkpoint()
            return projected

    def _event_payloads(
        self,
        identifier: str,
        datrix: StraubDatrix,
    ) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for record in self._records(datrix, EVENT_KIND):
            payload = self._payload(record)
            if payload.get("session_id") == identifier:
                values.append(payload)
        values.sort(
            key=lambda item: int(item.get("sequence", 0))
        )
        return values

    def persist_event(
        self,
        event: conversation_event,
    ) -> bool:
        identifier = self.ensure_session(event.session_id)
        with self._lock:
            datrix = self._open_datrix()
            for stored in self._event_payloads(
                identifier,
                datrix,
            ):
                if int(stored.get("sequence", 0)) == event.sequence:
                    if stored.get("semantic_digest") != event.semantic_digest:
                        raise session_store_error(
                            "conversation sequence conflict"
                        )
                    return False
                if stored.get("event_id") == event.event_id:
                    if stored.get("semantic_digest") != event.semantic_digest:
                        raise session_store_error(
                            "conversation event identity conflict"
                        )
                    return False
            payload = {
                "session_id": identifier,
                "sequence": event.sequence,
                "request_id": event.request_id,
                "event_type": event.type,
                "payload": event.payload,
                "observed_at": event.observed_at,
                "event_id": event.event_id,
                "semantic_digest": event.semantic_digest,
                "terminal": bool(event.terminal),
                "authority_effect": event.authority_effect,
            }
            datrix.registry.substantiate(
                {
                    "id": "palaver-session-event:" + event.semantic_digest,
                    "kind": EVENT_KIND,
                    "status": "active",
                    "authority": {
                        "owner": owner,
                        "authoritative": False,
                    },
                    "payload": payload,
                    "metadata": {
                        "profile": "chronicle",
                        "session_id": identifier,
                        "sequence": event.sequence,
                        "request_id": event.request_id,
                    },
                    "dependencies": [identifier],
                    "relationships": [],
                    "provenance": {
                        "owner": owner,
                        "source": "palaver",
                    },
                    "lineage": {
                        "session_id": identifier,
                        "sequence": event.sequence,
                    },
                    "extensions": {
                        "palaver_schema": schema,
                    },
                }
            )
            current = self._current_session(identifier, datrix)
            if current is None:
                raise session_store_error(
                    "Palaver session does not exist"
                )
            current["updated_at"] = _now()
            self._append_session_revision(datrix, current)
            datrix.checkpoint()
            return True

    def persist_events(
        self,
        events: Iterable[conversation_event],
    ) -> int:
        count = 0
        for event in events:
            if self.persist_event(event):
                count += 1
        return count

    def load_events(
        self,
        session: Any,
        *,
        after_sequence: int = 0,
        limit: int | None = 4096,
        tail: bool = False,
    ) -> tuple[conversation_event, ...]:
        identifier = session_id(session)
        if (
            not isinstance(after_sequence, int)
            or isinstance(after_sequence, bool)
            or after_sequence < 0
        ):
            raise session_store_error(
                "after_sequence must be a nonnegative integer"
            )
        effective_limit = 4096 if limit is None else limit
        if (
            not isinstance(effective_limit, int)
            or isinstance(effective_limit, bool)
            or not 1 <= effective_limit <= 65536
        ):
            raise session_store_error(
                "event limit must be between 1 and 65536"
            )
        with self._lock:
            payloads = self._event_payloads(
                identifier,
                self._open_datrix(),
            )
        payloads = [
            item
            for item in payloads
            if int(item.get("sequence", 0)) > after_sequence
        ]
        if tail:
            payloads = payloads[-effective_limit:]
        else:
            payloads = payloads[:effective_limit]
        events: list[conversation_event] = []
        for stored in payloads:
            rebuilt = project_event(
                session=stored["session_id"],
                request=stored["request_id"],
                sequence=int(stored["sequence"]),
                kind=stored["event_type"],
                payload=stored["payload"],
                observed_at=stored["observed_at"],
            )
            if (
                rebuilt.event_id != stored["event_id"]
                or rebuilt.semantic_digest != stored["semantic_digest"]
                or bool(rebuilt.terminal) != bool(stored["terminal"])
                or rebuilt.authority_effect
                != (stored.get("authority_effect") or "none")
            ):
                raise session_store_error(
                    "stored conversation event failed deterministic replay"
                )
            events.append(rebuilt)
        return tuple(events)

    def event_window(
        self,
        session: Any,
        *,
        capacity: int,
    ) -> dict[str, int | str]:
        identifier = session_id(session)
        if capacity < 1:
            raise session_store_error(
                "capacity must be positive"
            )
        with self._lock:
            payloads = self._event_payloads(
                identifier,
                self._open_datrix(),
            )
        total = len(payloads)
        earliest = (
            int(payloads[0]["sequence"])
            if payloads
            else 0
        )
        latest = (
            int(payloads[-1]["sequence"])
            if payloads
            else 0
        )
        retained_count = min(total, capacity)
        retained_from = (
            max(earliest, latest - retained_count + 1)
            if retained_count
            else 0
        )
        return {
            "session_id": identifier,
            "total_events": total,
            "earliest_sequence": earliest,
            "latest_sequence": latest,
            "retained_from_sequence": retained_from,
            "retained_event_count": retained_count,
        }

    def restore_buffer(
        self,
        session: Any,
        *,
        maximum_events: int = 2048,
    ) -> conversation_event_buffer:
        identifier = session_id(session)
        buffer = conversation_event_buffer(
            session=identifier,
            maximum_events=maximum_events,
        )
        for event in self.load_events(
            identifier,
            limit=maximum_events,
            tail=True,
        ):
            recreated = buffer.publish(
                request=event.request_id,
                kind=event.type,
                payload=event.payload,
                dedupe_key=None,
            )
            if (
                recreated.sequence != event.sequence
                or recreated.semantic_digest != event.semantic_digest
            ):
                raise session_store_error(
                    "conversation buffer replay diverged from stored history"
                )
        return buffer

    def _receipt_payloads(
        self,
        identifier: str,
        datrix: StraubDatrix,
    ) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for record in self._records(datrix, RECEIPT_KIND):
            payload = self._payload(record)
            if payload.get("session_id") == identifier:
                values.append(payload)
        values.sort(
            key=lambda item: (
                float(item.get("created_at", 0.0)),
                str(item.get("receipt_id", "")),
            )
        )
        return values

    def record_receipt(
        self,
        *,
        receipt_id: Any,
        session: Any,
        request: Any = None,
        receipt_type: Any,
        receipt_owner: Any,
        payload: Any,
        authority_effect: str = "none",
    ) -> bool:
        identifier = self.ensure_session(session)
        normalized_receipt = str(receipt_id or "").strip()
        normalized_type = str(receipt_type or "").strip()
        normalized_owner = str(receipt_owner or "").strip()
        if not normalized_receipt:
            raise session_store_error("receipt_id is required")
        if not normalized_type:
            raise session_store_error("receipt_type is required")
        if not normalized_owner:
            raise session_store_error("receipt owner is required")
        semantic = digest(
            {
                "receipt_id": normalized_receipt,
                "session_id": identifier,
                "request_id": request,
                "receipt_type": normalized_type,
                "owner": normalized_owner,
                "payload": payload,
                "authority_effect": authority_effect,
            }
        )
        with self._lock:
            datrix = self._open_datrix()
            for stored in self._records(datrix, RECEIPT_KIND):
                value = self._payload(stored)
                if value.get("receipt_id") != normalized_receipt:
                    continue
                if value.get("semantic_digest") != semantic:
                    raise session_store_error(
                        "receipt identity conflict"
                    )
                return False
            record = {
                "receipt_id": normalized_receipt,
                "session_id": identifier,
                "request_id": (
                    str(request)
                    if request is not None
                    else None
                ),
                "receipt_type": normalized_type,
                "owner": normalized_owner,
                "payload": payload,
                "created_at": _now(),
                "semantic_digest": semantic,
                "authority_effect": authority_effect,
            }
            datrix.registry.substantiate(
                {
                    "id": "palaver-session-receipt:" + semantic,
                    "kind": RECEIPT_KIND,
                    "status": "active",
                    "authority": {
                        "owner": owner,
                        "authoritative": False,
                    },
                    "payload": record,
                    "metadata": {
                        "profile": "chronicle",
                        "session_id": identifier,
                        "receipt_id": normalized_receipt,
                    },
                    "dependencies": [identifier],
                    "relationships": [],
                    "provenance": {
                        "owner": owner,
                        "source": "palaver",
                    },
                    "lineage": {
                        "session_id": identifier,
                        "receipt_id": normalized_receipt,
                    },
                    "extensions": {
                        "palaver_schema": schema,
                    },
                }
            )
            datrix.checkpoint()
            return True

    def receipts(
        self,
        session: Any,
    ) -> tuple[dict[str, Any], ...]:
        identifier = session_id(session)
        with self._lock:
            return tuple(
                dict(item)
                for item in self._receipt_payloads(
                    identifier,
                    self._open_datrix(),
                )
            )

    def recovery_projection(
        self,
        session: Any,
    ) -> dict[str, Any] | None:
        identifier = session_id(session)
        session_record = self.load_session(identifier)
        if session_record is None:
            return None
        events = self.load_events(identifier)
        receipts = self.receipts(identifier)
        projection = {
            "schema": schema,
            "owner": owner,
            "type": "palaver_session_recovery",
            "session": session_record,
            "event_count": len(events),
            "latest_sequence": (
                events[-1].sequence
                if events
                else 0
            ),
            "receipt_count": len(receipts),
            "deterministic_event_replay": True,
            "database": str(self.path),
            "datrix": str(self.path),
            "storage_backend": "straub-datrix",
            "datrix_profile": "chronicle",
            "database_is_authority": False,
            "repository_content_duplicated": False,
            "authority_effect": "none",
            "boundaries": {
                "conversation_owner": "palaver",
                "provider_owner": "opus",
                "task_owner": "niche",
                "persona_owner": "envoy",
                "mutation_owner": "coda",
                "canon_owner": False,
            },
        }
        projection["projection_digest"] = digest(
            {
                key: value
                for key, value in projection.items()
                if key not in {"database", "datrix"}
            }
        )
        return projection
