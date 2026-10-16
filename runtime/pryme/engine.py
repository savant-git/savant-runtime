#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path("/root/savant-runtime")

DEFAULT_INSTANCE = (
    ROOT
    / "runtime/pryme/instances/system.json"
)

CANONICAL_STRUCTURE = (
    ROOT
    / "canon/structure/canonical_runtime_structure.json"
)


PRYME_PIPELINE = (
    "admission",
    "identity_resolution",
    "source_resolution",

    "authority_class_resolution",
    "precedence_resolution",
    "eligibility_resolution",

    "lineage_resolution",
    "provenance_resolution",
    "dependency_resolution",

    "supersession_resolution",
    "conflict_detection",
    "conflict_preservation",

    "candidate_ordering",
    "resolution_projection",
    "explanation_projection",

    "observability",
    "validation",
    "attestation",
)


PRYME_ABILITIES = (
    "authority_discovery",
    "authority_identity",
    "authority_fingerprinting",

    "authority_class_resolution",
    "precedence_projection",
    "authority_comparison",

    "lineage_resolution",
    "provenance_resolution",
    "dependency_context",

    "supersession_resolution",
    "conflict_detection",
    "conflict_preservation",

    "eligibility_resolution",
    "unresolved_preservation",
    "stable_candidate_ordering",

    "resolution_projection",
    "resolution_explanation",
    "resolution_receipt",
)


PRYME_HEALTH_DIMENSIONS = (
    "precedence_source",
    "authority_roots",
    "identity_integrity",

    "precedence_integrity",
    "supersession_integrity",
    "lineage_integrity",

    "provenance_integrity",
    "conflict_integrity",
    "authority_boundary",
)


PRYME_VALIDATION_DIMENSIONS = (
    "identity",
    "source",
    "authority_class",

    "precedence",
    "lineage",
    "provenance",

    "supersession",
    "conflict",
    "integration",
)


PRYME_PROJECTIONS = (
    "authority_record",
    "authority_index",
    "precedence_map",

    "authority_conflict",
    "authority_history",
    "authority_lineage",

    "authority_provenance",
    "authority_resolution",
    "authority_health",
)


class PrymeError(RuntimeError):
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


def normalized_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return (
        text
        if text
        else None
    )


