#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-trait-evidence-binding/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

evidence_owner = "palaver"
verification_owner = "notary"

authority_effect = "none"


class orobouros_trait_evidence_binding_error(
    RuntimeError
):
    pass


def _canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        return {}

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
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


def _finite_score(
    value: Any,
) -> float | None:
    try:
        numeric = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(
        numeric
    ):
        return None

    if not (
        0.0
        <= numeric
        <= 1.0
    ):
        return None

    return numeric


def _evidence_digest(
    evidence: Mapping[
        str,
        Any,
    ],
) -> str:
    return str(
        evidence.get(
            "evidence_digest",
            ""
        )
        or ""
    ).strip()


def _admission_map(
    admissions: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[
    str,
    dict[str, Any],
]:
    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for raw in admissions:
        admission = _mapping(
            raw
        )

        admitted = bool(
            admission.get(
                "admitted",
                False,
            )
        )

        admission_owner = _term(
            admission.get(
                "owner"
            )
            or admission.get(
                "verifier_owner"
            )
        )

        evidence_digest = str(
            admission.get(
                "evidence_digest"
            )
            or admission.get(
                "subject_digest"
            )
            or ""
        ).strip()

        admission_ref = str(
            admission.get(
                "admission_ref"
            )
            or admission.get(
                "attestation_ref"
            )
            or ""
        ).strip()

        if not admitted:
            continue

        if admission_owner not in {
            "notary",
            "exile:notary",
        }:
            continue

        if not evidence_digest:
            continue

        if not admission_ref:
            continue

        result[
            evidence_digest
        ] = {
            "owner":
                verification_owner,
            "admitted":
                True,
            "admission_ref":
                admission_ref,
            "evidence_digest":
                evidence_digest,
        }

    return result


def _explicit_trait_measurements(
    evidence: Mapping[
        str,
        Any,
    ],
    trait_id: str,
) -> dict[str, float]:
    semantic = _mapping(
        evidence.get(
            "semantic"
        )
    )

    metadata = _mapping(
        semantic.get(
            "metadata"
        )
    )

    table = _mapping(
        metadata.get(
            "trait_measurements"
        )
    )

    raw = _mapping(
        table.get(
            trait_id
        )
    )

    result: dict[
        str,
        float,
    ] = {}

    for raw_name, raw_value in raw.items():
        name = _term(
            raw_name
        )

        score = _finite_score(
            raw_value
        )

        if (
            name
            and score is not None
        ):
            result[
                name
            ] = score

    return result


def _operational_measurements(
    evidence: Mapping[
        str,
        Any,
    ],
) -> dict[str, float]:
    semantic = _mapping(
        evidence.get(
            "semantic"
        )
    )

    observation = _mapping(
        semantic.get(
            "operational_observation"
        )
    )

    success = bool(
        observation.get(
            "success",
            False,
        )
    )

    cancelled = bool(
        observation.get(
            "cancelled",
            False,
        )
    )

    try:
        retries = max(
            0,
            int(
                observation.get(
                    "retry_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        retries = 0

    try:
        failovers = max(
            0,
            int(
                observation.get(
                    "provider_failover_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        failovers = 0

    reliability = (
        1.0
        if success
        else 0.0
    )

    if cancelled:
        reliability -= 0.20

    reliability -= min(
        0.25,
        retries
        * 0.05,
    )

    reliability -= min(
        0.20,
        failovers
        * 0.05,
    )

    reliability = max(
        0.0,
        min(
            1.0,
            reliability,
        ),
    )

    latency_score = 1.0

    try:
        latency_ms = float(
            observation.get(
                "latency_ms"
            )
        )

        if not math.isfinite(
            latency_ms
        ):
            raise ValueError

        if latency_ms > 60_000:
            latency_score = 0.35
        elif latency_ms > 30_000:
            latency_score = 0.55
        elif latency_ms > 10_000:
            latency_score = 0.75
        elif latency_ms > 5_000:
            latency_score = 0.90

    except (
        TypeError,
        ValueError,
    ):
        latency_score = 1.0

    return {
        "operational_reliability":
            reliability,
        "latency_stability":
            latency_score,
    }


def _aggregate(
    samples: Iterable[
        Mapping[
            str,
            float,
        ]
    ],
) -> dict[str, float]:
    buckets: dict[
        str,
        list[float],
    ] = {}

    for sample in samples:
        for name, value in sample.items():
            buckets.setdefault(
                name,
                [],
            ).append(
                value
            )

    return {
        name:
            (
                sum(
                    values
                )
                / len(
                    values
                )
            )
        for name, values in sorted(
            buckets.items()
        )
        if values
    }


def candidate_measurements(
    *,
    trait_id: str,
    evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    notary_admissions: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    minimum_samples: int = 1,
) -> dict[str, Any]:
    trait = _term(
        trait_id
    )

    if not trait:
        raise (
            orobouros_trait_evidence_binding_error(
                "trait_id is required"
            )
        )

    admission_index = (
        _admission_map(
            notary_admissions
        )
    )

    minimum_samples = max(
        1,
        int(
            minimum_samples
        ),
    )

    accepted: list[
        dict[str, Any]
    ] = []

    samples: list[
        dict[str, float]
    ] = []

    explicit_sample_count = 0

    for raw in evidence:
        item = _mapping(
            raw
        )

        if not item:
            continue

        if _term(
            item.get(
                "owner"
            )
        ) not in {
            "palaver",
            "exile:palaver",
        }:
            continue

        if (
            item.get(
                "authority_effect"
            )
            != "none"
        ):
            continue

        evidence_digest = (
            _evidence_digest(
                item
            )
        )

        if not evidence_digest:
            continue

        admission = (
            admission_index.get(
                evidence_digest
            )
        )

        if admission is None:
            continue

        explicit = (
            _explicit_trait_measurements(
                item,
                trait,
            )
        )

        operational = (
            _operational_measurements(
                item
            )
        )

        combined = dict(
            operational
        )

        if explicit:
            explicit_sample_count += 1

            combined.update(
                explicit
            )

        samples.append(
            combined
        )

        accepted.append(
            {
                "evidence_digest":
                    evidence_digest,
                "admission_ref":
                    admission[
                        "admission_ref"
                    ],
                "explicit_trait_measurements":
                    explicit,
                "operational_measurements":
                    operational,
            }
        )

    if (
        len(
            accepted
        )
        < minimum_samples
    ):
        raise (
            orobouros_trait_evidence_binding_error(
                "insufficient admitted evidence"
            )
        )

    measurements = _aggregate(
        samples
    )

    if not measurements:
        raise (
            orobouros_trait_evidence_binding_error(
                "admitted evidence produced "
                "no measurements"
            )
        )

    evidence_ids = tuple(
        sorted(
            {
                row[
                    "evidence_digest"
                ]
                for row in accepted
            }
            | {
                row[
                    "admission_ref"
                ]
                for row in accepted
            }
        )
    )

    semantic = {
        "trait_id":
            trait,
        "measurements":
            measurements,
        "sample_count":
            len(
                accepted
            ),
        "explicit_trait_sample_count":
            explicit_sample_count,
        "evidence_ids":
            list(
                evidence_ids
            ),
        "evidence":
            accepted,
    }

    binding_digest = _digest(
        semantic
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "trait_id":
            trait,
        "binding_id":
            (
                "oroevidence_"
                + binding_digest[
                    :32
                ]
            ),
        "binding_digest":
            binding_digest,
        "measurements":
            measurements,
        "sample_count":
            len(
                accepted
            ),
        "explicit_trait_sample_count":
            explicit_sample_count,
        "evidence_ids":
            list(
                evidence_ids
            ),
        "verified":
            True,
        "evidence_admitted":
            True,
        "evidence_owner":
            evidence_owner,
        "verification_owner":
            verification_owner,
        "trait_attribution_inferred":
            False,
        "operational_measurements_shared":
            True,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }


def build_trial(
    *,
    trait_id: str,
    champion_candidate_id: str,
    challenger_candidate_id: str,
    champion_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    challenger_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    notary_admissions: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    weights: Mapping[
        str,
        Any,
    ],
    minimum_margin: float = 0.03,
    minimum_samples: int = 1,
    policy_id: str = (
        "orobouros_evidence_driven_"
        "trait_promotion_v1"
    ),
) -> dict[str, Any]:
    champion = candidate_measurements(
        trait_id=
            trait_id,
        evidence=
            champion_evidence,
        notary_admissions=
            notary_admissions,
        minimum_samples=
            minimum_samples,
    )

    challenger = candidate_measurements(
        trait_id=
            trait_id,
        evidence=
            challenger_evidence,
        notary_admissions=
            notary_admissions,
        minimum_samples=
            minimum_samples,
    )

    normalized_weights: dict[
        str,
        float,
    ] = {}

    for raw_name, raw_value in (
        _mapping(
            weights
        ).items()
    ):
        name = _term(
            raw_name
        )

        score = _finite_score(
            raw_value
        )

        if (
            name
            and score is not None
        ):
            normalized_weights[
                name
            ] = score

    if not normalized_weights:
        raise (
            orobouros_trait_evidence_binding_error(
                "adjudication weights "
                "must not be empty"
            )
        )

    common = (
        set(
            champion[
                "measurements"
            ]
        )
        & set(
            challenger[
                "measurements"
            ]
        )
        & set(
            normalized_weights
        )
    )

    if not common:
        raise (
            orobouros_trait_evidence_binding_error(
                "champion and challenger "
                "have no weighted common dimensions"
            )
        )

    admission_refs = sorted(
        {
            evidence_id
            for evidence_id in (
                champion[
                    "evidence_ids"
                ]
                + challenger[
                    "evidence_ids"
                ]
            )
            if str(
                evidence_id
            ).startswith(
                (
                    "notary:",
                    "notary://",
                )
            )
        }
    )

    if not admission_refs:
        admission_refs = [
            "notary:admitted-evidence-set:"
            + _digest(
                sorted(
                    champion[
                        "evidence_ids"
                    ]
                    + challenger[
                        "evidence_ids"
                    ]
                )
            )[:32]
        ]

    return {
        "champion":
            {
                "candidate_id":
                    str(
                        champion_candidate_id
                    ),
                "measurements":
                    champion[
                        "measurements"
                    ],
            },
        "challenger":
            {
                "candidate_id":
                    str(
                        challenger_candidate_id
                    ),
                "measurements":
                    challenger[
                        "measurements"
                    ],
            },
        "policy":
            {
                "policy_id":
                    _term(
                        policy_id
                    ),
                "weights":
                    normalized_weights,
                "minimum_margin":
                    max(
                        0.0,
                        float(
                            minimum_margin
                        ),
                    ),
            },
        "notary_admission":
            {
                "owner":
                    verification_owner,
                "admitted":
                    True,
                "admission_ref":
                    admission_refs[
                        0
                    ],
            },
        "evidence_ids":
            sorted(
                set(
                    champion[
                        "evidence_ids"
                    ]
                    + challenger[
                        "evidence_ids"
                    ]
                )
            ),
        "binding":
            {
                "champion_binding_digest":
                    champion[
                        "binding_digest"
                    ],
                "challenger_binding_digest":
                    challenger[
                        "binding_digest"
                    ],
                "trait_attribution_inferred":
                    False,
            },
    }


def selftest() -> dict[str, Any]:
    def evidence(
        *,
        digest: str,
        planning: float,
    ) -> dict[str, Any]:
        return {
            "owner":
                "palaver",
            "authority_effect":
                "none",
            "evidence_digest":
                digest,
            "semantic":
                {
                    "metadata":
                        {
                            "trait_measurements":
                                {
                                    "planning":
                                        {
                                            "contextual_suitability":
                                                planning,
                                            "correctness":
                                                planning,
                                        }
                                }
                        },
                    "operational_observation":
                        {
                            "success":
                                True,
                            "cancelled":
                                False,
                            "latency_ms":
                                1000,
                            "retry_count":
                                0,
                            "provider_failover_count":
                                0,
                        },
                },
        }

    admissions = [
        {
            "owner":
                "notary",
            "admitted":
                True,
            "admission_ref":
                "notary://evidence/a",
            "evidence_digest":
                "evidence-a",
        },
        {
            "owner":
                "notary",
            "admitted":
                True,
            "admission_ref":
                "notary://evidence/b",
            "evidence_digest":
                "evidence-b",
        },
    ]

    trial = build_trial(
        trait_id=
            "planning",
        champion_candidate_id=
            "planning-v1",
        challenger_candidate_id=
            "planning-v2",
        champion_evidence=[
            evidence(
                digest="evidence-a",
                planning=0.75,
            )
        ],
        challenger_evidence=[
            evidence(
                digest="evidence-b",
                planning=0.90,
            )
        ],
        notary_admissions=
            admissions,
        weights=
            {
                "correctness":
                    1.0,
                "contextual_suitability":
                    1.0,
                "operational_reliability":
                    0.5,
            },
    )

    if (
        trial[
            "binding"
        ][
            "trait_attribution_inferred"
        ]
        is not False
    ):
        raise (
            orobouros_trait_evidence_binding_error(
                "trait attribution became inferred"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "trait_id":
            "planning",
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
