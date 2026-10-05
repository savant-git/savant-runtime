from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence


SCHEMA = "savant://noumenon/meaning-metabolism/1"

EPISTEMIC_CLASSES = frozenset(
    {
        "observed",
        "remembered",
        "believed",
        "interpreted",
        "inferred",
        "unknown",
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
class MeaningRevision:
    experience_ref: str
    predecessor_ref: str | None
    interpretation: str
    epistemic_class: str
    significance: Mapping[str, float]
    causal_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.experience_ref:
            raise ValueError(
                "experience_ref is required"
            )

        if not self.interpretation:
            raise ValueError(
                "interpretation is required"
            )

        if (
            self.epistemic_class
            not in EPISTEMIC_CLASSES
        ):
            raise ValueError(
                "unsupported epistemic_class"
            )

        for dimension, value in (
            self.significance.items()
        ):
            if not dimension:
                raise ValueError(
                    "significance dimension "
                    "is required"
                )

            numeric = float(value)

            if (
                numeric < -1.0
                or numeric > 1.0
            ):
                raise ValueError(
                    "significance values must "
                    "be between -1 and 1"
                )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "experience_ref": (
                self.experience_ref
            ),
            "predecessor_ref": (
                self.predecessor_ref
            ),
            "interpretation": (
                self.interpretation
            ),
            "epistemic_class": (
                self.epistemic_class
            ),
            "significance": {
                key: float(value)
                for key, value
                in sorted(
                    self.significance.items()
                )
            },
            "causal_refs": list(
                self.causal_refs
            ),
            "evidence_refs": list(
                self.evidence_refs
            ),
            "authority_refs": list(
                self.authority_refs
            ),
            "event_mutated": False,
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
            "noumenon-meaning:"
            + self.digest
        )


@dataclass(frozen=True, slots=True)
class MeaningHistory:
    experience_ref: str
    revisions: tuple[
        MeaningRevision,
        ...,
    ]

    def __post_init__(self) -> None:
        if not self.experience_ref:
            raise ValueError(
                "experience_ref is required"
            )

        known: set[str] = set()

        previous: str | None = None

        for revision in self.revisions:
            if (
                revision.experience_ref
                != self.experience_ref
            ):
                raise ValueError(
                    "meaning history cannot "
                    "mix experiences"
                )

            if (
                revision.predecessor_ref
                != previous
            ):
                raise ValueError(
                    "meaning revision lineage "
                    "is discontinuous"
                )

            if revision.id in known:
                raise ValueError(
                    "duplicate meaning revision"
                )

            known.add(
                revision.id
            )

            previous = revision.id

    @property
    def current(
        self,
    ) -> MeaningRevision | None:
        if not self.revisions:
            return None

        return self.revisions[-1]

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "experience_ref": (
                self.experience_ref
            ),
            "revisions": [
                revision.projection()
                for revision
                in self.revisions
            ],
            "current_ref": (
                self.current.id
                if self.current
                is not None
                else None
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def empty_history(
    experience_ref: str,
) -> MeaningHistory:
    return MeaningHistory(
        experience_ref=experience_ref,
        revisions=(),
    )


def revise_meaning(
    history: MeaningHistory,
    *,
    interpretation: str,
    epistemic_class: str,
    significance: Mapping[
        str,
        float,
    ],
    causal_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    authority_refs: Sequence[str] = (),
) -> MeaningHistory:
    predecessor = history.current

    revision = MeaningRevision(
        experience_ref=(
            history.experience_ref
        ),
        predecessor_ref=(
            predecessor.id
            if predecessor is not None
            else None
        ),
        interpretation=interpretation,
        epistemic_class=(
            epistemic_class
        ),
        significance=dict(
            significance
        ),
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

    return MeaningHistory(
        experience_ref=(
            history.experience_ref
        ),
        revisions=(
            *history.revisions,
            revision,
        ),
    )


def significance_delta(
    predecessor: MeaningRevision | None,
    successor: MeaningRevision,
) -> Mapping[str, float]:
    before = (
        predecessor.significance
        if predecessor is not None
        else {}
    )

    dimensions = (
        set(before)
        | set(successor.significance)
    )

    return {
        dimension: (
            float(
                successor.significance.get(
                    dimension,
                    0.0,
                )
            )
            - float(
                before.get(
                    dimension,
                    0.0,
                )
            )
        )
        for dimension
        in sorted(dimensions)
    }


def metabolism_projection(
    history: MeaningHistory,
) -> Mapping[str, Any]:
    current = history.current

    predecessor = (
        history.revisions[-2]
        if len(history.revisions) > 1
        else None
    )

    return {
        "schema": SCHEMA,
        "experience_ref": (
            history.experience_ref
        ),
        "current_ref": (
            current.id
            if current is not None
            else None
        ),
        "revision_count": len(
            history.revisions
        ),
        "significance_delta": (
            significance_delta(
                predecessor,
                current,
            )
            if current is not None
            else {}
        ),
        "event_mutated": False,
        "derived": True,
        "authoritative": False,
    }
