#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.scrybe import (
    Scrybe,
    ScrybeError,
)


OWNER = "exile:lore"
RETRIEVAL_OWNER = "living:scrybe"
CANONICAL_STORE = "fluid-canon"

SCHEMA = "savant://runtime/lore/living-canon/1.1.0"


class LoreLivingCanonError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _projection(
    schema: str,
    **values: Any,
) -> dict[str, Any]:
    payload = {
        "schema": schema,
        "owner": OWNER,
        "retrieval_owner": RETRIEVAL_OWNER,
        "canonical_store": CANONICAL_STORE,
        **values,
        "projection_authoritative": False,
        "mutation_performed": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(payload)

    return payload


@dataclass(
    frozen=True,
    slots=True,
)
class CanonContext:
    query: Any
    records: tuple[
        Mapping[str, Any],
        ...
    ]
    limit: int
    memory_type: str | None
    at: str | None

    def projection(self) -> dict[str, Any]:
        return _projection(
            "savant://runtime/lore/canon-context/1.1.0",
            query=self.query,
            records=[
                dict(record)
                for record in self.records
            ],
            record_count=len(self.records),
            limit=self.limit,
            memory_type=self.memory_type,
            at=self.at,
            independent_memory_store=False,
        )


class LoreLivingCanon:
    """
    Lore interpretation and projection facade over Scrybe-backed
    Fluid Canon memory.

    Authority boundaries:

    - Fluid Canon owns canonical memory.
    - Scrybe owns retrieval mechanics.
    - Lore owns canon interpretation and bounded projections.
    - Scyon provides shared living behavior independently of this facade.
    - This facade never persists memory.
    - This facade never duplicates Scrybe ranking.
    - This facade never mutates canon.
    - This facade never manufactures authority.
    """

    def __init__(
        self,
        *,
        scrybe: Scrybe,
    ) -> None:
        if not isinstance(
            scrybe,
            Scrybe,
        ):
            raise LoreLivingCanonError(
                "scrybe must be a Scrybe instance"
            )

        self.scrybe = scrybe

    @staticmethod
    def _validate_limit(
        limit: int,
    ) -> int:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise LoreLivingCanonError(
                "limit must be a positive integer"
            )

        return limit

    @staticmethod
    def _normalize_records(
        records: Any,
    ) -> tuple[
        Mapping[str, Any],
        ...
    ]:
        try:
            return tuple(
                dict(record)
                for record in records
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise LoreLivingCanonError(
                "Scrybe returned an invalid projection sequence"
            ) from exc

    def recall(
        self,
        query: Any,
        *,
        limit: int = 9,
        memory_type: str | None = None,
        at: str | None = None,
    ) -> CanonContext:
        self._validate_limit(limit)

        try:
            records = self.scrybe.recall(
                query,
                limit=limit,
                memory_type=memory_type,
                at=at,
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        return CanonContext(
            query=query,
            records=self._normalize_records(records),
            limit=limit,
            memory_type=memory_type,
            at=at,
        )

    def canonical_truth(
        self,
        query: Any,
        *,
        limit: int = 9,
    ) -> dict[str, Any]:
        context = self.recall(
            query,
            limit=limit,
        )

        return _projection(
            "savant://runtime/lore/canonical-truth/1.1.0",
            context=context.projection(),
            current_only=True,
            historical=False,
        )

    def historical_truth(
        self,
        query: Any,
        *,
        at: str,
        limit: int = 9,
    ) -> dict[str, Any]:
        if not str(
            at or ""
        ).strip():
            raise LoreLivingCanonError(
                "at is required for historical truth"
            )

        context = self.recall(
            query,
            limit=limit,
            at=at,
        )

        return _projection(
            "savant://runtime/lore/historical-truth/1.1.0",
            at=at,
            context=context.projection(),
            historical=True,
        )

    def authority(
        self,
        authority: Any,
    ) -> dict[str, Any]:
        try:
            records = (
                self.scrybe
                .authority_recall(authority)
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        normalized = self._normalize_records(
            records
        )

        return _projection(
            "savant://runtime/lore/authority-recall/1.1.0",
            authority_query=authority,
            records=[
                dict(record)
                for record in normalized
            ],
            record_count=len(normalized),
        )

    def relationships(
        self,
        identity: str,
        *,
        relationship_type: str | None = None,
    ) -> dict[str, Any]:
        if not str(
            identity or ""
        ).strip():
            raise LoreLivingCanonError(
                "identity is required"
            )

        try:
            records = self.scrybe.relationships(
                identity,
                relationship_type=relationship_type,
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        normalized = self._normalize_records(
            records
        )

        return _projection(
            "savant://runtime/lore/relationships/1.1.0",
            identity=identity,
            relationship_type=relationship_type,
            records=[
                dict(record)
                for record in normalized
            ],
            record_count=len(normalized),
        )

    def context(
        self,
        query: Any,
        *,
        limit: int = 9,
        memory_type: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        result = self.recall(
            query,
            limit=limit,
            memory_type=memory_type,
            at=at,
        )

        return _projection(
            "savant://runtime/lore/context-projection/1.1.0",
            context=result.projection(),
            bounded=True,
            independent_memory_store=False,
        )

    def hydrate(
        self,
        query: Any,
        *,
        limit: int | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        if limit is not None:
            self._validate_limit(limit)

        try:
            context = self.scrybe.hydrate(
                query,
                limit=limit,
                at=at,
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        return _projection(
            "savant://runtime/lore/context-hydration/1.1.0",
            query=query,
            at=at,
            context=dict(context),
            bounded=True,
            independent_memory_store=False,
        )

    def explain(
        self,
        query: Any,
        *,
        limit: int = 9,
        at: str | None = None,
    ) -> dict[str, Any]:
        self._validate_limit(limit)

        try:
            explanation = self.scrybe.explain(
                query,
                limit=limit,
                at=at,
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        return _projection(
            "savant://runtime/lore/explanation/1.1.0",
            query=query,
            at=at,
            explanation=dict(explanation),
        )

    def feed(
        self,
        *,
        memory_type: str | None = None,
        at: str | None = None,
        limit: int = 18,
    ) -> dict[str, Any]:
        self._validate_limit(limit)

        try:
            records = self.scrybe.feed(
                memory_type=memory_type,
                at=at,
                limit=limit,
            )
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        normalized = self._normalize_records(
            records
        )

        return _projection(
            "savant://runtime/lore/canon-feed/1.1.0",
            memory_type=memory_type,
            at=at,
            limit=limit,
            records=[
                dict(record)
                for record in normalized
            ],
            record_count=len(normalized),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        try:
            scrybe_health = self.scrybe.health()
        except ScrybeError as exc:
            raise LoreLivingCanonError(
                str(exc)
            ) from exc

        return _projection(
            SCHEMA,
            canon_read=True,
            historical_read=True,
            authority_recall=True,
            relationship_traversal=True,
            context_hydration=True,
            explanatory_projection=True,
            canon_feed=True,
            scrybe_retrieval_reused=True,
            independent_ranking_engine=False,
            independent_memory_store=False,
            canon_mutation=False,
            scrybe_health=scrybe_health,
        )


def bind_scrybe(
    scrybe: Scrybe,
) -> LoreLivingCanon:
    return LoreLivingCanon(
        scrybe=scrybe
    )
