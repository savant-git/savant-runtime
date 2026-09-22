from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/residue/1"

RESIDUE_KINDS = frozenset(
    {
        "developmental",
        "moral",
        "relational",
        "commitment",
        "wound",
        "gratitude",
        "contradiction",
    }
)


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class Residue:
    kind: str
    dimension: str
    magnitude: float
    causal_refs: tuple[str, ...]
    resolved: bool = False
    resolution_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in RESIDUE_KINDS:
            raise ValueError(
                "unsupported residue kind"
            )

        if not self.dimension:
            raise ValueError(
                "dimension is required"
            )

        if not (
            0.0
            <= float(self.magnitude)
            <= 1.0
        ):
            raise ValueError(
                "magnitude must be between "
                "0 and 1"
            )

        if not self.causal_refs:
            raise ValueError(
                "causal_refs are required"
            )

        if (
            self.resolved
            and not self.resolution_refs
        ):
            raise ValueError(
                "resolved residue requires "
                "resolution_refs"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "kind": self.kind,
            "dimension": self.dimension,
            "magnitude": float(
                self.magnitude
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "resolved": self.resolved,
            "resolution_refs": list(
                self.resolution_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "authority_effect": "none",
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-residue:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class ResidueLedger:
    noumenon_id: str
    entries: tuple[
        Residue,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        identifiers = [
            entry.id
            for entry in self.entries
        ]

        if (
            len(identifiers)
            != len(set(identifiers))
        ):
            raise ValueError(
                "duplicate residue entry"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": (
                self.noumenon_id
            ),
            "entries": [
                entry.projection()
                for entry in self.entries
            ],
            "active_refs": [
                entry.id
                for entry in self.entries
                if not entry.resolved
            ],
            "resolved_refs": [
                entry.id
                for entry in self.entries
                if entry.resolved
            ],
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def empty_ledger(
    noumenon_id: str,
) -> ResidueLedger:
    return ResidueLedger(
        noumenon_id=noumenon_id
    )


def add_residue(
    ledger: ResidueLedger,
    *,
    kind: str,
    dimension: str,
    magnitude: float,
    causal_refs: Sequence[str],
    evidence_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
) -> ResidueLedger:
    residue = Residue(
        kind=kind,
        dimension=dimension,
        magnitude=magnitude,
        causal_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in causal_refs
            )
        ),
        evidence_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in evidence_refs
            )
        ),
        authority_refs=tuple(
            dict.fromkeys(
                str(value)
                for value in authority_refs
            )
        ),
    )

    if any(
        entry.id == residue.id
        for entry in ledger.entries
    ):
        return ledger

    return ResidueLedger(
        noumenon_id=ledger.noumenon_id,
        entries=(
            *ledger.entries,
            residue,
        ),
    )


def resolve_residue(
    ledger: ResidueLedger,
    residue_id: str,
    *,
    resolution_refs: Sequence[str],
) -> ResidueLedger:
    refs = tuple(
        dict.fromkeys(
            str(value)
            for value in resolution_refs
        )
    )

    if not refs:
        raise ValueError(
            "resolution_refs are required"
        )

    found = False
    entries: list[Residue] = []

    for entry in ledger.entries:
        if entry.id != residue_id:
            entries.append(entry)
            continue

        found = True

        if entry.resolved:
            entries.append(entry)
            continue

        entries.append(
            Residue(
                kind=entry.kind,
                dimension=entry.dimension,
                magnitude=entry.magnitude,
                causal_refs=entry.causal_refs,
                resolved=True,
                resolution_refs=refs,
                evidence_refs=(
                    entry.evidence_refs
                ),
                authority_refs=(
                    entry.authority_refs
                ),
            )
        )

    if not found:
        raise KeyError(
            residue_id
        )

    return ResidueLedger(
        noumenon_id=ledger.noumenon_id,
        entries=tuple(entries),
    )


def active_residue(
    ledger: ResidueLedger,
    *,
    kind: str | None = None,
    dimension: str | None = None,
) -> tuple[Residue, ...]:
    return tuple(
        entry
        for entry in ledger.entries
        if not entry.resolved
        and (
            kind is None
            or entry.kind == kind
        )
        and (
            dimension is None
            or entry.dimension
            == dimension
        )
    )


def residue_pressure(
    ledger: ResidueLedger,
    *,
    kind: str | None = None,
    dimension: str | None = None,
) -> float:
    return sum(
        float(entry.magnitude)
        for entry in active_residue(
            ledger,
            kind=kind,
            dimension=dimension,
        )
    )


def residue_projection(
    ledger: ResidueLedger,
) -> Mapping[str, Any]:
    active = active_residue(
        ledger
    )

    by_kind: dict[str, float] = {}
    by_dimension: dict[str, float] = {}

    for entry in active:
        by_kind[entry.kind] = (
            by_kind.get(
                entry.kind,
                0.0,
            )
            + float(entry.magnitude)
        )

        by_dimension[
            entry.dimension
        ] = (
            by_dimension.get(
                entry.dimension,
                0.0,
            )
            + float(entry.magnitude)
        )

    return {
        "schema": SCHEMA,
        "noumenon_id": (
            ledger.noumenon_id
        ),
        "active_count": len(active),
        "resolved_count": (
            len(ledger.entries)
            - len(active)
        ),
        "pressure_by_kind": {
            key: by_kind[key]
            for key in sorted(by_kind)
        },
        "pressure_by_dimension": {
            key: by_dimension[key]
            for key
            in sorted(by_dimension)
        },
        "derived": True,
        "authoritative": False,
    }
