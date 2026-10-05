#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "savant.translucent.shard-ir.v1"
PROGRAM_SCHEMA = "savant.translucent.shard-program.v1"

AUTHORITY_EFFECT = "none"

MAX_SHARDS = 100_000
MAX_SEGUES = 250_000
MAX_PAYLOAD_BYTES = 1_048_576
MAX_DEPTH = 64


class ShardIRError(ValueError):
    pass


def _json_safe(
    value: Any,
    depth: int = 0,
) -> Any:
    if depth > MAX_DEPTH:
        raise ShardIRError(
            "maximum shard value depth exceeded"
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
        out: dict[str, Any] = {}

        for key, item in value.items():
            if (
                not isinstance(
                    key,
                    str,
                )
                or not key
            ):
                raise ShardIRError(
                    "mapping keys must be "
                    "non-empty strings"
                )

            if key in out:
                raise ShardIRError(
                    "duplicate mapping key: "
                    f"{key}"
                )

            out[key] = _json_safe(
                item,
                depth + 1,
            )

        return out

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            _json_safe(
                item,
                depth + 1,
            )
            for item in value
        ]

    raise ShardIRError(
        "unsupported shard value: "
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


def _token(
    value: str,
    label: str,
) -> str:
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ShardIRError(
            f"{label} must be "
            "a non-empty string"
        )

    normalized = (
        value
        .strip()
        .casefold()
    )

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-._:/"
    )

    if any(
        character not in allowed
        for character in normalized
    ):
        raise ShardIRError(
            f"{label} contains "
            "unsupported characters: "
            f"{value!r}"
        )

    return normalized


def _strings(
    values: Iterable[str],
) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []

    for value in values:
        item = _token(
            value,
            "reference",
        )

        if item not in seen:
            seen.add(
                item
            )

            out.append(
                item
            )

    return tuple(
        out
    )