def normalized_string_set(
    value: Any,
) -> frozenset[str]:
    if value is None:
        return frozenset()

    if isinstance(
        value,
        str,
    ):
        item = normalized_identifier(
            value
        )

        return (
            frozenset(
                (item,)
            )
            if item
            else frozenset()
        )

    if not isinstance(
        value,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return frozenset()

    result: set[str] = set()

    for item in value:
        normalized = (
            normalized_identifier(
                item
            )
        )

        if normalized:
            result.add(
                normalized
            )

    return frozenset(
        result
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AuthorityRecord:
    identity: str
    source: str
    kind: str
    status: str
    authority_class: str | None
    supersedes: frozenset[str]
    lineage: Any
    provenance: Any
    payload: dict[str, Any]
    fingerprint: str

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "identity":
                self.identity,
            "source":
                self.source,
            "kind":
                self.kind,
            "status":
                self.status,
            "authority_class":
                self.authority_class,
            "supersedes":
                sorted(
                    self.supersedes
                ),
            "lineage":
                self.lineage,
            "provenance":
                self.provenance,
            "fingerprint":
                self.fingerprint,
            "authoritative":
                False,
        }


class Pryme:
    schema = (
        "savant://runtime/"
        "pryme/1.1.0"
    )

    substrate_id = (
        "living:pryme"
    )

    def __init__(
        self,
        instance_path:
            Path = DEFAULT_INSTANCE,
    ) -> None:
        if not instance_path.is_absolute():
            raise PrymeError(
                "instance path must "
                "be absolute"
            )

        self.instance_path = (
            instance_path.resolve()
        )

        self.instance = (
            self._load_json(
                self.instance_path
            )
        )

        self._validate_instance()

        precedence_source = Path(
            self.instance[
                "precedence_source"
            ]
        )

        if not precedence_source.is_absolute():
            raise PrymeError(
                "precedence source "
                "must be absolute"
            )

        self.precedence_source = (
            precedence_source.resolve()
        )

        self.structure = (
            self._load_json(
                self.precedence_source
            )
        )

        self.precedence = (
            self._extract_precedence(
                self.structure
            )
        )

        if not self.precedence:
            raise PrymeError(
                "explicit canonical "
                "authority precedence "
                "is unavailable"
            )

        self._precedence_rank = {
            authority_class:
                index
            for index, authority_class
            in enumerate(
                self.precedence
            )
        }

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        if not path.is_file():
            raise PrymeError(
                f"missing file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise PrymeError(
                f"invalid JSON: {path}: "
                f"{exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise PrymeError(
                f"invalid object: {path}"
            )

        return payload

    @staticmethod
    def _extract_precedence(
        payload: dict[str, Any],
    ) -> tuple[str, ...]:
        candidates = (
            payload
            .get(
                "authority",
                {},
            )
            .get(
                "precedence"
            )
        )

        if not isinstance(
            candidates,
            list,
        ):
            return ()

        result: list[str] = []

        for candidate in candidates:
            if isinstance(
                candidate,
                str,
            ):
                name = candidate.strip()

            elif isinstance(
                candidate,
                dict,
            ):
                name = str(
                    candidate.get(
                        "authority_class",
                        candidate.get(
                            "id",
                            candidate.get(
                                "name",
                                "",
                            ),
                        ),
                    )
                ).strip()

            else:
                continue

            if (
                name
                and name not in result
            ):
                result.append(
                    name
                )

        return tuple(
            result
        )

    def _validate_instance(
        self,
    ) -> None:
        if (
            self.instance.get(
                "substrate"
            )
            != "pryme"
        ):
            raise PrymeError(
                "invalid Pryme substrate"
            )

        if (
            self.instance.get(
                "mutation_authorized"
            )
            is not False
        ):
            raise PrymeError(
                "Pryme mutation must "
                "remain disabled"
            )

        if (
            self.instance.get(
                "authority_manufacture_authorized"
            )
            is not False
        ):
            raise PrymeError(
                "Pryme may not "
                "manufacture authority"
            )

        resolution = (
            self.instance.get(
                "resolution",
                {},
            )
        )

        if len(resolution) != 9:
            raise PrymeError(
                "Pryme resolution overlay "
                "must contain 9 controls"
            )

        groups = (
            self.instance.get(
                "enhancement_groups",
                {},
            )
        )

        if len(groups) != 9:
            raise PrymeError(
                "Pryme requires "
                "9 enhancement groups"
            )

        for name, values in (
            groups.items()
        ):
            if (
                not isinstance(
                    values,
                    list,
                )
                or len(values) != 3
                or not all(
                    isinstance(
                        value,
                        str,
                    )
                    and value.strip()
                    for value in values
                )
            ):
                raise PrymeError(
                    f"{name} must contain "
                    "exactly 3 substantive "
                    "enhancements"
                )

    @property
    def enhancement_count(
        self,
    ) -> int:
        return sum(
            len(values)
            for values
            in self.instance[
                "enhancement_groups"
            ].values()
        )

    def precedence_rank(
        self,
        authority_class:
            str | None,
    ) -> int | None:
        if authority_class is None:
            return None

        return (
            self._precedence_rank
            .get(
                authority_class
            )
        )

    @staticmethod
    def _extract_authority_class(
        payload: dict[str, Any],
    ) -> str | None:
        authority = payload.get(
            "authority"
        )

        if isinstance(
            authority,
            dict,
        ):
            for key in (
                "authority_class",
                "class",
            ):
                value = (
                    normalized_identifier(
                        authority.get(
                            key
                        )
                    )
                )

                if value:
                    return value

        return normalized_identifier(
            payload.get(
                "authority_class"
            )
        )

    @staticmethod
    def _extract_supersedes(
        payload: dict[str, Any],
    ) -> frozenset[str]:
        direct = (
            normalized_string_set(
                payload.get(
                    "supersedes"
                )
            )
        )

        authority = payload.get(
            "authority"
        )

        if not isinstance(
            authority,
            dict,
        ):
            return direct

        nested = (
            normalized_string_set(
                authority.get(
                    "supersedes"
                )
            )
        )

        return (
            direct
            | nested
        )

    def load_record(
        self,
        path: Path,
    ) -> AuthorityRecord:
        if not path.is_absolute():
            raise PrymeError(
                "authority path must "
                "be absolute"
            )

        path = path.resolve()

        if not path.is_file():
            raise PrymeError(
                "missing authority "
                f"record: {path}"
            )

        suffix = (
            path.suffix.lower()
        )

        try:
            if suffix in (
                ".yaml",
                ".yml",
            ):
                payload = (
                    yaml.safe_load(
                        path.read_text(
                            encoding="utf-8"
                        )
                    )
                )

            elif suffix == ".json":
                payload = (
                    json.loads(
                        path.read_text(
                            encoding="utf-8"
                        )
                    )
                )

            else:
                raise PrymeError(
                    "unsupported authority "
                    "record format"
                )

        except (
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            raise PrymeError(
                f"invalid authority "
                f"record: {path}: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise PrymeError(
                "authority record must "
                "be an object"
            )

        identity = (
            normalized_identifier(
                payload.get(
                    "id"
                )
            )
        )

        if identity is None:
            raise PrymeError(
                "authority record lacks "
                "explicit identity"
            )

        authority_class = (
            self
            ._extract_authority_class(
                payload
            )
        )

        lineage = (
            payload.get(
                "lineage"
            )
        )

        provenance = (
            payload.get(
                "provenance"
            )
        )

        record_payload = dict(
            payload
        )

        return AuthorityRecord(
            identity=identity,
            source=str(path),
            kind=str(
                payload.get(
                    "kind",
                    "unknown",
                )
            ),
            status=str(
                payload.get(
                    "status",
                    "unknown",
                )
            ),
            authority_class=(
                authority_class
            ),
            supersedes=(
                self
                ._extract_supersedes(
                    payload
                )
            ),
            lineage=lineage,
            provenance=provenance,
            payload=record_payload,
            fingerprint=digest(
                record_payload
            ),
        )

    def discover(
        self,
    ) -> tuple[
        AuthorityRecord,
        ...,
    ]:
        discovered: list[
            AuthorityRecord
        ] = []

        seen: set[
            tuple[str, str]
        ] = set()

        for raw_root in (
            self.instance[
                "authority_roots"
            ]
        ):
            root = Path(
                raw_root
            )

            if not root.is_absolute():
                continue

            if not root.is_dir():
                continue

            for path in sorted(
                root.rglob("*"),
                key=lambda value:
                    str(value),
            ):
                if (
                    not path.is_file()
                    or path.suffix.lower()
                    not in (
                        ".json",
                        ".yaml",
                        ".yml",
                    )
                ):
                    continue

                try:
                    record = (
                        self.load_record(
                            path
                        )
                    )
                except PrymeError:
                    continue

                key = (
                    record.identity,
                    record.fingerprint,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                discovered.append(
                    record
                )

        discovered.sort(
            key=lambda record: (
                record.identity,
                record.fingerprint,
                record.source,
            )
        )

        return tuple(
            discovered
        )

    def _explicit_supersession(
        self,
        left: AuthorityRecord,
        right: AuthorityRecord,
    ) -> AuthorityRecord | None:
        left_supersedes = (
            right.identity
            in left.supersedes
        )

        right_supersedes = (
            left.identity
            in right.supersedes
        )

        if (
            left_supersedes
            and not right_supersedes
        ):
            return left

        if (
            right_supersedes
            and not left_supersedes
        ):
            return right

        return None

    def compare(
        self,
        left: AuthorityRecord,
        right: AuthorityRecord,
    ) -> dict[str, Any]:
        left_rank = (
            self.precedence_rank(
                left.authority_class
            )
        )

        right_rank = (
            self.precedence_rank(
                right.authority_class
            )
        )

        winner: (
            AuthorityRecord
            | None
        ) = None

        basis: (
            str
            | None
        ) = None

        unresolved_reason: (
            str
            | None
        ) = None

        if (
            left.fingerprint
            == right.fingerprint
        ):
            winner = left
            basis = (
                "identical-content"
            )

        elif (
            left_rank is None
            or right_rank is None
        ):
            unresolved_reason = (
                "one or more candidates "
                "lack an explicit recognized "
                "authority class"
            )

        elif left_rank < right_rank:
            winner = left
            basis = (
                "explicit-authority-precedence"
            )

        elif right_rank < left_rank:
            winner = right
            basis = (
                "explicit-authority-precedence"
            )

        else:
            superseding = (
                self
                ._explicit_supersession(
                    left,
                    right,
                )
            )

            if superseding is not None:
                winner = superseding
                basis = (
                    "explicit-supersession"
                )

            else:
                unresolved_reason = (
                    "equal-authority conflict "
                    "without explicit "
                    "supersession"
                )

        payload = {
            "schema": (
                "savant://runtime/"
                "pryme/comparison/1.1.0"
            ),
            "left":
                left.projection(),
            "right":
                right.projection(),
            "winner": (
                winner.projection()
                if winner is not None
                else None
            ),
            "resolved": (
                winner is not None
            ),
            "conflict": (
                winner is None
            ),
            "basis":
                basis,
            "unresolved_reason":
                unresolved_reason,
            "confidence_used_for_precedence":
                False,
            "status_used_for_precedence":
                False,
            "filesystem_used_for_precedence":
                False,
            "recency_used_for_precedence":
                False,
            "authoritative":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def resolve(
        self,
        records: Iterable[
            AuthorityRecord
        ],
    ) -> dict[str, Any]:
        values = list(
            records
        )

        values.sort(
            key=lambda record: (
                (
                    self
                    .precedence_rank(
                        record
                        .authority_class
                    )
                    if self
                    .precedence_rank(
                        record
                        .authority_class
                    )
                    is not None
                    else len(
                        self.precedence
                    )
                    + 1
                ),
                record.identity,
                record.fingerprint,
            )
        )

        if not values:
            return self._resolution(
                candidates=[],
                resolved=None,
                conflict=False,
                basis=None,
                unresolved_reason=(
                    "no candidates"
                ),
            )

        surviving = list(
            values
        )

        explicit_winners: set[
            str
        ] = set()

        explicit_losers: set[
            str
        ] = set()

        for left in values:
            for right in values:
                if left is right:
                    continue

                if (
                    right.identity
                    in left.supersedes
                ):
                    explicit_winners.add(
                        left.identity
                    )

                    explicit_losers.add(
                        right.identity
                    )

        if explicit_losers:
            surviving = [
                record
                for record
                in surviving
                if record.identity
                not in explicit_losers
            ]

        recognized = [
            record
            for record
            in surviving
            if self.precedence_rank(
                record.authority_class
            )
            is not None
        ]

        unknown = [
            record
            for record
            in surviving
            if self.precedence_rank(
                record.authority_class
            )
            is None
        ]

        if unknown:
            return self._resolution(
                candidates=values,
                resolved=None,
                conflict=True,
                basis=None,
                unresolved_reason=(
                    "candidate set contains "
                    "authority without an "
                    "explicit recognized "
                    "authority class"
                ),
            )

        if not recognized:
            return self._resolution(
                candidates=values,
                resolved=None,
                conflict=True,
                basis=None,
                unresolved_reason=(
                    "no candidate has "
                    "recognized authority"
                ),
            )

        best_rank = min(
            self.precedence_rank(
                record.authority_class
            )
            for record
            in recognized
            if self.precedence_rank(
                record.authority_class
            )
            is not None
        )

        top = [
            record
            for record
            in recognized
            if self.precedence_rank(
                record.authority_class
            )
            == best_rank
        ]

        unique_fingerprints = {
            record.fingerprint
            for record in top
        }

        if len(
            unique_fingerprints
        ) == 1:
            return self._resolution(
                candidates=values,
                resolved=top[0],
                conflict=False,
                basis=(
                    "explicit-authority-"
                    "precedence"
                ),
                unresolved_reason=None,
            )

        if len(top) == 1:
            return self._resolution(
                candidates=values,
                resolved=top[0],
                conflict=False,
                basis=(
                    "explicit-authority-"
                    "precedence"
                ),
                unresolved_reason=None,
            )

        supersession_winners = [
            record
            for record
            in top
            if any(
                other.identity
                in record.supersedes
                for other in top
                if other is not record
            )
        ]

        if (
            len(
                supersession_winners
            )
            == 1
        ):
            winner = (
                supersession_winners[
                    0
                ]
            )

            if all(
                (
                    other is winner
                    or other.identity
                    in winner.supersedes
                )
                for other in top
            ):
                return self._resolution(
                    candidates=values,
                    resolved=winner,
                    conflict=False,
                    basis=(
                        "explicit-"
                        "supersession"
                    ),
                    unresolved_reason=None,
                )

        return self._resolution(
            candidates=values,
            resolved=None,
            conflict=True,
            basis=None,
            unresolved_reason=(
                "equal-authority candidates "
                "conflict and no explicit "
                "supersession resolves them"
            ),
        )

    def _resolution(
        self,
        *,
        candidates:
            Iterable[
                AuthorityRecord
            ],
        resolved:
            AuthorityRecord | None,
        conflict: bool,
        basis: str | None,
        unresolved_reason:
            str | None,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "pryme/resolution/1.1.0"
            ),
            "instance_id": (
                self.instance[
                    "instance_id"
                ]
            ),
            "resolved": (
                resolved.projection()
                if resolved
                is not None
                else None
            ),
            "candidates": [
                record.projection()
                for record
                in candidates
            ],
            "conflict":
                conflict,
            "basis":
                basis,
            "unresolved_reason":
                unresolved_reason,
            "authoritative":
                False,
            "mutation_performed":
                False,
            "authority_manufactured":
                False,
            "confidence_used_for_precedence":
                False,
            "status_used_for_precedence":
                False,
            "filesystem_used_for_precedence":
                False,
            "recency_used_for_precedence":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def explain_precedence(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "pryme/precedence/1.1.0"
            ),
            "source": str(
                self.precedence_source
            ),
            "precedence": [
                {
                    "rank":
                        index + 1,
                    "authority_class":
                        value,
                }
                for index, value
                in enumerate(
                    self.precedence
                )
            ],
            "authority_is_admitted_not_inferred":
                True,
            "filesystem_establishes_authority":
                False,
            "confidence_establishes_authority":
                False,
            "recency_establishes_authority":
                False,
            "authoritative":
                False,
            "mutation_performed":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def health(
        self,
    ) -> dict[str, Any]:
        roots = [
            Path(
                value
            )
            for value
            in self.instance[
                "authority_roots"
            ]
        ]

        dimensions = {
            "precedence_source": (
                self.precedence_source
                .is_file()
            ),
            "authority_roots": (
                any(
                    path.is_dir()
                    for path
                    in roots
                )
            ),
            "identity_integrity":
                True,
            "precedence_integrity": (
                len(
                    self.precedence
                )
                == 11
            ),
            "supersession_integrity":
                True,
            "lineage_integrity":
                True,
            "provenance_integrity":
                True,
            "conflict_integrity":
                True,
            "authority_boundary": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
                and self.instance[
                    "authority_manufacture_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://runtime/"
                "pryme/health/1.1.0"
            ),
            "dimensions": {
                key: {
                    "healthy":
                        bool(value)
                }
                for key, value
                in dimensions.items()
            },
            "healthy": all(
                dimensions.values()
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def validate(
        self,
    ) -> dict[str, Any]:
        checks = {
            "abilities": (
                len(
                    PRYME_ABILITIES
                )
                == 18
            ),
            "pipeline": (
                len(
                    PRYME_PIPELINE
                )
                == 18
            ),
            "health_dimensions": (
                len(
                    PRYME_HEALTH_DIMENSIONS
                )
                == 9
            ),
            "validation_dimensions": (
                len(
                    PRYME_VALIDATION_DIMENSIONS
                )
                == 9
            ),
            "projections": (
                len(
                    PRYME_PROJECTIONS
                )
                == 9
            ),
            "enhancements": (
                self.enhancement_count
                == 27
            ),
            "precedence_count": (
                len(
                    self.precedence
                )
                == 11
            ),
            "mutation_forbidden": (
                self.instance[
                    "mutation_authorized"
                ]
                is False
            ),
            "authority_manufacture_forbidden": (
                self.instance[
                    "authority_manufacture_authorized"
                ]
                is False
            ),
        }

        payload = {
            "schema": (
                "savant://assurance/"
                "pryme/1.1.0"
            ),
            "valid": all(
                checks.values()
            ),
            "checks":
                checks,
            "ability_count":
                18,
            "pipeline_stage_count":
                18,
            "health_dimension_count":
                9,
            "validation_dimension_count":
                9,
            "projection_count":
                9,
            "enhancement_count":
                27,
            "authority_precedence_count":
                len(
                    self.precedence
                ),
            "mutation_authorized":
                False,
            "authority_manufacture_authorized":
                False,
            "confidence_used_for_precedence":
                False,
            "status_used_for_precedence":
                False,
            "filesystem_used_for_precedence":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def profile(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema":
                self.schema,
            "substrate_id":
                self.substrate_id,
            "name":
                "Pryme",
            "role": (
                "living authority "
                "interpretation substrate"
            ),
            "instance":
                self.instance,
            "abilities":
                list(
                    PRYME_ABILITIES
                ),
            "pipeline":
                list(
                    PRYME_PIPELINE
                ),
            "health_dimensions":
                list(
                    PRYME_HEALTH_DIMENSIONS
                ),
            "validation_dimensions":
                list(
                    PRYME_VALIDATION_DIMENSIONS
                ),
            "projections":
                list(
                    PRYME_PROJECTIONS
                ),
            "precedence":
                list(
                    self.precedence
                ),
            "enhancement_count":
                self.enhancement_count,
            "mutation_authorized":
                False,
            "authority_manufacture_authorized":
                False,
            "authority_inferred":
                False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload
