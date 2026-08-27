#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = (
    "savant://envoy/"
    "orobouros-trait-evidence/1.0.0"
)

OWNER = "exile:envoy"
VERIFICATION_OWNER = "exile:notary"
MECHANICS_OWNER = "living:thryce"


class TraitEvidenceError(
    ValueError
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


def normalize_term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalized
                for value in values
                if (
                    normalized
                    := normalize_term(
                        value
                    )
                )
            }
        )
    )


def normalize_confidence(
    value: Any,
) -> float:
    try:
        confidence = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise TraitEvidenceError(
            "confidence must be numeric"
        ) from exc

    if not (
        0.0
        <= confidence
        <= 1.0
    ):
        raise TraitEvidenceError(
            "confidence must be "
            "between 0 and 1"
        )

    return confidence


def normalize_measurements(
    values: Mapping[
        str,
        Any,
    ]
    | None,
) -> tuple[
    tuple[
        str,
        float,
    ],
    ...,
]:
    if values is None:
        return ()

    if not isinstance(
        values,
        Mapping,
    ):
        raise TraitEvidenceError(
            "measurements must be "
            "a mapping"
        )

    normalized: list[
        tuple[
            str,
            float,
        ]
    ] = []

    for raw_name, raw_value in (
        values.items()
    ):
        name = normalize_term(
            raw_name
        )

        if not name:
            raise TraitEvidenceError(
                "measurement name "
                "is required"
            )

        try:
            value = float(
                raw_value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TraitEvidenceError(
                "measurement values "
                "must be numeric"
            ) from exc

        normalized.append(
            (
                name,
                value,
            )
        )

    normalized.sort(
        key=lambda item: (
            item[0]
        )
    )

    return tuple(
        normalized
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderProvenance:
    provider_id: str
    model_id: str
    model_version: str = ""
    route: str = (
        "text_inference_route"
    )
    response_id: str = ""

    def __post_init__(
        self,
    ) -> None:
        provider_id = normalize_term(
            self.provider_id
        )

        model_id = str(
            self.model_id
            or ""
        ).strip()

        if not provider_id:
            raise TraitEvidenceError(
                "provider_id is required"
            )

        if not model_id:
            raise TraitEvidenceError(
                "model_id is required"
            )

        object.__setattr__(
            self,
            "provider_id",
            provider_id,
        )

        object.__setattr__(
            self,
            "model_id",
            model_id,
        )

        object.__setattr__(
            self,
            "model_version",
            str(
                self.model_version
                or ""
            ).strip(),
        )

        object.__setattr__(
            self,
            "route",
            str(
                self.route
                or ""
            ).strip(),
        )

        object.__setattr__(
            self,
            "response_id",
            str(
                self.response_id
                or ""
            ).strip(),
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "provider_id": (
                self.provider_id
            ),
            "model_id": (
                self.model_id
            ),
            "model_version": (
                self.model_version
            ),
            "route": self.route,
            "response_id": (
                self.response_id
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class TraitObservation:
    trait_id: str
    description: str
    provenance: ProviderProvenance
    confidence: float
    domains: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    measurements: tuple[
        tuple[
            str,
            float,
        ],
        ...,
    ] = ()
    evidence_refs: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        trait_id = normalize_term(
            self.trait_id
        )

        description = str(
            self.description
            or ""
        ).strip()

        if not trait_id:
            raise TraitEvidenceError(
                "trait_id is required"
            )

        if not description:
            raise TraitEvidenceError(
                "description is required"
            )

        object.__setattr__(
            self,
            "trait_id",
            trait_id,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "confidence",
            normalize_confidence(
                self.confidence
            ),
        )

        object.__setattr__(
            self,
            "domains",
            normalize_terms(
                self.domains
            ),
        )

        object.__setattr__(
            self,
            "signals",
            normalize_terms(
                self.signals
            ),
        )

        object.__setattr__(
            self,
            "conflicts",
            normalize_terms(
                self.conflicts
            ),
        )

        object.__setattr__(
            self,
            "measurements",
            tuple(
                sorted(
                    (
                        (
                            normalize_term(
                                name
                            ),
                            float(
                                value
                            ),
                        )
                        for (
                            name,
                            value,
                        )
                        in self.measurements
                    ),
                    key=lambda item: (
                        item[0]
                    ),
                )
            ),
        )

        object.__setattr__(
            self,
            "evidence_refs",
            normalize_terms(
                self.evidence_refs
            ),
        )

        object.__setattr__(
            self,
            "lineage",
            normalize_terms(
                self.lineage
            ),
        )

        object.__setattr__(
            self,
            "dependencies",
            normalize_terms(
                self.dependencies
            ),
        )

    @property
    def observation_id(
        self,
    ) -> str:
        material = {
            "trait_id": (
                self.trait_id
            ),
            "description": (
                self.description
            ),
            "provenance": (
                self.provenance
                .projection()
            ),
            "confidence": (
                self.confidence
            ),
            "domains": list(
                self.domains
            ),
            "signals": list(
                self.signals
            ),
            "conflicts": list(
                self.conflicts
            ),
            "measurements": [
                {
                    "name": name,
                    "value": value,
                }
                for (
                    name,
                    value,
                )
                in self.measurements
            ],
            "evidence_refs": list(
                self.evidence_refs
            ),
            "lineage": list(
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
        }

        return (
            "trait-observation:"
            + digest(
                material
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "observation_id": (
                self.observation_id
            ),
            "trait_id": (
                self.trait_id
            ),
            "description": (
                self.description
            ),
            "domains": list(
                self.domains
            ),
            "signals": list(
                self.signals
            ),
            "conflicts": list(
                self.conflicts
            ),
            "confidence": (
                self.confidence
            ),
            "measurements": [
                {
                    "name": name,
                    "value": value,
                }
                for (
                    name,
                    value,
                )
                in self.measurements
            ],
            "evidence_refs": list(
                self.evidence_refs
            ),
            "provenance": (
                self.provenance
                .projection()
            ),
            "lineage": list(
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
            "owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "verified": False,
            "evidence_admitted": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class TraitCandidate:
    trait_id: str
    description: str
    observations: tuple[
        TraitObservation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        trait_id = normalize_term(
            self.trait_id
        )

        description = str(
            self.description
            or ""
        ).strip()

        if not trait_id:
            raise TraitEvidenceError(
                "candidate trait_id "
                "is required"
            )

        if not description:
            raise TraitEvidenceError(
                "candidate description "
                "is required"
            )

        if not self.observations:
            raise TraitEvidenceError(
                "candidate requires "
                "at least one observation"
            )

        for observation in (
            self.observations
        ):
            if (
                observation.trait_id
                != trait_id
            ):
                raise TraitEvidenceError(
                    "candidate contains "
                    "observation for a "
                    "different trait"
                )

        ordered = tuple(
            sorted(
                self.observations,
                key=lambda observation: (
                    observation
                    .observation_id
                ),
            )
        )

        object.__setattr__(
            self,
            "trait_id",
            trait_id,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "observations",
            ordered,
        )

    @property
    def candidate_id(
        self,
    ) -> str:
        material = {
            "trait_id": (
                self.trait_id
            ),
            "description": (
                self.description
            ),
            "observations": [
                observation
                .observation_id
                for observation
                in self.observations
            ],
        }

        return (
            "trait-candidate:"
            + digest(
                material
            )[:32]
        )

    @property
    def providers(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    observation
                    .provenance
                    .provider_id
                    for observation
                    in self.observations
                }
            )
        )

    @property
    def models(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    observation
                    .provenance
                    .model_id
                    for observation
                    in self.observations
                }
            )
        )

    @property
    def domains(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    domain
                    for observation
                    in self.observations
                    for domain
                    in observation.domains
                }
            )
        )

    @property
    def signals(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    signal
                    for observation
                    in self.observations
                    for signal
                    in observation.signals
                }
            )
        )

    @property
    def conflicts(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    conflict
                    for observation
                    in self.observations
                    for conflict
                    in observation.conflicts
                }
            )
        )

    @property
    def confidence_range(
        self,
    ) -> tuple[
        float,
        float,
    ]:
        values = tuple(
            observation.confidence
            for observation
            in self.observations
        )

        return (
            min(
                values
            ),
            max(
                values
            ),
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        low, high = (
            self.confidence_range
        )

        payload = {
            "schema": (
                "savant://envoy/"
                "orobouros-trait-candidate/"
                "1.0.0"
            ),
            "candidate_id": (
                self.candidate_id
            ),
            "trait_id": (
                self.trait_id
            ),
            "description": (
                self.description
            ),
            "domains": list(
                self.domains
            ),
            "signals": list(
                self.signals
            ),
            "conflicts": list(
                self.conflicts
            ),
            "observation_ids": [
                observation
                .observation_id
                for observation
                in self.observations
            ],
            "observation_count": len(
                self.observations
            ),
            "providers": list(
                self.providers
            ),
            "models": list(
                self.models
            ),
            "confidence_range": {
                "minimum": low,
                "maximum": high,
            },
            "owner": OWNER,
            "verification_owner": (
                VERIFICATION_OWNER
            ),
            "verified": False,
            "evidence_admitted": False,
            "champion": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def candidate_from_observations(
    observations: Sequence[
        TraitObservation
    ],
) -> TraitCandidate:
    materialized = tuple(
        observations
    )

    if not materialized:
        raise TraitEvidenceError(
            "no observations supplied"
        )

    trait_ids = {
        observation.trait_id
        for observation
        in materialized
    }

    if len(
        trait_ids
    ) != 1:
        raise TraitEvidenceError(
            "observations span "
            "multiple trait ids"
        )

    descriptions = tuple(
        sorted(
            {
                observation
                .description
                for observation
                in materialized
            }
        )
    )

    if len(
        descriptions
    ) != 1:
        raise TraitEvidenceError(
            "semantic trait description "
            "conflict requires adjudication"
        )

    return TraitCandidate(
        trait_id=next(
            iter(
                trait_ids
            )
        ),
        description=(
            descriptions[0]
        ),
        observations=materialized,
    )


def notary_candidate_payload(
    candidate: TraitCandidate,
) -> dict[str, Any]:
    projection = (
        candidate.projection()
    )

    dependencies = tuple(
        sorted(
            {
                dependency
                for observation
                in candidate.observations
                for dependency
                in observation.dependencies
            }
        )
    )

    provenance = [
        observation
        .provenance
        .projection()
        for observation
        in candidate.observations
    ]

    lineage = tuple(
        sorted(
            {
                lineage
                for observation
                in candidate.observations
                for lineage
                in observation.lineage
            }
        )
    )

    return {
        "subject": (
            "orobouros-trait:"
            + candidate.trait_id
        ),
        "payload": projection,
        "provenance": provenance,
        "lineage": list(
            lineage
        ),
        "dependencies": list(
            dependencies
        ),
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "authoritative": False,
        "authority_effect": "none",
    }


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://envoy/"
            "orobouros-trait-evidence-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "verification_owner": (
            VERIFICATION_OWNER
        ),
        "mechanics_owner": (
            MECHANICS_OWNER
        ),
        "provider_identity_role": (
            "provenance_only"
        ),
        "candidate_semantics_owner": (
            OWNER
        ),
        "verification_delegated": True,
        "evidence_admission_local": False,
        "champion_selection_local": False,
        "baseline_mutation": False,
        "crown_mutation": False,
        "persistent_store": False,
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
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
