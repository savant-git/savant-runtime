#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


OWNER = "exile:envoy"

SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-history/1.0.0"
)

PROJECTION_SCHEMA = (
    "savant://envoy/"
    "orobouros-accepted-trait-projection/1.0.0"
)

SUPPORTED_DECISIONS = {
    "establish_champion",
    "retain_champion",
    "challenge_wins",
    "no_decision",
}


class TraitHistoryError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
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


def normalize_text(
    value: Any,
) -> str:
    return str(
        value
        or ""
    ).strip()


def normalize_term(
    value: Any,
) -> str:
    return (
        normalize_text(
            value
        )
        .lower()
        .replace(
            "-",
            "_",
        )
        .replace(
            " ",
            "_",
        )
    )


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalized
                for value
                in values
                if (
                    normalized
                    := normalize_text(
                        value
                    )
                )
            }
        )
    )


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TraitHistoryError(
            f"{name} must be a mapping"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class HistoryRecord:
    sequence: int
    decision_id: str
    trait_id: str
    policy_id: str
    previous_champion_id: str | None
    winner_candidate_id: str | None
    decision: str
    decision_digest: str
    evidence_ids: tuple[str, ...]
    lineage: tuple[str, ...]

    def __post_init__(
        self,
    ) -> None:
        sequence = int(
            self.sequence
        )

        if sequence < 1:
            raise TraitHistoryError(
                "history sequence must "
                "be positive"
            )

        decision_id = normalize_text(
            self.decision_id
        )

        trait_id = normalize_term(
            self.trait_id
        )

        policy_id = normalize_term(
            self.policy_id
        )

        decision = normalize_term(
            self.decision
        )

        decision_digest = (
            normalize_text(
                self.decision_digest
            )
        )

        if not decision_id:
            raise TraitHistoryError(
                "decision_id is required"
            )

        if not trait_id:
            raise TraitHistoryError(
                "trait_id is required"
            )

        if not policy_id:
            raise TraitHistoryError(
                "policy_id is required"
            )

        if (
            decision
            not in SUPPORTED_DECISIONS
        ):
            raise TraitHistoryError(
                "unsupported adjudication "
                f"decision: {decision}"
            )

        if not decision_digest:
            raise TraitHistoryError(
                "decision_digest is required"
            )

        previous = (
            normalize_text(
                self.previous_champion_id
            )
            or None
        )

        winner = (
            normalize_text(
                self.winner_candidate_id
            )
            or None
        )

        if (
            decision
            == "no_decision"
            and winner is not None
        ):
            raise TraitHistoryError(
                "no_decision cannot have "
                "a winner"
            )

        if (
            decision
            in {
                "establish_champion",
                "retain_champion",
                "challenge_wins",
            }
            and winner is None
        ):
            raise TraitHistoryError(
                "champion decision requires "
                "a winner"
            )

        if (
            decision
            == "establish_champion"
            and previous is not None
        ):
            raise TraitHistoryError(
                "establish_champion cannot "
                "declare a previous champion"
            )

        if (
            decision
            == "retain_champion"
            and previous != winner
        ):
            raise TraitHistoryError(
                "retain_champion winner must "
                "equal previous champion"
            )

        if (
            decision
            == "challenge_wins"
            and (
                previous is None
                or previous == winner
            )
        ):
            raise TraitHistoryError(
                "challenge_wins requires "
                "a distinct previous champion"
            )

        object.__setattr__(
            self,
            "sequence",
            sequence,
        )

        object.__setattr__(
            self,
            "decision_id",
            decision_id,
        )

        object.__setattr__(
            self,
            "trait_id",
            trait_id,
        )

        object.__setattr__(
            self,
            "policy_id",
            policy_id,
        )

        object.__setattr__(
            self,
            "decision",
            decision,
        )

        object.__setattr__(
            self,
            "decision_digest",
            decision_digest,
        )

        object.__setattr__(
            self,
            "previous_champion_id",
            previous,
        )

        object.__setattr__(
            self,
            "winner_candidate_id",
            winner,
        )

        object.__setattr__(
            self,
            "evidence_ids",
            normalize_terms(
                self.evidence_ids
            ),
        )

        object.__setattr__(
            self,
            "lineage",
            normalize_terms(
                self.lineage
            ),
        )

    @property
    def record_id(
        self,
    ) -> str:
        return (
            "trait-history:"
            + digest(
                self.projection(
                    include_digest=False
                )
            )[:32]
        )

    def projection(
        self,
        *,
        include_digest: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "record_id": (
                self.record_id
                if include_digest
                else None
            ),
            "sequence": (
                self.sequence
            ),
            "decision_id": (
                self.decision_id
            ),
            "trait_id": (
                self.trait_id
            ),
            "policy_id": (
                self.policy_id
            ),
            "previous_champion_id": (
                self.previous_champion_id
            ),
            "winner_candidate_id": (
                self.winner_candidate_id
            ),
            "decision": (
                self.decision
            ),
            "decision_digest": (
                self.decision_digest
            ),
            "evidence_ids": list(
                self.evidence_ids
            ),
            "lineage": list(
                self.lineage
            ),
            "owner": OWNER,
            "authoritative": False,
            "authority_effect": "none",
            "immutable": True,
            "rebuildable": True,
        }

        if not include_digest:
            payload.pop(
                "record_id",
                None,
            )

            return payload

        payload["digest"] = digest(
            {
                key: value
                for key, value
                in payload.items()
                if key != "digest"
            }
        )

        return payload


def record_from_decision(
    decision_projection: Mapping[
        str,
        Any,
    ],
    *,
    sequence: int,
) -> HistoryRecord:
    decision = require_mapping(
        decision_projection,
        "decision_projection",
    )

    if (
        decision.get(
            "authoritative"
        )
        is not False
    ):
        raise TraitHistoryError(
            "adjudication decision must "
            "remain non-authoritative"
        )

    if (
        normalize_text(
            decision.get(
                "authority_effect"
            )
        )
        != "none"
    ):
        raise TraitHistoryError(
            "adjudication decision changed "
            "authority"
        )

    decision_id = normalize_text(
        decision.get(
            "decision_id"
        )
    )

    decision_digest = normalize_text(
        decision.get(
            "digest"
        )
    )

    if not decision_id:
        raise TraitHistoryError(
            "decision projection lacks "
            "decision_id"
        )

    if not decision_digest:
        raise TraitHistoryError(
            "decision projection lacks digest"
        )

    return HistoryRecord(
        sequence=sequence,
        decision_id=decision_id,
        trait_id=normalize_term(
            decision.get(
                "trait_id"
            )
        ),
        policy_id=normalize_term(
            decision.get(
                "policy_id"
            )
        ),
        previous_champion_id=(
            decision.get(
                "previous_champion_id"
            )
        ),
        winner_candidate_id=(
            decision.get(
                "winner_candidate_id"
            )
        ),
        decision=normalize_term(
            decision.get(
                "decision"
            )
        ),
        decision_digest=(
            decision_digest
        ),
        evidence_ids=tuple(
            decision.get(
                "evidence_ids"
            )
            or ()
        ),
        lineage=tuple(
            decision.get(
                "lineage"
            )
            or ()
        ),
    )


def validate_history(
    records: Sequence[
        HistoryRecord
    ],
) -> tuple[
    HistoryRecord,
    ...,
]:
    materialized = tuple(
        records
    )

    if not materialized:
        return ()

    ordered = tuple(
        sorted(
            materialized,
            key=lambda record: (
                record.sequence
            ),
        )
    )

    if (
        ordered
        != materialized
    ):
        raise TraitHistoryError(
            "history is not in canonical "
            "sequence order"
        )

    decision_ids: set[str] = set()
    record_ids: set[str] = set()

    champion_by_trait: dict[
        str,
        str | None,
    ] = {}

    for index, record in enumerate(
        ordered,
        start=1,
    ):
        if record.sequence != index:
            raise TraitHistoryError(
                "history sequence contains "
                "a gap or duplicate"
            )

        if (
            record.decision_id
            in decision_ids
        ):
            raise TraitHistoryError(
                "decision replay detected"
            )

        if (
            record.record_id
            in record_ids
        ):
            raise TraitHistoryError(
                "history record replay detected"
            )

        decision_ids.add(
            record.decision_id
        )

        record_ids.add(
            record.record_id
        )

        current = champion_by_trait.get(
            record.trait_id
        )

        if (
            record.previous_champion_id
            != current
        ):
            raise TraitHistoryError(
                "history lineage mismatch "
                f"for {record.trait_id}: "
                "declared previous champion "
                f"{record.previous_champion_id!r}, "
                f"derived {current!r}"
            )

        if (
            record.decision
            == "no_decision"
        ):
            continue

        champion_by_trait[
            record.trait_id
        ] = record.winner_candidate_id

    return ordered


def append_record(
    records: Sequence[
        HistoryRecord
    ],
    decision_projection: Mapping[
        str,
        Any,
    ],
) -> tuple[
    HistoryRecord,
    ...,
]:
    existing = validate_history(
        records
    )

    record = record_from_decision(
        decision_projection,
        sequence=(
            len(
                existing
            )
            + 1
        ),
    )

    combined = (
        *existing,
        record,
    )

    return validate_history(
        combined
    )


def current_champions(
    records: Sequence[
        HistoryRecord
    ],
) -> dict[
    str,
    str,
]:
    validated = validate_history(
        records
    )

    champions: dict[
        str,
        str,
    ] = {}

    for record in validated:
        if (
            record.decision
            == "no_decision"
        ):
            continue

        winner = (
            record.winner_candidate_id
        )

        if winner is None:
            raise TraitHistoryError(
                "champion decision lost winner"
            )

        champions[
            record.trait_id
        ] = winner

    return {
        trait_id: champions[
            trait_id
        ]
        for trait_id
        in sorted(
            champions
        )
    }


def accepted_trait_projection(
    records: Sequence[
        HistoryRecord
    ],
    candidates: Mapping[
        str,
        Mapping[
            str,
            Any,
        ],
    ],
) -> dict[str, Any]:
    validated = validate_history(
        records
    )

    champions = current_champions(
        validated
    )

    projected: list[
        dict[str, Any]
    ] = []

    dependencies: set[str] = set()

    for trait_id, candidate_id in (
        champions.items()
    ):
        if candidate_id not in candidates:
            raise TraitHistoryError(
                "accepted champion candidate "
                "is missing from candidate "
                f"catalog: {candidate_id}"
            )

        candidate = require_mapping(
            candidates[
                candidate_id
            ],
            (
                "candidate "
                + candidate_id
            ),
        )

        candidate_trait_id = (
            normalize_term(
                candidate.get(
                    "trait_id"
                )
            )
        )

        if candidate_trait_id != trait_id:
            raise TraitHistoryError(
                "candidate trait identity "
                "does not match history"
            )

        candidate_projection = dict(
            candidate
        )

        candidate_projection[
            "candidate_id"
        ] = candidate_id

        candidate_projection[
            "trait_id"
        ] = trait_id

        projected.append(
            candidate_projection
        )

        dependencies.add(
            candidate_id
        )

    for record in validated:
        dependencies.add(
            record.decision_id
        )

        dependencies.update(
            record.evidence_ids
        )

    payload = {
        "schema": PROJECTION_SCHEMA,
        "owner": OWNER,
        "persona_id": "orobouros",
        "accepted_traits": projected,
        "champions": champions,
        "history_record_count": (
            len(
                validated
            )
        ),
        "dependencies": sorted(
            dependencies
        ),
        "baseline_mutated": False,
        "trait_pool_mutated": False,
        "persistent_state": False,
        "projection_only": True,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-history-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "append_only_model": True,
        "immutable_records": True,
        "deterministic_replay": True,
        "decision_replay_rejected": True,
        "lineage_continuity_required": True,
        "no_decision_preserves_champion": (
            True
        ),
        "accepted_traits_derived": True,
        "baseline_mutation": False,
        "trait_pool_mutation": False,
        "persistent_state": False,
        "persistence_owner_required": (
            "coda"
        ),
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def main() -> int:
    print(
        json.dumps(
            status(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
