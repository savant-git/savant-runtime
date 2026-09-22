#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from guise import (
    OWNER,
    SCHEMA,
    SPECIALIZATION,
    digest,
)


class ProjectionIndex:
    def __init__(self) -> None:
        self._dependencies: dict[
            str,
            set[str],
        ] = defaultdict(set)

        self._projections: dict[
            str,
            dict[str, Any],
        ] = {}

    def register(
        self,
        *,
        projection_id: str,
        payload: Mapping[str, Any],
        dependencies: Iterable[str],
    ) -> dict[str, Any]:
        normalized_dependencies = {
            str(item).strip()
            for item in dependencies
            if str(item).strip()
        }

        value = dict(payload)

        record = {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "projection_id": projection_id,
            "payload_digest": digest(
                value
            ),
            "dependencies": sorted(
                normalized_dependencies
            ),
            "stale": False,
            "authority_effect": "none",
        }

        self._projections[
            projection_id
        ] = record

        for dependency in (
            normalized_dependencies
        ):
            self._dependencies[
                dependency
            ].add(
                projection_id
            )

        return dict(record)

    def invalidate(
        self,
        changed_ids: Iterable[str],
    ) -> dict[str, Any]:
        changed = {
            str(item).strip()
            for item in changed_ids
            if str(item).strip()
        }

        affected: set[str] = set()

        for identifier in changed:
            affected.update(
                self._dependencies.get(
                    identifier,
                    set(),
                )
            )

        for projection_id in affected:
            self._projections[
                projection_id
            ]["stale"] = True

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "operation": (
                "incremental_invalidation"
            ),
            "changed_ids": sorted(
                changed
            ),
            "affected_projections": (
                sorted(affected)
            ),
            "authority_effect": "none",
        }

    def drift(
        self,
        *,
        projection_id: str,
        current_payload: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        record = self._projections.get(
            projection_id
        )

        if record is None:
            return {
                "projection_id": (
                    projection_id
                ),
                "known": False,
                "drifted": True,
                "reason": "unregistered",
                "authority_effect": "none",
            }

        current_digest = digest(
            dict(current_payload)
        )

        drifted = (
            current_digest
            != record["payload_digest"]
        )

        return {
            "projection_id": projection_id,
            "known": True,
            "drifted": drifted,
            "registered_digest": (
                record["payload_digest"]
            ),
            "current_digest": (
                current_digest
            ),
            "stale": bool(
                record["stale"]
            ),
            "authority_effect": "none",
        }

    def dependents(
        self,
        identifier: str,
    ) -> list[str]:
        return sorted(
            self._dependencies.get(
                identifier,
                set(),
            )
        )

    def status(self) -> dict[str, Any]:
        stale = sorted(
            projection_id
            for projection_id, record
            in self._projections.items()
            if record["stale"]
        )

        return {
            "schema": SCHEMA,
            "owner": OWNER,
            "specialization": SPECIALIZATION,
            "projection_count": len(
                self._projections
            ),
            "dependency_count": len(
                self._dependencies
            ),
            "stale_projections": stale,
            "authority_effect": "none",
        }
