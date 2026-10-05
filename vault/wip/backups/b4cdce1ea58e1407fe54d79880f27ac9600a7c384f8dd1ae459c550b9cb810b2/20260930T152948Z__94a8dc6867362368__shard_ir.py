#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


schema = "savant.translucent.shard-ir.v1"
authority_effect = "none"

MAX_SHARDS = 100_000
MAX_SEGUES = 250_000
MAX_DEPENDENCIES = 4_096
MAX_DEPTH = 256

SEMANTIC_REFS = MappingProxyType(
    {
        "shard":
            "lex:primitive:shard",

        "segue":
            "lex:core:segue",

        "instance":
            "lex:core:shade",

        "projection":
            "lex:core:wavre",

        "provenance":
            "lex:core:provenance",

        "lineage":
            "lex:core:lineage",

        "truth":
            "lex:core:truth",

        "determinism":
            "lex:core:determinism",
    }
)

TRUTH_STATES = (
    "unknown",
    "claimed",
    "supported",
    "contested",
    "contradicted",
    "verified",
)

_ID_RE = re.compile(
    r"^[a-z0-9][a-z0-9._:/-]{0,255}$"
)

_KIND_RE = re.compile(
    r"^[a-z][a-z0-9._:-]{0,127}$"
)


class ShardIRError(
    ValueError
):
    pass


