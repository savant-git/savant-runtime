#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


def _normalize(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def _sentences(text: str) -> List[str]:
    values = re.split(
        r"(?<=[.!?])\s+|\n+",
        str(text or "").strip(),
    )

    return [
        " ".join(value.split())
        for value in values
        if value.strip()
    ]


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(
            r"[a-z0-9_]+",
            _normalize(text),
        )
        if len(token) > 2
    )


def similarity(
    left: str,
    right: str,
) -> float:
    a = _tokens(left)
    b = _tokens(right)

    if not a or not b:
        return 0.0

    union = a | b

    if not union:
        return 0.0

    return len(a & b) / len(union)


@dataclass(frozen=True)
class ConsensusCluster:
    representative: str
    members: tuple[str, ...]
    providers: tuple[str, ...]
    agreement: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "representative": self.representative,
            "members": list(self.members),
            "providers": list(self.providers),
            "agreement": self.agreement,
        }


@dataclass(frozen=True)
class ConsensusResult:
    clusters: tuple[ConsensusCluster, ...]
    agreements: tuple[str, ...]
    disagreements: tuple[str, ...]
    provider_count: int
    agreement_ratio: float
    requires_adjudication: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clusters": [
                cluster.as_dict()
                for cluster in self.clusters
            ],
            "agreements": list(
                self.agreements
            ),
            "disagreements": list(
                self.disagreements
            ),
            "provider_count":
                self.provider_count,
            "agreement_ratio":
                self.agreement_ratio,
            "requires_adjudication":
                self.requires_adjudication,
        }


def semantic_consensus(
    candidates: Sequence[Mapping[str, Any]],
    *,
    similarity_threshold: float = 0.58,
    agreement_threshold: float = 0.67,
) -> ConsensusResult:
    threshold = max(
        0.0,
        min(
            1.0,
            float(similarity_threshold),
        ),
    )

    providers = {
        str(
            candidate.get(
                "provider_id"
            )
            or candidate.get(
                "provider"
            )
            or ""
        ).strip()
        for candidate in candidates
    }

    providers.discard("")

    statements: List[
        Tuple[str, str]
    ] = []

    for candidate in candidates:
        provider_id = str(
            candidate.get(
                "provider_id"
            )
            or candidate.get(
                "provider"
            )
            or ""
        ).strip()

        text = str(
            candidate.get("text")
            or ""
        ).strip()

        if not provider_id or not text:
            continue

        for sentence in _sentences(text):
            statements.append(
                (
                    provider_id,
                    sentence,
                )
            )

    groups: List[
        Dict[str, Any]
    ] = []

    for provider_id, statement in statements:
        best_index = None
        best_similarity = 0.0

        for index, group in enumerate(groups):
            score = similarity(
                statement,
                group["representative"],
            )

            if score > best_similarity:
                best_similarity = score
                best_index = index

        if (
            best_index is not None
            and best_similarity >= threshold
        ):
            group = groups[
                best_index
            ]

            group["members"].append(
                statement
            )
            group["providers"].add(
                provider_id
            )

            current = group[
                "representative"
            ]

            if len(statement) < len(current):
                group[
                    "representative"
                ] = statement
        else:
            groups.append(
                {
                    "representative":
                        statement,
                    "members": [
                        statement
                    ],
                    "providers": {
                        provider_id
                    },
                }
            )

    provider_count = len(
        providers
    )

    clusters: List[
        ConsensusCluster
    ] = []

    agreements: List[str] = []
    disagreements: List[str] = []

    for group in groups:
        agreement = (
            len(group["providers"])
            / provider_count
            if provider_count
            else 0.0
        )

        cluster = ConsensusCluster(
            representative=group[
                "representative"
            ],
            members=tuple(
                group["members"]
            ),
            providers=tuple(
                sorted(
                    group[
                        "providers"
                    ]
                )
            ),
            agreement=round(
                agreement,
                6,
            ),
        )

        clusters.append(
            cluster
        )

        if (
            agreement
            >= agreement_threshold
        ):
            agreements.append(
                cluster.representative
            )
        else:
            disagreements.append(
                cluster.representative
            )

    clusters.sort(
        key=lambda item: (
            -item.agreement,
            item.representative.lower(),
        )
    )

    total_clusters = len(
        clusters
    )

    agreement_ratio = (
        len(agreements)
        / total_clusters
        if total_clusters
        else 0.0
    )

    return ConsensusResult(
        clusters=tuple(clusters),
        agreements=tuple(
            agreements
        ),
        disagreements=tuple(
            disagreements
        ),
        provider_count=provider_count,
        agreement_ratio=round(
            agreement_ratio,
            6,
        ),
        requires_adjudication=(
            provider_count > 1
            and (
                bool(disagreements)
                or agreement_ratio
                < agreement_threshold
            )
        ),
    )
