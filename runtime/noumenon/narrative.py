from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/self-narrative/1"

NARRATIVE_CLASSES = frozenset(
    {
        "continuity",
        "growth",
        "rupture",
        "repair",
        "conflict",
        "reinterpretation",
        "uncertain",
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
class NarrativeClaim:
    claim_ref: str
    narrative_class: str
    statement: str
    confidence: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim_ref:
            raise ValueError(
                "claim_ref is required"
            )

        if (
            self.narrative_class
            not in NARRATIVE_CLASSES
        ):
            raise ValueError(
                "unsupported narrative class"
            )

        if not self.statement:
            raise ValueError(
                "statement is required"
            )

        if not (
            0.0
            <= float(self.confidence)
            <= 1.0
        ):
            raise ValueError(
                "confidence must be between "
                "0 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "claim_ref": self.claim_ref,
            "narrative_class": (
                self.narrative_class
            ),
            "statement": self.statement,
            "confidence": float(
                self.confidence
            ),
            "causal_refs": list(
                self.causal_refs
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
            "noumenon-narrative-claim:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class NarrativeLayer:
    sequence: int
    claims: tuple[NarrativeClaim, ...]
    predecessor_ref: str | None = None
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError(
                "sequence cannot be negative"
            )

        if (
            self.sequence > 0
            and not self.predecessor_ref
        ):
            raise ValueError(
                "non-genesis narrative layer "
                "requires predecessor"
            )

        claim_ids = tuple(
            claim.id
            for claim in self.claims
        )

        if len(claim_ids) != len(
            set(claim_ids)
        ):
            raise ValueError(
                "duplicate narrative claims"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "sequence": self.sequence,
            "claims": [
                claim.projection()
                for claim in self.claims
            ],
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "causal_refs": list(
                self.causal_refs
            ),
            "derived": True,
            "authoritative": False,
        }

    @property
    def digest(self) -> str:
        return _digest(
            self.projection()
        )

    @property
    def id(self) -> str:
        return (
            "noumenon-narrative-layer:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class SelfNarrative:
    noumenon_id: str
    layers: tuple[NarrativeLayer, ...]

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        if not self.layers:
            raise ValueError(
                "narrative requires layers"
            )

        previous: NarrativeLayer | None = (
            None
        )

        for layer in self.layers:
            if previous is None:
                if layer.sequence != 0:
                    raise ValueError(
                        "narrative must begin "
                        "at sequence zero"
                    )
            else:
                if (
                    layer.sequence
                    != previous.sequence + 1
                ):
                    raise ValueError(
                        "narrative sequence "
                        "discontinuity"
                    )

                if (
                    layer.predecessor_ref
                    != previous.id
                ):
                    raise ValueError(
                        "narrative lineage "
                        "discontinuity"
                    )

            previous = layer

    @property
    def current(
        self,
    ) -> NarrativeLayer:
        return self.layers[-1]

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "noumenon_id": self.noumenon_id,
            "layers": [
                layer.projection()
                for layer in self.layers
            ],
            "current_ref": self.current.id,
            "history_erased": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class NarrativeDrift:
    predecessor_ref: str
    successor_ref: str
    retained_claim_refs: tuple[str, ...]
    added_claim_refs: tuple[str, ...]
    omitted_claim_refs: tuple[str, ...]
    contradiction_pairs: tuple[
        tuple[str, str],
        ...
    ]

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "successor_ref": (
                self.successor_ref
            ),
            "retained_claim_refs": list(
                self.retained_claim_refs
            ),
            "added_claim_refs": list(
                self.added_claim_refs
            ),
            "omitted_claim_refs": list(
                self.omitted_claim_refs
            ),
            "contradiction_pairs": [
                list(pair)
                for pair
                in self.contradiction_pairs
            ],
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def establish_narrative(
    noumenon_id: str,
    claims: Sequence[NarrativeClaim],
    *,
    causal_refs: Sequence[str] = (),
) -> SelfNarrative:
    layer = NarrativeLayer(
        sequence=0,
        claims=tuple(claims),
        causal_refs=tuple(
            dict.fromkeys(
                causal_refs
            )
        ),
    )

    return SelfNarrative(
        noumenon_id=noumenon_id,
        layers=(layer,),
    )


def revise_narrative(
    narrative: SelfNarrative,
    claims: Sequence[NarrativeClaim],
    *,
    causal_refs: Sequence[str],
) -> SelfNarrative:
    if not causal_refs:
        raise ValueError(
            "narrative revision requires "
            "causal refs"
        )

    predecessor = narrative.current

    successor = NarrativeLayer(
        sequence=(
            predecessor.sequence + 1
        ),
        claims=tuple(claims),
        predecessor_ref=predecessor.id,
        causal_refs=tuple(
            dict.fromkeys(
                (
                    *predecessor.causal_refs,
                    *causal_refs,
                )
            )
        ),
    )

    return SelfNarrative(
        noumenon_id=narrative.noumenon_id,
        layers=(
            *narrative.layers,
            successor,
        ),
    )


def narrative_drift(
    predecessor: NarrativeLayer,
    successor: NarrativeLayer,
    *,
    contradiction_pairs: Sequence[
        tuple[str, str]
    ] = (),
) -> NarrativeDrift:
    if (
        successor.predecessor_ref
        != predecessor.id
    ):
        raise ValueError(
            "narrative layers are not "
            "successive"
        )

    before = {
        claim.claim_ref: claim
        for claim in predecessor.claims
    }

    after = {
        claim.claim_ref: claim
        for claim in successor.claims
    }

    retained = tuple(
        sorted(
            set(before)
            & set(after)
        )
    )

    added = tuple(
        sorted(
            set(after)
            - set(before)
        )
    )

    omitted = tuple(
        sorted(
            set(before)
            - set(after)
        )
    )

    known = (
        set(before)
        | set(after)
    )

    normalized_pairs: list[
        tuple[str, str]
    ] = []

    for left, right in (
        contradiction_pairs
    ):
        if (
            left not in known
            or right not in known
        ):
            raise ValueError(
                "contradiction references "
                "unknown claim"
            )

        normalized_pairs.append(
            tuple(
                sorted(
                    (
                        left,
                        right,
                    )
                )
            )
        )

    return NarrativeDrift(
        predecessor_ref=predecessor.id,
        successor_ref=successor.id,
        retained_claim_refs=retained,
        added_claim_refs=added,
        omitted_claim_refs=omitted,
        contradiction_pairs=tuple(
            sorted(
                set(normalized_pairs)
            )
        ),
    )


def autobiographical_compression(
    narrative: SelfNarrative,
) -> Mapping[str, Any]:
    latest: dict[
        str,
        NarrativeClaim,
    ] = {}

    appearances: dict[
        str,
        int,
    ] = {}

    for layer in narrative.layers:
        for claim in layer.claims:
            latest[
                claim.claim_ref
            ] = claim

            appearances[
                claim.claim_ref
            ] = (
                appearances.get(
                    claim.claim_ref,
                    0,
                )
                + 1
            )

    ordered = sorted(
        latest.values(),
        key=lambda claim: (
            -appearances[
                claim.claim_ref
            ],
            -claim.confidence,
            claim.claim_ref,
        ),
    )

    return {
        "schema": SCHEMA,
        "noumenon_id": (
            narrative.noumenon_id
        ),
        "claims": [
            {
                **claim.projection(),
                "appearances": (
                    appearances[
                        claim.claim_ref
                    ]
                ),
            }
            for claim in ordered
        ],
        "source_layer_refs": [
            layer.id
            for layer in narrative.layers
        ],
        "compression_erased_history": False,
        "compression_is_authority": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }


def narrative_projection(
    narrative: SelfNarrative,
) -> Mapping[str, Any]:
    return {
        **narrative.projection(),
        "compression": (
            autobiographical_compression(
                narrative
            )
        ),
        "self_description_is_causal_truth": (
            False
        ),
        "contradictions_may_persist": True,
        "reinterpretation_erases_history": (
            False
        ),
    }
