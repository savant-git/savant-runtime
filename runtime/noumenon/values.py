from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/values/1"

VALUE_CLASSES = frozenset(
    {
        "professed",
        "observed",
        "aspirational",
        "inherited",
        "questioned",
        "rejected",
        "unresolved",
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
class ValueEvidence:
    value_ref: str
    value_class: str
    strength: float
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.value_ref:
            raise ValueError(
                "value_ref is required"
            )

        if (
            self.value_class
            not in VALUE_CLASSES
        ):
            raise ValueError(
                "unsupported value class"
            )

        if not (
            -1.0
            <= float(self.strength)
            <= 1.0
        ):
            raise ValueError(
                "strength must be between "
                "-1 and 1"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "value_ref": self.value_ref,
            "value_class": (
                self.value_class
            ),
            "strength": float(
                self.strength
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
            "noumenon-value-evidence:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class ValueProfile:
    noumenon_id: str
    evidence: tuple[
        ValueEvidence,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not self.noumenon_id:
            raise ValueError(
                "noumenon_id is required"
            )

        identifiers = [
            item.id
            for item in self.evidence
        ]

        if (
            len(identifiers)
            != len(set(identifiers))
        ):
            raise ValueError(
                "duplicate value evidence"
            )

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": (
                self.noumenon_id
            ),
            "evidence": [
                item.projection()
                for item in self.evidence
            ],
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def empty_profile(
    noumenon_id: str,
) -> ValueProfile:
    return ValueProfile(
        noumenon_id=noumenon_id
    )


def add_value_evidence(
    profile: ValueProfile,
    *,
    value_ref: str,
    value_class: str,
    strength: float,
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
) -> ValueProfile:
    item = ValueEvidence(
        value_ref=value_ref,
        value_class=value_class,
        strength=strength,
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
        existing.id == item.id
        for existing in profile.evidence
    ):
        return profile

    return ValueProfile(
        noumenon_id=(
            profile.noumenon_id
        ),
        evidence=(
            *profile.evidence,
            item,
        ),
    )


def value_classes(
    profile: ValueProfile,
    value_ref: str,
) -> Mapping[str, float]:
    grouped: dict[
        str,
        list[float],
    ] = {}

    for item in profile.evidence:
        if item.value_ref != value_ref:
            continue

        grouped.setdefault(
            item.value_class,
            [],
        ).append(
            float(item.strength)
        )

    return {
        value_class: (
            sum(values)
            / len(values)
        )
        for value_class, values
        in sorted(grouped.items())
    }


def revealed_value(
    profile: ValueProfile,
    value_ref: str,
) -> float | None:
    observed = tuple(
        float(item.strength)
        for item in profile.evidence
        if item.value_ref == value_ref
        and item.value_class
        == "observed"
    )

    if not observed:
        return None

    return (
        sum(observed)
        / len(observed)
    )


def professed_value(
    profile: ValueProfile,
    value_ref: str,
) -> float | None:
    professed = tuple(
        float(item.strength)
        for item in profile.evidence
        if item.value_ref == value_ref
        and item.value_class
        == "professed"
    )

    if not professed:
        return None

    return (
        sum(professed)
        / len(professed)
    )


def value_discrepancy(
    profile: ValueProfile,
    value_ref: str,
) -> float | None:
    professed = professed_value(
        profile,
        value_ref,
    )

    observed = revealed_value(
        profile,
        value_ref,
    )

    if (
        professed is None
        or observed is None
    ):
        return None

    return (
        observed - professed
    )


def value_projection(
    profile: ValueProfile,
    value_ref: str,
) -> Mapping[str, Any]:
    classes = value_classes(
        profile,
        value_ref,
    )

    professed = professed_value(
        profile,
        value_ref,
    )

    observed = revealed_value(
        profile,
        value_ref,
    )

    discrepancy = value_discrepancy(
        profile,
        value_ref,
    )

    return {
        "schema": SCHEMA,
        "noumenon_id": (
            profile.noumenon_id
        ),
        "value_ref": value_ref,
        "classes": dict(classes),
        "professed": professed,
        "revealed": observed,
        "discrepancy": discrepancy,
        "contradiction": (
            discrepancy is not None
            and abs(discrepancy) > 0.0
        ),
        "derived": True,
        "authoritative": False,
    }