def _frozen_map(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    safe = _json_safe(
        dict(
            value
            or {}
        )
    )

    encoded = canonical_json(
        safe
    ).encode(
        "utf-8"
    )

    if (
        len(
            encoded
        )
        > MAX_PAYLOAD_BYTES
    ):
        raise ShardIRError(
            "shard payload exceeds "
            "resource bound"
        )

    return MappingProxyType(
        safe
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SourceWitness:
    identity: str
    digest: str

    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    authority_witness: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "identity",
            _token(
                self.identity,
                "source identity",
            ),
        )

        if (
            len(
                self.digest
            )
            != 64
            or any(
                character
                not in "0123456789abcdef"
                for character
                in self.digest
            )
        ):
            raise ShardIRError(
                "source digest must be "
                "lowercase sha256"
            )

        object.__setattr__(
            self,
            "lineage",
            _strings(
                self.lineage
            ),
        )

        object.__setattr__(
            self,
            "provenance",
            _strings(
                self.provenance
            ),
        )

        object.__setattr__(
            self,
            "authority_witness",
            _strings(
                self.authority_witness
            ),
        )

    def primitive(
        self,
    ) -> dict[str, Any]:
        return {
            "identity":
                self.identity,

            "digest":
                self.digest,

            "lineage":
                list(
                    self.lineage
                ),

            "provenance":
                list(
                    self.provenance
                ),

            "authority_witness":
                list(
                    self.authority_witness
                ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class RuntimeShard:
    kind: str
    source: SourceWitness

    payload: Mapping[str, Any] = field(
        default_factory=dict
    )

    owner: str = "translucent"
    plane: str = "execution"

    dependencies: tuple[str, ...] = ()

    truth: Mapping[str, Any] = field(
        default_factory=dict
    )

    capabilities: tuple[str, ...] = ()

    ordinal: int = 0

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "kind",
            _token(
                self.kind,
                "shard kind",
            ),
        )

        object.__setattr__(
            self,
            "owner",
            _token(
                self.owner,
                "owner",
            ),
        )

        object.__setattr__(
            self,
            "plane",
            _token(
                self.plane,
                "plane",
            ),
        )

        object.__setattr__(
            self,
            "dependencies",
            _strings(
                self.dependencies
            ),
        )

        object.__setattr__(
            self,
            "capabilities",
            _strings(
                self.capabilities
            ),
        )

        object.__setattr__(
            self,
            "payload",
            _frozen_map(
                self.payload
            ),
        )

        object.__setattr__(
            self,
            "truth",
            _frozen_map(
                self.truth
            ),
        )

        if (
            not isinstance(
                self.ordinal,
                int,
            )
            or self.ordinal < 0
        ):
            raise ShardIRError(
                "ordinal must be a "
                "non-negative integer"
            )

    def semantic_primitive(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                SCHEMA,

            "class":
                "shard",

            "kind":
                self.kind,

            "owner":
                self.owner,

            "plane":
                self.plane,

            "source":
                self.source.primitive(),

            "dependencies":
                list(
                    self.dependencies
                ),

            "truth":
                dict(
                    self.truth
                ),

            "capabilities":
                list(
                    self.capabilities
                ),

            "payload":
                dict(
                    self.payload
                ),

            "ordinal":
                self.ordinal,

            "authority_effect":
                AUTHORITY_EFFECT,
        }

    @property
    def semantic_digest(
        self,
    ) -> str:
        return digest(
            self.semantic_primitive()
        )

    @property
    def id(
        self,
    ) -> str:
        return (
            f"shard:{self.kind}:"
            f"{self.semantic_digest[:24]}"
        )

    def primitive(
        self,
    ) -> dict[str, Any]:
        out = (
            self.semantic_primitive()
        )

        out["id"] = (
            self.id
        )

        out["semantic_digest"] = (
            self.semantic_digest
        )

        return out


@dataclass(
    frozen=True,
    slots=True,
)
class SegueShard:
    kind: str
    source: SourceWitness

    origin: str
    destination: str

    payload: Mapping[str, Any] = field(
        default_factory=dict
    )

    owner: str = "translucent"

    dependencies: tuple[str, ...] = ()

    truth: Mapping[str, Any] = field(
        default_factory=dict
    )

    ordinal: int = 0

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "kind",
            _token(
                self.kind,
                "segue kind",
            ),
        )

        object.__setattr__(
            self,
            "owner",
            _token(
                self.owner,
                "owner",
            ),
        )

        object.__setattr__(
            self,
            "origin",
            _token(
                self.origin,
                "segue origin",
            ),
        )

        object.__setattr__(
            self,
            "destination",
            _token(
                self.destination,
                "segue destination",
            ),
        )

        object.__setattr__(
            self,
            "dependencies",
            _strings(
                self.dependencies
            ),
        )

        object.__setattr__(
            self,
            "payload",
            _frozen_map(
                self.payload
            ),
        )

        object.__setattr__(
            self,
            "truth",
            _frozen_map(
                self.truth
            ),
        )

        if (
            self.origin
            == self.destination
            and self.kind
            not in {
                "recur",
                "reflect",
                "self",
            }
        ):
            raise ShardIRError(
                "self segue requires "
                "an explicit "
                "self-capable kind"
            )

        if (
            not isinstance(
                self.ordinal,
                int,
            )
            or self.ordinal < 0
        ):
            raise ShardIRError(
                "ordinal must be a "
                "non-negative integer"
            )

    def semantic_primitive(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                SCHEMA,

            "class":
                "segue-shard",

            "kind":
                self.kind,

            "owner":
                self.owner,

            "source":
                self.source.primitive(),

            "origin":
                self.origin,

            "destination":
                self.destination,

            "dependencies":
                list(
                    self.dependencies
                ),

            "truth":
                dict(
                    self.truth
                ),

            "payload":
                dict(
                    self.payload
                ),

            "ordinal":
                self.ordinal,

            "authority_effect":
                AUTHORITY_EFFECT,
        }

    @property
    def semantic_digest(
        self,
    ) -> str:
        return digest(
            self.semantic_primitive()
        )

    @property
    def id(
        self,
    ) -> str:
        return (
            f"segue:{self.kind}:"
            f"{self.semantic_digest[:24]}"
        )

    def primitive(
        self,
    ) -> dict[str, Any]:
        out = (
            self.semantic_primitive()
        )

        out["id"] = (
            self.id
        )

        out["semantic_digest"] = (
            self.semantic_digest
        )

        return out


@dataclass(
    frozen=True,
    slots=True,
)
class ShardProgram:
    shards: tuple[
        RuntimeShard,
        ...,
    ]

    segues: tuple[
        SegueShard,
        ...,
    ] = ()

    source_format: str = "lucid"
    language: str = "translucent"
    version: str = "1"

    def __post_init__(
        self,
    ) -> None:
        if (
            len(
                self.shards
            )
            > MAX_SHARDS
        ):
            raise ShardIRError(
                "program shard bound exceeded"
            )

        if (
            len(
                self.segues
            )
            > MAX_SEGUES
        ):
            raise ShardIRError(
                "program segue bound exceeded"
            )

        object.__setattr__(
            self,
            "source_format",
            _token(
                self.source_format,
                "source format",
            ),
        )

        object.__setattr__(
            self,
            "language",
            _token(
                self.language,
                "language",
            ),
        )

        object.__setattr__(
            self,
            "version",
            _token(
                self.version,
                "version",
            ),
        )

        shard_ids = [
            item.id
            for item
            in self.shards
        ]

        if (
            len(
                shard_ids
            )
            != len(
                set(
                    shard_ids
                )
            )
        ):
            raise ShardIRError(
                "duplicate runtime "
                "shard identity"
            )

        segue_ids = [
            item.id
            for item
            in self.segues
        ]

        if (
            len(
                segue_ids
            )
            != len(
                set(
                    segue_ids
                )
            )
        ):
            raise ShardIRError(
                "duplicate segue "
                "shard identity"
            )

        known = set(
            shard_ids
        )

        for segue in self.segues:
            if (
                segue.origin
                not in known
                or segue.destination
                not in known
            ):
                raise ShardIRError(
                    "segue endpoints must "
                    "resolve to runtime shards "
                    "in the same program"
                )

    def semantic_primitive(
        self,
    ) -> dict[str, Any]:
        return {
            "schema":
                PROGRAM_SCHEMA,

            "language":
                self.language,

            "source_format":
                self.source_format,

            "version":
                self.version,

            "shards":
                [
                    item.primitive()
                    for item
                    in self.shards
                ],

            "segues":
                [
                    item.primitive()
                    for item
                    in self.segues
                ],

            "authority_effect":
                AUTHORITY_EFFECT,
        }

    @property
    def semantic_digest(
        self,
    ) -> str:
        return digest(
            self.semantic_primitive()
        )

    def primitive(
        self,
    ) -> dict[str, Any]:
        out = (
            self.semantic_primitive()
        )

        out["semantic_digest"] = (
            self.semantic_digest
        )

        out["counts"] = {
            "shards":
                len(
                    self.shards
                ),

            "segues":
                len(
                    self.segues
                ),
        }

        return out

    def shard(
        self,
        shard_id: str,
    ) -> RuntimeShard:
        for item in self.shards:
            if (
                item.id
                == shard_id
            ):
                return item

        raise ShardIRError(
            "unknown runtime shard: "
            f"{shard_id}"
        )

    def outgoing(
        self,
        shard_id: str,
    ) -> tuple[
        SegueShard,
        ...,
    ]:
        self.shard(
            shard_id
        )

        return tuple(
            item
            for item
            in self.segues
            if (
                item.origin
                == shard_id
            )
        )

    def incoming(
        self,
        shard_id: str,
    ) -> tuple[
        SegueShard,
        ...,
    ]:
        self.shard(
            shard_id
        )

        return tuple(
            item
            for item
            in self.segues
            if (
                item.destination
                == shard_id
            )
        )


def substantiate_shard(
    *,
    kind: str,
    source_identity: str,
    source_digest: str,
    payload: Mapping[
        str,
        Any,
    ] | None = None,
    owner: str = "translucent",
    plane: str = "execution",
    dependencies: Sequence[str] = (),
    lineage: Sequence[str] = (),
    provenance: Sequence[str] = (),
    authority_witness: Sequence[str] = (),
    truth: Mapping[
        str,
        Any,
    ] | None = None,
    capabilities: Sequence[str] = (),
    ordinal: int = 0,
) -> RuntimeShard:
    return RuntimeShard(
        kind=kind,

        source=SourceWitness(
            identity=
                source_identity,

            digest=
                source_digest,

            lineage=
                tuple(
                    lineage
                ),

            provenance=
                tuple(
                    provenance
                ),

            authority_witness=
                tuple(
                    authority_witness
                ),
        ),

        payload=
            payload
            or {},

        owner=
            owner,

        plane=
            plane,

        dependencies=
            tuple(
                dependencies
            ),

        truth=
            truth
            or {},

        capabilities=
            tuple(
                capabilities
            ),

        ordinal=
            ordinal,
    )


def substantiate_segue(
    *,
    kind: str,
    source_identity: str,
    source_digest: str,
    origin: str,
    destination: str,
    payload: Mapping[
        str,
        Any,
    ] | None = None,
    owner: str = "translucent",
    dependencies: Sequence[str] = (),
    lineage: Sequence[str] = (),
    provenance: Sequence[str] = (),
    authority_witness: Sequence[str] = (),
    truth: Mapping[
        str,
        Any,
    ] | None = None,
    ordinal: int = 0,
) -> SegueShard:
    return SegueShard(
        kind=
            kind,

        source=
            SourceWitness(
                identity=
                    source_identity,

                digest=
                    source_digest,

                lineage=
                    tuple(
                        lineage
                    ),

                provenance=
                    tuple(
                        provenance
                    ),

                authority_witness=
                    tuple(
                        authority_witness
                    ),
            ),

        origin=
            origin,

        destination=
            destination,

        payload=
            payload
            or {},

        owner=
            owner,

        dependencies=
            tuple(
                dependencies
            ),

        truth=
            truth
            or {},

        ordinal=
            ordinal,
    )


def manifest() -> dict[str, Any]:
    return {
        "schema":
            SCHEMA,

        "owner":
            "translucent",

        "authority_effect":
            AUTHORITY_EFFECT,

        "canonical_source_authority":
            False,

        "runtime_projection":
            True,

        "source_extensions":
            [
                ".lucid",
                ".nimble",
            ],

        "object_classes":
            [
                "shard",
                "segue-shard",
            ],

        "invariants":
            [
                (
                    "canonical instances "
                    "remain authoritative"
                ),
                (
                    "runtime shards never "
                    "replace canonical identity"
                ),
                (
                    "every executable object "
                    "is a typed runtime shard"
                ),
                (
                    "every executable transition "
                    "or relation is a segue shard"
                ),
                (
                    "source identity and digest "
                    "are mandatory"
                ),
                (
                    "lineage provenance authority "
                    "witness truth and dependencies "
                    "survive projection"
                ),
                (
                    "semantic identity excludes "
                    "incidental execution state"
                ),
                (
                    "derived runtime state "
                    "is rebuildable"
                ),
            ],

        "limits":
            {
                "shards":
                    MAX_SHARDS,

                "segues":
                    MAX_SEGUES,

                "payload_bytes":
                    MAX_PAYLOAD_BYTES,

                "value_depth":
                    MAX_DEPTH,
            },
    }


def selftest() -> dict[str, Any]:
    source_digest = hashlib.sha256(
        b"canonical-instance"
    ).hexdigest()

    a = substantiate_shard(
        kind=
            "invoke",

        source_identity=
            "shade:demo:a",

        source_digest=
            source_digest,

        payload=
            {
                "verb":
                    "project",

                "value":
                    7,
            },

        provenance=
            (
                "source:demo",
            ),

        authority_witness=
            (
                "authority:demo",
            ),

        truth=
            {
                "state":
                    "supported",
            },
    )

    b = substantiate_shard(
        kind=
            "project",

        source_identity=
            "shade:demo:b",

        source_digest=
            source_digest,

        payload=
            {
                "target":
                    "blot",
            },

        dependencies=
            (
                a.id,
            ),

        ordinal=
            1,
    )

    segue = substantiate_segue(
        kind=
            "flow",

        source_identity=
            "segue:demo:flow",

        source_digest=
            source_digest,

        origin=
            a.id,

        destination=
            b.id,

        payload=
            {
                "mode":
                    "typed",
            },
    )

    program = ShardProgram(
        (
            a,
            b,
        ),
        (
            segue,
        ),
    )

    program_again = ShardProgram(
        (
            a,
            b,
        ),
        (
            segue,
        ),
    )

    checks = {
        "authority_none":
            (
                manifest()[
                    "authority_effect"
                ]
                == "none"
            ),

        "canonical_not_replaced":
            (
                manifest()[
                    "canonical_source_authority"
                ]
                is False
            ),

        "runtime_projection":
            (
                manifest()[
                    "runtime_projection"
                ]
                is True
            ),

        "typed_shard":
            (
                a.kind
                == "invoke"
            ),

        "typed_segue_shard":
            (
                segue.kind
                == "flow"
            ),

        "source_identity_preserved":
            (
                a.source.identity
                == "shade:demo:a"
            ),

        "source_digest_preserved":
            (
                a.source.digest
                == source_digest
            ),

        "provenance_preserved":
            (
                a.source.provenance
                == (
                    "source:demo",
                )
            ),

        "authority_witness_preserved":
            (
                a.source.authority_witness
                == (
                    "authority:demo",
                )
            ),

        "truth_preserved":
            (
                a.truth[
                    "state"
                ]
                == "supported"
            ),

        "dependency_preserved":
            (
                b.dependencies
                == (
                    a.id,
                )
            ),

        "segue_resolves":
            (
                program.outgoing(
                    a.id
                )
                == (
                    segue,
                )
            ),

        "deterministic_shard_identity":
            (
                a.id
                == substantiate_shard(
                    kind=
                        "invoke",

                    source_identity=
                        "shade:demo:a",

                    source_digest=
                        source_digest,

                    payload=
                        {
                            "value":
                                7,

                            "verb":
                                "project",
                        },

                    provenance=
                        (
                            "source:demo",
                        ),

                    authority_witness=
                        (
                            "authority:demo",
                        ),

                    truth=
                        {
                            "state":
                                "supported",
                        },
                ).id
            ),

        "deterministic_program":
            (
                program.semantic_digest
                == program_again.semantic_digest
            ),

        "two_source_extensions":
            (
                manifest()[
                    "source_extensions"
                ]
                == [
                    ".lucid",
                    ".nimble",
                ]
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

        "digest":
            program.semantic_digest,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
