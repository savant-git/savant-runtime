#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


schema = "savant.nimble.graph.v1"
authority_effect = "none"

MAX_SHARDS = 100_000
MAX_SEGUE_SHARDS = 200_000
MAX_DEPENDENCIES = 4_096
MAX_VALUE_DEPTH = 64

SHARD_KINDS = frozenset(
    {
        "source",
        "substance",
        "selection",
        "predicate",
        "projection",
        "ordering",
        "window",
        "aggregation",
        "composition",
        "mutation",
        "retirement",
        "checkpoint",
        "assertion",
        "truth-gate",
        "projection-request",
        "result",
    }
)

SEGUE_KINDS = frozenset(
    {
        "feeds",
        "depends",
        "filters",
        "projects",
        "orders",
        "groups",
        "aggregates",
        "joins",
        "unions",
        "intersects",
        "subtracts",
        "walks",
        "supersedes",
        "retires",
        "guards",
        "commits",
        "projects-to",
    }
)


class NimbleGraphError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise NimbleGraphError(
            f"value is not canonical-json compatible: {exc}"
        ) from exc


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def _clean(value: Any, field_name: str) -> str:
    text = str(value or "").strip()

    if not text:
        raise NimbleGraphError(
            f"{field_name} is required"
        )

    return text


def _validate_value(
    value: Any,
    *,
    depth: int = 0,
) -> None:
    if depth > MAX_VALUE_DEPTH:
        raise NimbleGraphError(
            f"value exceeds depth {MAX_VALUE_DEPTH}"
        )

    if value is None:
        return

    if isinstance(
        value,
        (
            str,
            bool,
            int,
        ),
    ):
        return

    if isinstance(
        value,
        float,
    ):
        if not math.isfinite(
            value
        ):
            raise NimbleGraphError(
                "non-finite numbers are forbidden"
            )

        return

    if isinstance(
        value,
        Mapping,
    ):
        for key, child in value.items():
            if not isinstance(
                key,
                str,
            ):
                raise NimbleGraphError(
                    "mapping keys must be strings"
                )

            _validate_value(
                child,
                depth=depth + 1,
            )

        return

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        for child in value:
            _validate_value(
                child,
                depth=depth + 1,
            )

        return

    raise NimbleGraphError(
        "unsupported value type: "
        f"{type(value).__name__}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Shard:
    id: str
    kind: str
    substance: Mapping[str, Any] = field(
        default_factory=dict
    )
    semantic_refs: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()
    authority_effect: str = "none"

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "id",
            _clean(
                self.id,
                "shard.id",
            ),
        )

        normalized_kind = (
            _clean(
                self.kind,
                "shard.kind",
            )
            .casefold()
        )

        if (
            normalized_kind
            not in SHARD_KINDS
        ):
            raise NimbleGraphError(
                "unsupported shard kind: "
                f"{normalized_kind}"
            )

        object.__setattr__(
            self,
            "kind",
            normalized_kind,
        )

        substance = dict(
            self.substance
        )

        _validate_value(
            substance
        )

        object.__setattr__(
            self,
            "substance",
            substance,
        )

        object.__setattr__(
            self,
            "semantic_refs",
            tuple(
                dict.fromkeys(
                    _clean(
                        value,
                        "semantic_ref",
                    )
                    for value
                    in self.semantic_refs
                )
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    _clean(
                        value,
                        "provenance",
                    )
                    for value
                    in self.provenance
                )
            ),
        )

        object.__setattr__(
            self,
            "lineage",
            tuple(
                dict.fromkeys(
                    _clean(
                        value,
                        "lineage",
                    )
                    for value
                    in self.lineage
                )
            ),
        )

        if (
            self.authority_effect
            != "none"
        ):
            raise NimbleGraphError(
                "nimble graph shards cannot "
                "self-declare authority effects"
            )

    def canonical(
        self,
    ) -> dict[str, Any]:
        return {
            "id":
                self.id,

            "kind":
                self.kind,

            "substance":
                dict(
                    self.substance
                ),

            "semantic_refs":
                list(
                    self.semantic_refs
                ),

            "provenance":
                list(
                    self.provenance
                ),

            "lineage":
                list(
                    self.lineage
                ),

            "authority_effect":
                self.authority_effect,
        }

    @property
    def digest(
        self,
    ) -> str:
        return digest(
            self.canonical()
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SegueShard:
    id: str
    kind: str
    source: str
    target: str
    substance: Mapping[str, Any] = field(
        default_factory=dict
    )
    semantic_refs: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    authority_effect: str = "none"

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "id",
            _clean(
                self.id,
                "segue_shard.id",
            ),
        )

        normalized_kind = (
            _clean(
                self.kind,
                "segue_shard.kind",
            )
            .casefold()
        )

        if (
            normalized_kind
            not in SEGUE_KINDS
        ):
            raise NimbleGraphError(
                "unsupported segue shard kind: "
                f"{normalized_kind}"
            )

        object.__setattr__(
            self,
            "kind",
            normalized_kind,
        )

        object.__setattr__(
            self,
            "source",
            _clean(
                self.source,
                "segue_shard.source",
            ),
        )

        object.__setattr__(
            self,
            "target",
            _clean(
                self.target,
                "segue_shard.target",
            ),
        )

        substance = dict(
            self.substance
        )

        _validate_value(
            substance
        )

        object.__setattr__(
            self,
            "substance",
            substance,
        )

        object.__setattr__(
            self,
            "semantic_refs",
            tuple(
                dict.fromkeys(
                    _clean(
                        value,
                        "semantic_ref",
                    )
                    for value
                    in self.semantic_refs
                )
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            tuple(
                dict.fromkeys(
                    _clean(
                        value,
                        "provenance",
                    )
                    for value
                    in self.provenance
                )
            ),
        )

        if (
            self.authority_effect
            != "none"
        ):
            raise NimbleGraphError(
                "segue shards cannot "
                "self-declare authority effects"
            )

    def canonical(
        self,
    ) -> dict[str, Any]:
        return {
            "id":
                self.id,

            "kind":
                self.kind,

            "source":
                self.source,

            "target":
                self.target,

            "substance":
                dict(
                    self.substance
                ),

            "semantic_refs":
                list(
                    self.semantic_refs
                ),

            "provenance":
                list(
                    self.provenance
                ),

            "authority_effect":
                self.authority_effect,
        }

    @property
    def digest(
        self,
    ) -> str:
        return digest(
            self.canonical()
        )


class NimbleGraph:
    def __init__(
        self,
    ) -> None:
        self._shards: dict[
            str,
            Shard,
        ] = {}

        self._segues: dict[
            str,
            SegueShard,
        ] = {}

    @property
    def shards(
        self,
    ) -> tuple[Shard, ...]:
        return tuple(
            self._shards[key]
            for key
            in sorted(
                self._shards
            )
        )

    @property
    def segue_shards(
        self,
    ) -> tuple[SegueShard, ...]:
        return tuple(
            self._segues[key]
            for key
            in sorted(
                self._segues
            )
        )

    def add_shard(
        self,
        shard: Shard,
    ) -> Shard:
        if (
            len(self._shards)
            >= MAX_SHARDS
            and shard.id
            not in self._shards
        ):
            raise NimbleGraphError(
                "nimble graph exceeds "
                f"{MAX_SHARDS} shards"
            )

        existing = (
            self._shards.get(
                shard.id
            )
        )

        if existing is not None:
            if (
                existing.digest
                != shard.digest
            ):
                raise NimbleGraphError(
                    "shard identity already "
                    "contains different substance: "
                    f"{shard.id}"
                )

            return existing

        self._shards[
            shard.id
        ] = shard

        return shard

    def add_segue_shard(
        self,
        segue: SegueShard,
    ) -> SegueShard:
        if (
            len(self._segues)
            >= MAX_SEGUE_SHARDS
            and segue.id
            not in self._segues
        ):
            raise NimbleGraphError(
                "nimble graph exceeds "
                f"{MAX_SEGUE_SHARDS} "
                "segue shards"
            )

        if (
            segue.source
            not in self._shards
        ):
            raise NimbleGraphError(
                "segue source does not "
                "resolve to a shard: "
                f"{segue.source}"
            )

        if (
            segue.target
            not in self._shards
        ):
            raise NimbleGraphError(
                "segue target does not "
                "resolve to a shard: "
                f"{segue.target}"
            )

        existing = (
            self._segues.get(
                segue.id
            )
        )

        if existing is not None:
            if (
                existing.digest
                != segue.digest
            ):
                raise NimbleGraphError(
                    "segue shard identity already "
                    "contains different substance: "
                    f"{segue.id}"
                )

            return existing

        self._segues[
            segue.id
        ] = segue

        return segue

    def incoming(
        self,
        shard_id: str,
    ) -> tuple[SegueShard, ...]:
        target = _clean(
            shard_id,
            "shard_id",
        )

        return tuple(
            segue
            for segue
            in self.segue_shards
            if segue.target == target
        )

    def outgoing(
        self,
        shard_id: str,
    ) -> tuple[SegueShard, ...]:
        source = _clean(
            shard_id,
            "shard_id",
        )

        return tuple(
            segue
            for segue
            in self.segue_shards
            if segue.source == source
        )

    def dependency_order(
        self,
    ) -> tuple[str, ...]:
        dependency_kinds = {
            "feeds",
            "depends",
            "filters",
            "projects",
            "orders",
            "groups",
            "aggregates",
            "joins",
            "unions",
            "intersects",
            "subtracts",
            "walks",
            "guards",
            "commits",
            "projects-to",
        }

        indegree = {
            shard_id: 0
            for shard_id
            in self._shards
        }

        adjacency: dict[
            str,
            set[str],
        ] = {
            shard_id: set()
            for shard_id
            in self._shards
        }

        dependency_count = 0

        for segue in self._segues.values():
            if (
                segue.kind
                not in dependency_kinds
            ):
                continue

            dependency_count += 1

            if (
                dependency_count
                > MAX_DEPENDENCIES
                * max(
                    1,
                    len(
                        self._shards
                    ),
                )
            ):
                raise NimbleGraphError(
                    "dependency surface exceeds "
                    "configured bound"
                )

            if (
                segue.target
                in adjacency[
                    segue.source
                ]
            ):
                continue

            adjacency[
                segue.source
            ].add(
                segue.target
            )

            indegree[
                segue.target
            ] += 1

        ready = sorted(
            shard_id
            for shard_id, count
            in indegree.items()
            if count == 0
        )

        order: list[str] = []

        while ready:
            current = ready.pop(
                0
            )

            order.append(
                current
            )

            for target in sorted(
                adjacency[
                    current
                ]
            ):
                indegree[
                    target
                ] -= 1

                if (
                    indegree[
                        target
                    ]
                    == 0
                ):
                    ready.append(
                        target
                    )

                    ready.sort()

        if (
            len(order)
            != len(
                self._shards
            )
        ):
            cyclic = sorted(
                shard_id
                for shard_id, count
                in indegree.items()
                if count > 0
            )

            raise NimbleGraphError(
                "execution dependency cycle: "
                + ", ".join(
                    cyclic
                )
            )

        return tuple(
            order
        )

    def canonical(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                schema,

            "authority_effect":
                authority_effect,

            "shards":
                [
                    shard.canonical()
                    for shard
                    in self.shards
                ],

            "segue_shards":
                [
                    segue.canonical()
                    for segue
                    in self.segue_shards
                ],

            "dependency_order":
                list(
                    self.dependency_order()
                ),
        }

    @property
    def digest(
        self,
    ) -> str:
        return digest(
            self.canonical()
        )


def graph_from(
    *,
    shards: Iterable[Shard],
    segue_shards: Iterable[SegueShard],
) -> NimbleGraph:
    graph = NimbleGraph()

    for shard in shards:
        graph.add_shard(
            shard
        )

    for segue in segue_shards:
        graph.add_segue_shard(
            segue
        )

    return graph


def manifest() -> dict[str, Any]:
    value = {
        "schema":
            schema,

        "owner":
            "savant",

        "language":
            "nimble",

        "source_extension":
            ".nimble",

        "authority_effect":
            authority_effect,

        "execution_model":
            "shard-graph",

        "objects":
            [
                "shard",
                "segue-shard",
            ],

        "properties":
            {
                "immutable_identity":
                    True,

                "typed_segues":
                    True,

                "dependency_closed":
                    True,

                "deterministic_order":
                    True,

                "presentation_independent":
                    True,

                "storage_engine_selected":
                    False,
            },

        "shard_kinds":
            sorted(
                SHARD_KINDS
            ),

        "segue_kinds":
            sorted(
                SEGUE_KINDS
            ),
    }

    return {
        **value,
        "digest":
            digest(
                value
            ),
    }


def selftest() -> dict[str, Any]:
    graph = NimbleGraph()

    source = graph.add_shard(
        Shard(
            id="source.people",
            kind="source",
            substance={
                "datrix":
                    "people",
            },
        )
    )

    predicate = graph.add_shard(
        Shard(
            id="predicate.active",
            kind="predicate",
            substance={
                "path":
                    "payload.active",

                "operator":
                    "eq",

                "value":
                    True,
            },
        )
    )

    result = graph.add_shard(
        Shard(
            id="result.active",
            kind="result",
            substance={
                "projection":
                    [
                        "id",
                        "payload.name",
                    ],
            },
        )
    )

    graph.add_segue_shard(
        SegueShard(
            id="segue.source.predicate",
            kind="feeds",
            source=source.id,
            target=predicate.id,
        )
    )

    graph.add_segue_shard(
        SegueShard(
            id="segue.predicate.result",
            kind="filters",
            source=predicate.id,
            target=result.id,
        )
    )

    first_digest = (
        graph.digest
    )

    second = graph_from(
        shards=[
            result,
            source,
            predicate,
        ],
        segue_shards=[
            SegueShard(
                id="segue.predicate.result",
                kind="filters",
                source=predicate.id,
                target=result.id,
            ),
            SegueShard(
                id="segue.source.predicate",
                kind="feeds",
                source=source.id,
                target=predicate.id,
            ),
        ],
    )

    immutable_conflict = False

    try:
        graph.add_shard(
            Shard(
                id="source.people",
                kind="source",
                substance={
                    "datrix":
                        "different",
                },
            )
        )

    except NimbleGraphError:
        immutable_conflict = True

    cycle_rejected = False

    try:
        cyclic = NimbleGraph()

        cyclic.add_shard(
            Shard(
                id="a",
                kind="source",
            )
        )

        cyclic.add_shard(
            Shard(
                id="b",
                kind="result",
            )
        )

        cyclic.add_segue_shard(
            SegueShard(
                id="a-b",
                kind="feeds",
                source="a",
                target="b",
            )
        )

        cyclic.add_segue_shard(
            SegueShard(
                id="b-a",
                kind="depends",
                source="b",
                target="a",
            )
        )

        cyclic.dependency_order()

    except NimbleGraphError:
        cycle_rejected = True

    checks = {
        "authority_none":
            authority_effect
            == "none",

        "two_object_model":
            manifest()[
                "objects"
            ]
            == [
                "shard",
                "segue-shard",
            ],

        "source_extension_nimble":
            manifest()[
                "source_extension"
            ]
            == ".nimble",

        "three_shards":
            len(
                graph.shards
            )
            == 3,

        "two_segues":
            len(
                graph.segue_shards
            )
            == 2,

        "deterministic_order":
            graph.dependency_order()
            == (
                "source.people",
                "predicate.active",
                "result.active",
            ),

        "deterministic_graph":
            first_digest
            == second.digest,

        "immutable_identity":
            immutable_conflict,

        "cycle_rejected":
            cycle_rejected,

        "storage_engine_not_invented":
            manifest()[
                "properties"
            ][
                "storage_engine_selected"
            ]
            is False,
    }

    return {
        "schema":
            "savant.nimble.graph-selftest.v1",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "digest":
            graph.digest,

        "manifest_digest":
            manifest()[
                "digest"
            ],
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