def _json_safe(
    value: Any,
    *,
    depth: int = 0,
) -> Any:
    if depth > MAX_DEPTH:
        raise ShardIRError(
            f"value exceeds depth {MAX_DEPTH}"
        )

    if (
        value is None
        or isinstance(
            value,
            (
                str,
                bool,
                int,
            ),
        )
    ):
        return value

    if isinstance(
        value,
        float,
    ):
        if not math.isfinite(
            value
        ):
            raise ShardIRError(
                "non-finite numbers are forbidden"
            )

        return value

    if isinstance(
        value,
        Mapping,
    ):
        result: dict[
            str,
            Any,
        ] = {}

        for key in sorted(
            value,
            key=lambda item: str(
                item
            ),
        ):
            text = str(
                key
            )

            if text in result:
                raise ShardIRError(
                    "duplicate mapping key "
                    "after normalization: "
                    f"{text}"
                )

            result[
                text
            ] = _json_safe(
                value[
                    key
                ],
                depth=(
                    depth + 1
                ),
            )

        return result

    if (
        isinstance(
            value,
            Sequence,
        )
        and not isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        return [
            _json_safe(
                item,
                depth=(
                    depth + 1
                ),
            )
            for item
            in value
        ]

    raise ShardIRError(
        "unsupported value type: "
        f"{type(value).__name__}"
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        _json_safe(
            value
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _identity(
    value: Any,
    field: str,
) -> str:
    text = str(
        value
        or ""
    ).strip().casefold()

    if not text:
        raise ShardIRError(
            f"{field} is required"
        )

    if not _ID_RE.fullmatch(
        text
    ):
        raise ShardIRError(
            f"{field} is invalid: "
            f"{text!r}"
        )

    return text


def _kind(
    value: Any,
    field: str = "kind",
) -> str:
    text = str(
        value
        or ""
    ).strip().casefold()

    if not text:
        raise ShardIRError(
            f"{field} is required"
        )

    if not _KIND_RE.fullmatch(
        text
    ):
        raise ShardIRError(
            f"{field} is invalid: "
            f"{text!r}"
        )

    return text


def _truth(
    value: Any,
) -> str:
    text = str(
        value
        or "unknown"
    ).strip().casefold()

    if (
        text
        not in TRUTH_STATES
    ):
        raise ShardIRError(
            "unsupported truth state: "
            f"{text!r}"
        )

    return text


def _strings(
    values: Iterable[
        Any
    ],
) -> tuple[
    str,
    ...,
]:
    items: list[
        str
    ] = []

    seen: set[
        str
    ] = set()

    for raw in values:
        value = _identity(
            raw,
            "reference",
        )

        if value in seen:
            continue

        seen.add(
            value
        )

        items.append(
            value
        )

    if (
        len(
            items
        )
        > MAX_DEPENDENCIES
    ):
        raise ShardIRError(
            "reference count exceeds "
            f"{MAX_DEPENDENCIES}"
        )

    return tuple(
        items
    )


@dataclass(
    frozen=True,
    slots=True,
)
class Shard:
    id: str
    kind: str
    payload: Mapping[
        str,
        Any,
    ]
    bindings: Mapping[
        str,
        str,
    ]
    dependencies: tuple[
        str,
        ...,
    ]
    provenance: Mapping[
        str,
        Any,
    ]
    lineage: Mapping[
        str,
        Any,
    ]
    truth: str
    semantic_refs: Mapping[
        str,
        str,
    ]
    digest: str

    @classmethod
    def build(
        cls,
        *,
        shard_id: str,
        kind: str,
        payload: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        bindings: (
            Mapping[
                str,
                str,
            ]
            | None
        ) = None,
        dependencies: Iterable[
            str
        ] = (),
        provenance: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        lineage: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        truth: str = "unknown",
        semantic_refs: (
            Mapping[
                str,
                str,
            ]
            | None
        ) = None,
    ) -> "Shard":
        identity = _identity(
            shard_id,
            "shard.id",
        )

        normalized_kind = _kind(
            kind,
            "shard.kind",
        )

        normalized_bindings = {
            _kind(
                name,
                "binding.name",
            ):
                _identity(
                    target,
                    "binding.target",
                )
            for name, target
            in sorted(
                (
                    bindings
                    or {}
                ).items()
            )
        }

        normalized_dependencies = (
            _strings(
                dependencies
            )
        )

        normalized_refs = dict(
            SEMANTIC_REFS
        )

        normalized_refs.update(
            {
                str(
                    key
                )
                .strip()
                .casefold():
                    str(
                        value
                    )
                    .strip()
                    .casefold()
                for key, value
                in sorted(
                    (
                        semantic_refs
                        or {}
                    ).items()
                )
            }
        )

        material = {
            "schema":
                schema,

            "id":
                identity,

            "kind":
                normalized_kind,

            "payload":
                _json_safe(
                    payload
                    or {}
                ),

            "bindings":
                normalized_bindings,

            "dependencies":
                list(
                    normalized_dependencies
                ),

            "provenance":
                _json_safe(
                    provenance
                    or {}
                ),

            "lineage":
                _json_safe(
                    lineage
                    or {}
                ),

            "truth":
                _truth(
                    truth
                ),

            "semantic_refs":
                normalized_refs,

            "authority_effect":
                authority_effect,
        }

        return cls(
            id=identity,
            kind=normalized_kind,
            payload=MappingProxyType(
                deepcopy(
                    material[
                        "payload"
                    ]
                )
            ),
            bindings=MappingProxyType(
                deepcopy(
                    normalized_bindings
                )
            ),
            dependencies=(
                normalized_dependencies
            ),
            provenance=MappingProxyType(
                deepcopy(
                    material[
                        "provenance"
                    ]
                )
            ),
            lineage=MappingProxyType(
                deepcopy(
                    material[
                        "lineage"
                    ]
                )
            ),
            truth=material[
                "truth"
            ],
            semantic_refs=MappingProxyType(
                deepcopy(
                    normalized_refs
                )
            ),
            digest=digest(
                material
            ),
        )

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "schema":
                schema,

            "id":
                self.id,

            "kind":
                self.kind,

            "payload":
                deepcopy(
                    dict(
                        self.payload
                    )
                ),

            "bindings":
                deepcopy(
                    dict(
                        self.bindings
                    )
                ),

            "dependencies":
                list(
                    self.dependencies
                ),

            "provenance":
                deepcopy(
                    dict(
                        self.provenance
                    )
                ),

            "lineage":
                deepcopy(
                    dict(
                        self.lineage
                    )
                ),

            "truth":
                self.truth,

            "semantic_refs":
                deepcopy(
                    dict(
                        self.semantic_refs
                    )
                ),

            "digest":
                self.digest,

            "authority_effect":
                authority_effect,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class SegueShard:
    id: str
    source: str
    target: str
    relation: str
    payload: Mapping[
        str,
        Any,
    ]
    dependencies: tuple[
        str,
        ...,
    ]
    provenance: Mapping[
        str,
        Any,
    ]
    lineage: Mapping[
        str,
        Any,
    ]
    active: bool
    semantic_refs: Mapping[
        str,
        str,
    ]
    digest: str

    @classmethod
    def build(
        cls,
        *,
        source: str,
        target: str,
        relation: str,
        segue_id: (
            str
            | None
        ) = None,
        payload: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        dependencies: Iterable[
            str
        ] = (),
        provenance: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        lineage: (
            Mapping[
                str,
                Any,
            ]
            | None
        ) = None,
        active: bool = True,
        semantic_refs: (
            Mapping[
                str,
                str,
            ]
            | None
        ) = None,
    ) -> "SegueShard":
        src = _identity(
            source,
            "segue.source",
        )

        dst = _identity(
            target,
            "segue.target",
        )

        rel = _kind(
            relation,
            "segue.relation",
        )

        stable_material = {
            "source":
                src,

            "target":
                dst,

            "relation":
                rel,

            "payload":
                _json_safe(
                    payload
                    or {}
                ),
        }

        identity = _identity(
            segue_id
            or (
                "segue:"
                + digest(
                    stable_material
                )[
                    :32
                ]
            ),
            "segue.id",
        )

        deps = _strings(
            (
                src,
                dst,
                *tuple(
                    dependencies
                ),
            )
        )

        refs = dict(
            SEMANTIC_REFS
        )

        refs.update(
            {
                str(
                    key
                )
                .strip()
                .casefold():
                    str(
                        value
                    )
                    .strip()
                    .casefold()
                for key, value
                in sorted(
                    (
                        semantic_refs
                        or {}
                    ).items()
                )
            }
        )

        material = {
            "schema":
                schema,

            "id":
                identity,

            "kind":
                "segue_shard",

            "source":
                src,

            "target":
                dst,

            "relation":
                rel,

            "payload":
                stable_material[
                    "payload"
                ],

            "dependencies":
                list(
                    deps
                ),

            "provenance":
                _json_safe(
                    provenance
                    or {}
                ),

            "lineage":
                _json_safe(
                    lineage
                    or {}
                ),

            "active":
                bool(
                    active
                ),

            "semantic_refs":
                refs,

            "authority_effect":
                authority_effect,
        }

        return cls(
            id=identity,
            source=src,
            target=dst,
            relation=rel,
            payload=MappingProxyType(
                deepcopy(
                    material[
                        "payload"
                    ]
                )
            ),
            dependencies=deps,
            provenance=MappingProxyType(
                deepcopy(
                    material[
                        "provenance"
                    ]
                )
            ),
            lineage=MappingProxyType(
                deepcopy(
                    material[
                        "lineage"
                    ]
                )
            ),
            active=bool(
                active
            ),
            semantic_refs=MappingProxyType(
                deepcopy(
                    refs
                )
            ),
            digest=digest(
                material
            ),
        )

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "schema":
                schema,

            "id":
                self.id,

            "kind":
                "segue_shard",

            "source":
                self.source,

            "target":
                self.target,

            "relation":
                self.relation,

            "payload":
                deepcopy(
                    dict(
                        self.payload
                    )
                ),

            "dependencies":
                list(
                    self.dependencies
                ),

            "provenance":
                deepcopy(
                    dict(
                        self.provenance
                    )
                ),

            "lineage":
                deepcopy(
                    dict(
                        self.lineage
                    )
                ),

            "active":
                self.active,

            "semantic_refs":
                deepcopy(
                    dict(
                        self.semantic_refs
                    )
                ),

            "digest":
                self.digest,

            "authority_effect":
                authority_effect,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ShardProgram:
    language: str
    version: str
    shards: tuple[
        Shard,
        ...,
    ]
    segues: tuple[
        SegueShard,
        ...,
    ]
    source_digest: str
    semantic_digest: str

    @classmethod
    def build(
        cls,
        *,
        language: str,
        version: str,
        shards: Iterable[
            Shard
        ],
        segues: Iterable[
            SegueShard
        ],
        source: str,
    ) -> "ShardProgram":
        shard_items = tuple(
            shards
        )

        segue_items = tuple(
            segues
        )

        if (
            len(
                shard_items
            )
            > MAX_SHARDS
        ):
            raise ShardIRError(
                "shard count exceeds "
                f"{MAX_SHARDS}"
            )

        if (
            len(
                segue_items
            )
            > MAX_SEGUES
        ):
            raise ShardIRError(
                "segue count exceeds "
                f"{MAX_SEGUES}"
            )

        shard_index: dict[
            str,
            Shard,
        ] = {}

        for shard in shard_items:
            if (
                shard.id
                in shard_index
            ):
                raise ShardIRError(
                    "duplicate shard identity: "
                    f"{shard.id}"
                )

            shard_index[
                shard.id
            ] = shard

        segue_index: dict[
            str,
            SegueShard,
        ] = {}

        for segue in segue_items:
            if (
                segue.id
                in segue_index
                or segue.id
                in shard_index
            ):
                raise ShardIRError(
                    "duplicate runtime identity: "
                    f"{segue.id}"
                )

            segue_index[
                segue.id
            ] = segue

            if (
                segue.source
                not in shard_index
            ):
                raise ShardIRError(
                    "segue source is unresolved: "
                    f"{segue.source}"
                )

            if (
                segue.target
                not in shard_index
            ):
                raise ShardIRError(
                    "segue target is unresolved: "
                    f"{segue.target}"
                )

        for shard in shard_items:
            for target in shard.dependencies:
                if (
                    target
                    not in shard_index
                    and target
                    not in segue_index
                ):
                    raise ShardIRError(
                        "shard dependency is unresolved: "
                        f"{shard.id} -> {target}"
                    )

            for target in shard.bindings.values():
                if (
                    target
                    not in shard_index
                    and target
                    not in segue_index
                ):
                    raise ShardIRError(
                        "shard binding is unresolved: "
                        f"{shard.id} -> {target}"
                    )

        semantic = {
            "schema":
                schema,

            "language":
                _kind(
                    language,
                    "program.language",
                ),

            "version":
                str(
                    version
                ),

            "shards":
                [
                    item.to_dict()
                    for item
                    in sorted(
                        shard_items,
                        key=lambda x: x.id,
                    )
                ],

            "segues":
                [
                    item.to_dict()
                    for item
                    in sorted(
                        segue_items,
                        key=lambda x: x.id,
                    )
                ],

            "authority_effect":
                authority_effect,
        }

        return cls(
            language=semantic[
                "language"
            ],
            version=str(
                version
            ),
            shards=tuple(
                sorted(
                    shard_items,
                    key=lambda x: x.id,
                )
            ),
            segues=tuple(
                sorted(
                    segue_items,
                    key=lambda x: x.id,
                )
            ),
            source_digest=hashlib.sha256(
                source.encode(
                    "utf-8"
                )
            ).hexdigest(),
            semantic_digest=digest(
                semantic
            ),
        )

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return {
            "schema":
                schema,

            "language":
                self.language,

            "version":
                self.version,

            "shard_count":
                len(
                    self.shards
                ),

            "segue_count":
                len(
                    self.segues
                ),

            "shards":
                [
                    item.to_dict()
                    for item
                    in self.shards
                ],

            "segues":
                [
                    item.to_dict()
                    for item
                    in self.segues
                ],

            "source_digest":
                self.source_digest,

            "semantic_digest":
                self.semantic_digest,

            "authority_effect":
                authority_effect,
        }


def selftest() -> dict[
    str,
    Any,
]:
    first = Shard.build(
        shard_id="a",
        kind="data",
        payload={
            "value":
                1,
        },
    )

    second = Shard.build(
        shard_id="b",
        kind="projection",
        bindings={
            "source":
                "a",
        },
        dependencies=(
            "a",
        ),
    )

    edge = SegueShard.build(
        source="a",
        target="b",
        relation="projects",
    )

    program_a = (
        ShardProgram.build(
            language="translucent",
            version="1",
            shards=(
                second,
                first,
            ),
            segues=(
                edge,
            ),
            source="same",
        )
    )

    program_b = (
        ShardProgram.build(
            language="translucent",
            version="1",
            shards=(
                first,
                second,
            ),
            segues=(
                edge,
            ),
            source="same",
        )
    )

    checks = {
        "authority_none":
            (
                authority_effect
                == "none"
            ),

        "shard_bound":
            (
                first.semantic_refs.get(
                    "shard"
                )
                == "lex:primitive:shard"
            ),

        "segue_bound":
            (
                edge.semantic_refs.get(
                    "segue"
                )
                == "lex:core:segue"
            ),

        "immutable_digest":
            (
                first.digest
                == Shard.build(
                    shard_id="a",
                    kind="data",
                    payload={
                        "value":
                            1,
                    },
                ).digest
            ),

        "program_order_independent":
            (
                program_a.semantic_digest
                == program_b.semantic_digest
            ),

        "source_digest_present":
            bool(
                program_a.source_digest
            ),
    }

    return {
        "schema":
            (
                "savant.translucent."
                "shard-ir-selftest.v1"
            ),

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "semantic_digest":
            program_a.semantic_digest,

        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
