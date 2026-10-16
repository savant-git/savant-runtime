from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/integrant-envelope/2"

ALLOWED_SYSTEMS = frozenset(
    {
        "carbon",
        "coda",
        "envoy",
        "guise",
        "memory",
        "notary",
        "noumenon",
        "opus",
        "orobouros",
        "palaver",
        "rapport",
        "underscore",
    }
)

DIRECTIONS = frozenset(
    {
        "consume",
        "emit",
        "request",
        "candidate",
    }
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class IntegrantEnvelope:
    source: str
    target: str
    contract: str
    direction: str
    payload: Mapping[str, Any]
    authority_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.source not in ALLOWED_SYSTEMS:
            raise ValueError(
                f"unsupported source system: "
                f"{self.source}"
            )

        if self.target not in ALLOWED_SYSTEMS:
            raise ValueError(
                f"unsupported target system: "
                f"{self.target}"
            )

        if self.source == self.target:
            raise ValueError(
                "integrant endpoints must differ"
            )

        if not self.contract:
            raise ValueError(
                "contract is required"
            )

        if self.direction not in DIRECTIONS:
            raise ValueError(
                "unsupported direction"
            )

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "integrant": "noumenon",
            "source": self.source,
            "target": self.target,
            "contract": self.contract,
            "direction": self.direction,
            "payload": dict(self.payload),
            "authority_refs": list(
                self.authority_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "lineage_refs": list(
                self.lineage_refs
            ),
            "provenance_refs": list(
                self.provenance_refs
            ),
            "authority_transfer": False,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-envelope:"
            + self.digest
        )


def envelope(
    source: str,
    target: str,
    contract: str,
    direction: str,
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return IntegrantEnvelope(
        source=source,
        target=target,
        contract=contract,
        direction=direction,
        payload=dict(payload),
        authority_refs=tuple(
            authority_refs
        ),
        evidence_refs=tuple(
            evidence_refs
        ),
        lineage_refs=tuple(
            lineage_refs
        ),
        provenance_refs=tuple(
            provenance_refs
        ),
    )


def consume(
    source: str,
    contract: str,
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return envelope(
        source,
        "noumenon",
        contract,
        "consume",
        payload,
        authority_refs=authority_refs,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        provenance_refs=provenance_refs,
    )


def emit(
    target: str,
    contract: str,
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return envelope(
        "noumenon",
        target,
        contract,
        "emit",
        payload,
        authority_refs=authority_refs,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        provenance_refs=provenance_refs,
    )


def request(
    target: str,
    contract: str,
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return envelope(
        "noumenon",
        target,
        contract,
        "request",
        payload,
        authority_refs=authority_refs,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        provenance_refs=provenance_refs,
    )


def candidate(
    source: str,
    contract: str,
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return envelope(
        source,
        "noumenon",
        contract,
        "candidate",
        payload,
        authority_refs=authority_refs,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        provenance_refs=provenance_refs,
    )
