#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable
from primitives import bind_stable_id
from primitives import load_payload as load_json


schema_version = "savant.underscore.vessel.ideal-state.v1"
authority_effect = "none"


try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


try:
    from pydantic import (
        BaseModel,
        ConfigDict,
        Field,
    )
except ImportError:
    BaseModel = None
    ConfigDict = None
    Field = None


word_pattern = re.compile(
    r"[a-z0-9][a-z0-9'\-]*",
    re.IGNORECASE,
)

sentence_pattern = re.compile(
    r"(?<=[.!?])\s+"
)

stopwords = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "hers",
        "him",
        "his",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "she",
        "so",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "they",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
    }
)

causal_markers = (
    "because",
    "therefore",
    "consequently",
    "causes",
    "caused",
    "results in",
    "leads to",
    "forces",
    "thereby",
    "so that",
    "which means",
    "as a result",
)

concealment_markers = (
    "secretly",
    "secret identity",
    "it was all a dream",
    "actually",
    "unknown all along",
    "revealed at the end",
    "suddenly reveals",
    "turns out",
    "was dead all along",
)

assumption_markers = (
    "must",
    "obviously",
    "clearly",
    "inevitably",
    "necessarily",
    "everyone knows",
    "of course",
    "cannot possibly",
    "has to",
    "always",
    "never",
)

specificity_markers = (
    "exactly",
    "specifically",
    "because",
    "when",
    "where",
    "after",
    "before",
    "during",
)

enhancements = (
    "typed_boundary_validation",
    "deterministic_candidate_fingerprints",
    "mechanism_fingerprints",
    "lexical_entropy",
    "baseline_dependence",
    "cliche_risk",
    "negative_knowledge_recurrence",
    "hard_constraint_integrity",
    "causal_coherence",
    "information_transparency",
    "specificity_density",
    "assumption_fragility",
    "false_diversity_detection",
    "mechanism_novelty",
    "anti_goodhart_penalty",
    "uncertainty_proxy",
    "multiobjective_vectors",
    "pareto_frontier",
    "quality_diversity_archive",
    "behavioral_cell_occupancy",
    "novelty_archive",
    "diversity_collapse_detection",
    "assumption_graph",
    "lineage_dag",
    "contradiction_matrix",
    "discriminating_experiment_planning",
    "information_gain_cost_risk_reversibility",
    "deterministic_stopping_policy",
)


if BaseModel is not None:

    class ConstraintModel(
        BaseModel
    ):
        model_config = (
            ConfigDict(
                extra="allow"
            )
        )

        required: list[str] = (
            Field(
                default_factory=list
            )
        )

        forbidden: list[str] = (
            Field(
                default_factory=list
            )
        )


    class CandidateModel(
        BaseModel
    ):
        model_config = (
            ConfigDict(
                extra="allow"
            )
        )

        instance_id: str | None = None
        candidate_id: str | None = None
        text: str
        assumptions: list[str] = (
            Field(
                default_factory=list
            )
        )
        lineage: list[str] = (
            Field(
                default_factory=list
            )
        )
        flags: list[str] = (
            Field(
                default_factory=list
            )
        )
        metadata: dict[str, Any] = (
            Field(
                default_factory=dict
            )
        )


    class PayloadModel(
        BaseModel
    ):
        model_config = (
            ConfigDict(
                extra="allow"
            )
        )

        subject: str
        candidates: list[
            CandidateModel
        ] = Field(
            default_factory=list
        )
        baselines: list[str] = (
            Field(
                default_factory=list
            )
        )
        cliches: list[str] = (
            Field(
                default_factory=list
            )
        )
        constraints: ConstraintModel = (
            Field(
                default_factory=(
                    ConstraintModel
                )
            )
        )
        negative_knowledge: (
            dict[str, Any]
        ) = Field(
            default_factory=dict
        )

else:
    PayloadModel = None


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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


stable_id = bind_stable_id(digest)

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
    )


def mean(
    values: Iterable[float],
) -> float:
    values = list(
        values
    )

    if not values:
        return 0.0

    return float(
        statistics.fmean(
            values
        )
    )


def tokens(
    text: Any,
) -> list[str]:
    return [
        value.casefold()
        for value
        in word_pattern.findall(
            str(
                text
                or ""
            )
        )
    ]


def content_tokens(
    text: Any,
) -> list[str]:
    return [
        value
        for value in tokens(
            text
        )
        if value not in stopwords
        and len(value) >= 3
    ]


def normalize_text(
    text: Any,
) -> str:
    return " ".join(
        tokens(
            text
        )
    )


def ngrams(
    values: list[str],
    width: int,
) -> set[
    tuple[str, ...]
]:
    if (
        width <= 0
        or len(values) < width
    ):
        return set()

    return {
        tuple(
            values[
                index:
                index + width
            ]
        )
        for index
        in range(
            len(values)
            - width
            + 1
        )
    }


def jaccard(
    left: set[Any],
    right: set[Any],
) -> float:
    if (
        not left
        and not right
    ):
        return 1.0

    union = (
        left
        | right
    )

    if not union:
        return 0.0

    return (
        len(
            left
            & right
        )
        / len(
            union
        )
    )


def fuzzy_similarity(
    left: Any,
    right: Any,
) -> float:
    left_text = normalize_text(
        left
    )

    right_text = normalize_text(
        right
    )

    if (
        not left_text
        or not right_text
    ):
        return 0.0

    if fuzz is not None:
        return clamp(
            max(
                fuzz.WRatio(
                    left_text,
                    right_text,
                ),
                fuzz.token_set_ratio(
                    left_text,
                    right_text,
                ),
            )
            / 100.0
        )

    return clamp(
        SequenceMatcher(
            None,
            left_text,
            right_text,
        ).ratio()
    )


def blended_similarity(
    left: Any,
    right: Any,
) -> float:
    left_tokens = tokens(
        left
    )

    right_tokens = tokens(
        right
    )

    lexical = fuzzy_similarity(
        left,
        right,
    )

    unigram = jaccard(
        set(
            left_tokens
        ),
        set(
            right_tokens
        ),
    )

    bigram = jaccard(
        ngrams(
            left_tokens,
            2,
        ),
        ngrams(
            right_tokens,
            2,
        ),
    )

    return clamp(
        (
            lexical * 0.60
            + unigram * 0.25
            + bigram * 0.15
        )
    )


def lexical_entropy(
    text: Any,
) -> float:
    values = tokens(
        text
    )

    if len(values) <= 1:
        return 0.0

    counts: dict[
        str,
        int,
    ] = {}

    for value in values:
        counts[
            value
        ] = (
            counts.get(
                value,
                0,
            )
            + 1
        )

    total = len(
        values
    )

    entropy = 0.0

    for count in (
        counts.values()
    ):
        probability = (
            count
            / total
        )

        entropy -= (
            probability
            * math.log2(
                probability
            )
        )

    maximum = math.log2(
        max(
            2,
            len(
                counts
            ),
        )
    )

    return clamp(
        entropy
        / maximum
        if maximum
        else 0.0
    )


def max_similarity(
    text: str,
    references: Iterable[Any],
) -> float:
    scores = [
        blended_similarity(
            text,
            value,
        )
        for value in references
        if str(
            value
        ).strip()
    ]

    return max(
        scores,
        default=0.0,
    )


def phrase_pressure(
    text: str,
    phrases: Iterable[Any],
) -> float:
    normalized = normalize_text(
        text
    )

    if not normalized:
        return 0.0

    values = []

    for phrase in phrases:
        phrase_text = (
            normalize_text(
                phrase
            )
        )

        if not phrase_text:
            continue

        direct = (
            1.0
            if phrase_text
            in normalized
            else 0.0
        )

        fuzzy_score = (
            blended_similarity(
                normalized,
                phrase_text,
            )
        )

        values.append(
            max(
                direct,
                fuzzy_score,
            )
        )

    return max(
        values,
        default=0.0,
    )


def constraint_integrity(
    text: str,
    constraints: dict[str, Any],
) -> tuple[
    float,
    dict[str, Any],
]:
    normalized = normalize_text(
        text
    )

    required = [
        normalize_text(
            item
        )
        for item
        in constraints.get(
            "required",
            [],
        )
        if normalize_text(
            item
        )
    ]

    forbidden = [
        normalize_text(
            item
        )
        for item
        in constraints.get(
            "forbidden",
            [],
        )
        if normalize_text(
            item
        )
    ]

    required_hits = [
        item
        for item
        in required
        if item in normalized
    ]

    required_misses = [
        item
        for item
        in required
        if item not in normalized
    ]

    forbidden_hits = [
        item
        for item
        in forbidden
        if item in normalized
    ]

    required_score = (
        len(
            required_hits
        )
        / len(
            required
        )
        if required
        else 1.0
    )

    forbidden_score = (
        1.0
        - (
            len(
                forbidden_hits
            )
            / len(
                forbidden
            )
        )
        if forbidden
        else 1.0
    )

    score = clamp(
        required_score
        * 0.65
        + forbidden_score
        * 0.35
    )

    return (
        score,
        {
            "required_hits": (
                required_hits
            ),
            "required_misses": (
                required_misses
            ),
            "forbidden_hits": (
                forbidden_hits
            ),
        },
    )


def causal_coherence(
    text: str,
) -> float:
    normalized = normalize_text(
        text
    )

    if not normalized:
        return 0.0

    marker_count = sum(
        1
        for marker
        in causal_markers
        if marker
        in normalized
    )

    sentences = [
        sentence
        for sentence
        in sentence_pattern.split(
            str(text)
        )
        if sentence.strip()
    ]

    sentence_factor = clamp(
        len(
            sentences
        )
        / 4.0
    )

    marker_factor = clamp(
        marker_count
        / 3.0
    )

    connector_factor = (
        1.0
        if any(
            marker in normalized
            for marker
            in (
                "because",
                "therefore",
                "as a result",
                "which means",
                "so that",
            )
        )
        else 0.35
    )

    return clamp(
        (
            marker_factor * 0.50
            + sentence_factor * 0.20
            + connector_factor * 0.30
        )
    )


def information_transparency(
    text: str,
) -> float:
    normalized = normalize_text(
        text
    )

    concealment = (
        phrase_pressure(
            normalized,
            concealment_markers,
        )
    )

    causal = causal_coherence(
        text
    )

    return clamp(
        (
            1.0
            - concealment
        )
        * 0.70
        + causal * 0.30
    )


def specificity_density(
    text: str,
) -> float:
    values = tokens(
        text
    )

    if not values:
        return 0.0

    unique_ratio = (
        len(
            set(
                values
            )
        )
        / len(
            values
        )
    )

    numeric = sum(
        1
        for value
        in values
        if any(
            character.isdigit()
            for character
            in value
        )
    )

    marker_count = sum(
        1
        for marker
        in specificity_markers
        if marker
        in normalize_text(
            text
        )
    )

    uncommon = sum(
        1
        for value
        in content_tokens(
            text
        )
        if len(
            value
        ) >= 8
    )

    density = (
        unique_ratio * 0.45
        + clamp(
            numeric
            / 3.0
        )
        * 0.15
        + clamp(
            marker_count
            / 4.0
        )
        * 0.20
        + clamp(
            uncommon
            / 8.0
        )
        * 0.20
    )

    return clamp(
        density
    )


def assumption_fragility(
    text: str,
    assumptions: Iterable[Any],
) -> float:
    normalized = normalize_text(
        text
    )

    marker_count = sum(
        1
        for marker
        in assumption_markers
        if marker
        in normalized
    )

    explicit_assumptions = len(
        [
            value
            for value
            in assumptions
            if str(
                value
            ).strip()
        ]
    )

    return clamp(
        (
            clamp(
                marker_count
                / 4.0
            )
            * 0.60
            + clamp(
                explicit_assumptions
                / 6.0
            )
            * 0.40
        )
    )


def mechanism_fingerprint(
    text: str,
) -> dict[str, Any]:
    values = content_tokens(
        text
    )

    frequency: dict[
        str,
        int,
    ] = {}

    for value in values:
        frequency[
            value
        ] = (
            frequency.get(
                value,
                0,
            )
            + 1
        )

    ranked = sorted(
        frequency.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    keywords = [
        value
        for value, _
        in ranked[:8]
    ]

    normalized = normalize_text(
        text
    )

    causal = [
        marker
        for marker
        in causal_markers
        if marker
        in normalized
    ]

    negation = any(
        value
        in values
        for value
        in (
            "not",
            "never",
            "without",
            "refuses",
            "fails",
        )
    )

    return {
        "keywords": keywords,
        "causal_markers": causal,
        "negation": negation,
        "fingerprint": digest(
            {
                "keywords": keywords,
                "causal": causal,
                "negation": (
                    negation
                ),
            }
        ),
    }


def bucket(
    value: float,
) -> int:
    if value < 0.34:
        return 0

    if value < 0.67:
        return 1

    return 2


def behavior_cell(
    metrics: dict[str, float],
) -> str:
    return (
        "d"
        + str(
            bucket(
                metrics[
                    "baseline_divergence"
                ]
            )
        )
        + ":c"
        + str(
            bucket(
                1.0
                - metrics[
                    "cliche_risk"
                ]
            )
        )
        + ":q"
        + str(
            bucket(
                metrics[
                    "causal_coherence"
                ]
            )
        )
        + ":s"
        + str(
            bucket(
                metrics[
                    "specificity"
                ]
            )
        )
    )


def negative_knowledge_texts(
    payload: dict[str, Any],
) -> list[str]:
    negative = payload.get(
        "negative_knowledge",
        {},
    )

    if not isinstance(
        negative,
        dict,
    ):
        return []

    packets = negative.get(
        "packets",
        [],
    )

    if not isinstance(
        packets,
        list,
    ):
        return []

    output = []

    for packet in packets:
        if not isinstance(
            packet,
            dict,
        ):
            continue

        evidence = packet.get(
            "evidence",
            {},
        )

        if not isinstance(
            evidence,
            dict,
        ):
            continue

        text = str(
            evidence.get(
                "text",
                "",
            )
        ).strip()

        if text:
            output.append(
                text
            )

    return output


def validate_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    if PayloadModel is not None:
        validated = (
            PayloadModel
            .model_validate(
                payload
            )
        )

        output = (
            validated.model_dump(
                mode="python"
            )
        )

        extras = (
            validated.model_extra
            or {}
        )

        output.update(
            extras
        )

        if (
            not output[
                "candidates"
            ]
            and isinstance(
                payload.get(
                    "_realized_instances"
                ),
                list,
            )
        ):
            output[
                "candidates"
            ] = payload[
                "_realized_instances"
            ]

        return output

    subject = str(
        payload.get(
            "subject",
            "",
        )
    ).strip()

    if not subject:
        raise ValueError(
            "subject is required"
        )

    candidates = payload.get(
        "candidates",
        payload.get(
            "_realized_instances",
            [],
        ),
    )

    if not isinstance(
        candidates,
        list,
    ):
        raise TypeError(
            "candidates must be a list"
        )

    return {
        **payload,
        "subject": subject,
        "candidates": candidates,
        "baselines": (
            payload.get(
                "baselines",
                [],
            )
            if isinstance(
                payload.get(
                    "baselines",
                    [],
                ),
                list,
            )
            else []
        ),
        "cliches": (
            payload.get(
                "cliches",
                [],
            )
            if isinstance(
                payload.get(
                    "cliches",
                    [],
                ),
                list,
            )
            else []
        ),
        "constraints": (
            payload.get(
                "constraints",
                {},
            )
            if isinstance(
                payload.get(
                    "constraints",
                    {},
                ),
                dict,
            )
            else {}
        ),
    }


@dataclass(frozen=True)
class Experiment:
    candidate_id: str
    experiment_type: str
    question: str
    expected_information_gain: float
    cost: float
    risk: float
    reversibility: float
    priority: float

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "candidate_id": (
                self.candidate_id
            ),
            "experiment_type": (
                self.experiment_type
            ),
            "question": (
                self.question
            ),
            "expected_information_gain": (
                self.expected_information_gain
            ),
            "cost": self.cost,
            "risk": self.risk,
            "reversibility": (
                self.reversibility
            ),
            "priority": (
                self.priority
            ),
        }


class IdealStateEngine:
    def __init__(
        self,
        *,
        archive_size: int = 18,
        experiment_limit: int = 12,
        collapse_similarity: float = 0.86,
        minimum_elites: int = 4,
    ) -> None:
        self.archive_size = max(
            4,
            min(
                int(
                    archive_size
                ),
                128,
            ),
        )

        self.experiment_limit = max(
            1,
            min(
                int(
                    experiment_limit
                ),
                128,
            ),
        )

        self.collapse_similarity = clamp(
            collapse_similarity
        )

        self.minimum_elites = max(
            1,
            int(
                minimum_elites
            ),
        )

    def candidate_identity(
        self,
        candidate: dict[str, Any],
        index: int,
    ) -> str:
        explicit = str(
            candidate.get(
                "instance_id",
                candidate.get(
                    "candidate_id",
                    "",
                ),
            )
        ).strip()

        if explicit:
            return explicit

        return stable_id(
            "candidate",
            {
                "text": (
                    candidate.get(
                        "text",
                        ""
                    )
                ),
                "index": index,
            },
        )

    def analyze(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload = validate_payload(
            payload
        )

        subject = str(
            payload.get(
                "subject",
                "",
            )
        ).strip()

        candidates_raw = payload.get(
            "candidates",
            [],
        )

        if not candidates_raw:
            raise ValueError(
                "at least one candidate "
                "is required"
            )

        baselines = [
            str(
                value
            )
            for value
            in payload.get(
                "baselines",
                [],
            )
        ]

        cliches = [
            str(
                value
            )
            for value
            in payload.get(
                "cliches",
                [],
            )
        ]

        constraints = payload.get(
            "constraints",
            {},
        )

        if not isinstance(
            constraints,
            dict,
        ):
            constraints = {}

        negative_texts = (
            negative_knowledge_texts(
                payload
            )
        )

        normalized_candidates = []

        for index, raw in enumerate(
            candidates_raw
        ):
            if hasattr(
                raw,
                "model_dump",
            ):
                raw = raw.model_dump(
                    mode="python"
                )

            if not isinstance(
                raw,
                dict,
            ):
                continue

            text = str(
                raw.get(
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            candidate_id = (
                self.candidate_identity(
                    raw,
                    index,
                )
            )

            normalized_candidates.append(
                {
                    **raw,
                    "candidate_id": (
                        candidate_id
                    ),
                    "text": text,
                }
            )

        if not normalized_candidates:
            raise ValueError(
                "no valid candidate text"
            )

        pair_similarity: dict[
            tuple[str, str],
            float,
        ] = {}

        for left_index, left in enumerate(
            normalized_candidates
        ):
            for right in (
                normalized_candidates[
                    left_index + 1:
                ]
            ):
                key = tuple(
                    sorted(
                        (
                            left[
                                "candidate_id"
                            ],
                            right[
                                "candidate_id"
                            ],
                        )
                    )
                )

                pair_similarity[
                    key
                ] = (
                    blended_similarity(
                        left["text"],
                        right["text"],
                    )
                )

        records = []

        for candidate in (
            normalized_candidates
        ):
            candidate_id = candidate[
                "candidate_id"
            ]

            text = candidate[
                "text"
            ]

            constraint_score, (
                constraint_detail
            ) = constraint_integrity(
                text,
                constraints,
            )

            baseline_similarity = (
                max_similarity(
                    text,
                    baselines,
                )
            )

            cliche_risk = (
                phrase_pressure(
                    text,
                    cliches,
                )
            )

            negative_similarity = (
                max_similarity(
                    text,
                    negative_texts,
                )
            )

            sibling_scores = []

            for other in (
                normalized_candidates
            ):
                other_id = other[
                    "candidate_id"
                ]

                if other_id == candidate_id:
                    continue

                key = tuple(
                    sorted(
                        (
                            candidate_id,
                            other_id,
                        )
                    )
                )

                sibling_scores.append(
                    pair_similarity.get(
                        key,
                        0.0,
                    )
                )

            sibling_similarity = max(
                sibling_scores,
                default=0.0,
            )

            mechanism_novelty = clamp(
                1.0
                - sibling_similarity
            )

            causal = causal_coherence(
                text
            )

            transparency = (
                information_transparency(
                    text
                )
            )

            specificity = (
                specificity_density(
                    text
                )
            )

            entropy = lexical_entropy(
                text
            )

            assumptions = candidate.get(
                "assumptions",
                [],
            )

            if not isinstance(
                assumptions,
                list,
            ):
                assumptions = []

            fragility = (
                assumption_fragility(
                    text,
                    assumptions,
                )
            )

            baseline_divergence = clamp(
                1.0
                - baseline_similarity
            )

            anti_cliche = clamp(
                1.0
                - cliche_risk
            )

            negative_avoidance = clamp(
                1.0
                - negative_similarity
            )

            novelty_raw = mean(
                (
                    baseline_divergence,
                    mechanism_novelty,
                    entropy,
                )
            )

            survivability_proxy = mean(
                (
                    constraint_score,
                    causal,
                    transparency,
                    specificity,
                )
            )

            anti_goodhart = clamp(
                1.0
                - max(
                    0.0,
                    novelty_raw
                    - survivability_proxy
                )
                * 0.85
            )

            objective = clamp(
                (
                    constraint_score
                    * 0.22
                    + anti_cliche
                    * 0.16
                    + negative_avoidance
                    * 0.11
                    + causal
                    * 0.14
                    + baseline_divergence
                    * 0.11
                    + mechanism_novelty
                    * 0.10
                    + transparency
                    * 0.06
                    + specificity
                    * 0.05
                    + entropy
                    * 0.05
                )
                * anti_goodhart
            )

            dimensions = {
                "constraint_integrity": (
                    constraint_score
                ),
                "anti_cliche": (
                    anti_cliche
                ),
                "negative_knowledge_avoidance": (
                    negative_avoidance
                ),
                "causal_coherence": (
                    causal
                ),
                "baseline_divergence": (
                    baseline_divergence
                ),
                "mechanism_novelty": (
                    mechanism_novelty
                ),
                "information_transparency": (
                    transparency
                ),
                "specificity": (
                    specificity
                ),
                "lexical_entropy": (
                    entropy
                ),
            }

            dimension_values = list(
                dimensions.values()
            )

            dispersion = (
                statistics.pstdev(
                    dimension_values
                )
                if len(
                    dimension_values
                ) > 1
                else 0.0
            )

            uncertainty = clamp(
                (
                    dispersion * 0.55
                    + fragility * 0.25
                    + negative_similarity
                    * 0.20
                )
            )

            mechanism = (
                mechanism_fingerprint(
                    text
                )
            )

            metrics = {
                **dimensions,
                "cliche_risk": (
                    cliche_risk
                ),
                "baseline_similarity": (
                    baseline_similarity
                ),
                "negative_knowledge_similarity": (
                    negative_similarity
                ),
                "sibling_similarity": (
                    sibling_similarity
                ),
                "assumption_fragility": (
                    fragility
                ),
                "novelty_raw": (
                    novelty_raw
                ),
                "survivability_proxy": (
                    survivability_proxy
                ),
                "anti_goodhart": (
                    anti_goodhart
                ),
                "uncertainty": (
                    uncertainty
                ),
                "objective": (
                    objective
                ),
            }

            record = {
                "candidate_id": (
                    candidate_id
                ),
                "text": text,
                "fingerprint": digest(
                    {
                        "candidate_id": (
                            candidate_id
                        ),
                        "text": text,
                    }
                ),
                "metrics": metrics,
                "constraint_detail": (
                    constraint_detail
                ),
                "mechanism": (
                    mechanism
                ),
                "behavior_cell": (
                    behavior_cell(
                        metrics
                    )
                ),
                "lineage": (
                    candidate.get(
                        "lineage",
                        [],
                    )
                    if isinstance(
                        candidate.get(
                            "lineage",
                            [],
                        ),
                        list,
                    )
                    else []
                ),
                "assumptions": (
                    assumptions
                ),
                "flags": (
                    candidate.get(
                        "flags",
                        [],
                    )
                    if isinstance(
                        candidate.get(
                            "flags",
                            [],
                        ),
                        list,
                    )
                    else []
                ),
                "authority_effect": (
                    authority_effect
                ),
            }

            records.append(
                record
            )

        records.sort(
            key=lambda item: (
                -item[
                    "metrics"
                ][
                    "objective"
                ],
                item[
                    "candidate_id"
                ],
            )
        )

        pareto = (
            self.pareto_frontier(
                records
            )
        )

        quality_archive = (
            self.quality_diversity_archive(
                records
            )
        )

        novelty_archive = (
            sorted(
                records,
                key=lambda item: (
                    -item[
                        "metrics"
                    ][
                        "mechanism_novelty"
                    ],
                    -item[
                        "metrics"
                    ][
                        "baseline_divergence"
                    ],
                    item[
                        "candidate_id"
                    ],
                ),
            )[
                :self.archive_size
            ]
        )

        similarities = list(
            pair_similarity.values()
        )

        mean_pair_similarity = mean(
            similarities
        )

        maximum_pair_similarity = max(
            similarities,
            default=0.0,
        )

        archive_coverage = (
            len(
                quality_archive
            )
            / 81.0
        )

        collapse = (
            len(
                records
            ) > 2
            and (
                mean_pair_similarity
                >= self.collapse_similarity
                or (
                    maximum_pair_similarity
                    >= 0.96
                    and len(
                        quality_archive
                    ) <= 2
                )
            )
        )

        assumptions_graph = (
            self.assumption_graph(
                records
            )
        )

        lineage_graph = (
            self.lineage_graph(
                records
            )
        )

        contradictions = (
            self.contradiction_matrix(
                records,
                pair_similarity,
            )
        )

        experiments = (
            self.plan_experiments(
                records
            )
        )

        stopping = (
            self.stopping_policy(
                records,
                quality_archive,
                experiments,
                collapse,
            )
        )

        recall_query = (
            self.recall_query_packet(
                subject,
                payload,
                records,
            )
        )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "capability": (
                "ideal_state_analysis"
            ),
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "enhancement_count": len(
                enhancements
            ),
            "enhancements": list(
                enhancements
            ),
            "dependency_state": {
                "rapidfuzz": (
                    fuzz is not None
                ),
                "pydantic": (
                    BaseModel is not None
                ),
                "hypothesis": (
                    self.hypothesis_available()
                ),
                "pyribs_runtime_dependency": (
                    False
                ),
                "quality_diversity_technique": (
                    "deterministic "
                    "map-elites-style archive"
                ),
            },
            "candidate_count": len(
                records
            ),
            "ranked_candidates": (
                records
            ),
            "pareto_frontier": [
                item[
                    "candidate_id"
                ]
                for item in pareto
            ],
            "quality_diversity": {
                "archive": (
                    quality_archive
                ),
                "occupied_cells": len(
                    quality_archive
                ),
                "possible_cells": 81,
                "coverage": (
                    archive_coverage
                ),
                "mean_pair_similarity": (
                    mean_pair_similarity
                ),
                "maximum_pair_similarity": (
                    maximum_pair_similarity
                ),
                "collapse_detected": (
                    collapse
                ),
            },
            "novelty_archive": [
                {
                    "candidate_id": (
                        item[
                            "candidate_id"
                        ]
                    ),
                    "mechanism_novelty": (
                        item[
                            "metrics"
                        ][
                            "mechanism_novelty"
                        ]
                    ),
                    "baseline_divergence": (
                        item[
                            "metrics"
                        ][
                            "baseline_divergence"
                        ]
                    ),
                }
                for item
                in novelty_archive
            ],
            "assumption_graph": (
                assumptions_graph
            ),
            "lineage_graph": (
                lineage_graph
            ),
            "contradictions": (
                contradictions
            ),
            "experiments": [
                experiment.as_dict()
                for experiment
                in experiments
            ],
            "stopping_policy": (
                stopping
            ),
            "scrybe_recall_query": (
                recall_query
            ),
            "invariants": {
                "projection_only": True,
                "authority_effect_none": True,
                "no_canon_admission": True,
                "no_evidence_admission": True,
                "no_coda_mutation": True,
                "no_memory_store_created": True,
                "no_provider_execution": True,
                "novelty_is_not_authority": True,
                "quality_is_not_authority": True,
                "failure_is_not_fact": True,
                "deterministic_archive": True,
                "deterministic_fingerprints": True,
                "dependency_fallbacks_preserve_core": True,
            },
        }

        result[
            "fingerprint"
        ] = digest(
            {
                "schema": (
                    schema_version
                ),
                "subject": subject,
                "ranked_candidates": (
                    records
                ),
                "pareto_frontier": (
                    result[
                        "pareto_frontier"
                    ]
                ),
                "quality_diversity": (
                    result[
                        "quality_diversity"
                    ]
                ),
                "experiments": (
                    result[
                        "experiments"
                    ]
                ),
                "stopping_policy": (
                    stopping
                ),
            }
        )

        return result

    @staticmethod
    def hypothesis_available() -> bool:
        try:
            import hypothesis
            return bool(
                hypothesis
            )
        except ImportError:
            return False

    @staticmethod
    def dominates(
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> bool:
        left_metrics = left[
            "metrics"
        ]

        right_metrics = right[
            "metrics"
        ]

        dimensions = (
            "objective",
            "constraint_integrity",
            "anti_cliche",
            "mechanism_novelty",
            "causal_coherence",
        )

        all_at_least = all(
            left_metrics[
                dimension
            ]
            >= right_metrics[
                dimension
            ]
            for dimension
            in dimensions
        )

        any_greater = any(
            left_metrics[
                dimension
            ]
            > right_metrics[
                dimension
            ]
            for dimension
            in dimensions
        )

        return (
            all_at_least
            and any_greater
        )

    def pareto_frontier(
        self,
        records: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        frontier = []

        for candidate in records:
            dominated = any(
                self.dominates(
                    other,
                    candidate,
                )
                for other in records
                if other is not candidate
            )

            if not dominated:
                frontier.append(
                    candidate
                )

        frontier.sort(
            key=lambda item: (
                -item[
                    "metrics"
                ][
                    "objective"
                ],
                item[
                    "candidate_id"
                ],
            )
        )

        return frontier

    def quality_diversity_archive(
        self,
        records: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        cells: dict[
            str,
            dict[str, Any],
        ] = {}

        for record in records:
            cell = record[
                "behavior_cell"
            ]

            incumbent = cells.get(
                cell
            )

            if (
                incumbent is None
                or (
                    record[
                        "metrics"
                    ][
                        "objective"
                    ],
                    -record[
                        "metrics"
                    ][
                        "uncertainty"
                    ],
                    record[
                        "candidate_id"
                    ],
                )
                > (
                    incumbent[
                        "metrics"
                    ][
                        "objective"
                    ],
                    -incumbent[
                        "metrics"
                    ][
                        "uncertainty"
                    ],
                    incumbent[
                        "candidate_id"
                    ],
                )
            ):
                cells[
                    cell
                ] = record

        archive = [
            {
                "cell": cell,
                "candidate_id": (
                    record[
                        "candidate_id"
                    ]
                ),
                "objective": (
                    record[
                        "metrics"
                    ][
                        "objective"
                    ]
                ),
                "uncertainty": (
                    record[
                        "metrics"
                    ][
                        "uncertainty"
                    ]
                ),
            }
            for cell, record
            in sorted(
                cells.items()
            )
        ]

        return archive

    @staticmethod
    def assumption_graph(
        records: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        nodes = []
        edges = []
        seen = set()

        for record in records:
            candidate_id = record[
                "candidate_id"
            ]

            nodes.append(
                {
                    "id": candidate_id,
                    "type": "candidate",
                }
            )

            for assumption in record[
                "assumptions"
            ]:
                text = str(
                    assumption
                ).strip()

                if not text:
                    continue

                assumption_id = stable_id(
                    "assumption",
                    text.casefold(),
                )

                if assumption_id not in seen:
                    seen.add(
                        assumption_id
                    )

                    nodes.append(
                        {
                            "id": (
                                assumption_id
                            ),
                            "type": (
                                "assumption"
                            ),
                            "text": text,
                        }
                    )

                edges.append(
                    {
                        "source": (
                            candidate_id
                        ),
                        "target": (
                            assumption_id
                        ),
                        "type": (
                            "candidate_uses_assumption"
                        ),
                    }
                )

        return {
            "nodes": nodes,
            "edges": edges,
        }

    @staticmethod
    def lineage_graph(
        records: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        nodes = {}
        edges = []

        for record in records:
            candidate_id = record[
                "candidate_id"
            ]

            nodes[
                candidate_id
            ] = {
                "id": candidate_id,
                "type": "candidate",
            }

            lineage = record.get(
                "lineage",
                [],
            )

            previous = None

            for identity in lineage:
                identity = str(
                    identity
                ).strip()

                if not identity:
                    continue

                nodes.setdefault(
                    identity,
                    {
                        "id": identity,
                        "type": (
                            "lineage_instance"
                        ),
                    },
                )

                if previous is not None:
                    edges.append(
                        {
                            "source": (
                                previous
                            ),
                            "target": (
                                identity
                            ),
                            "type": (
                                "lineage"
                            ),
                        }
                    )

                previous = identity

            if previous is not None:
                edges.append(
                    {
                        "source": previous,
                        "target": (
                            candidate_id
                        ),
                        "type": (
                            "lineage"
                        ),
                    }
                )

        return {
            "nodes": [
                nodes[
                    key
                ]
                for key
                in sorted(
                    nodes
                )
            ],
            "edges": edges,
        }

    @staticmethod
    def contradiction_matrix(
        records: list[
            dict[str, Any]
        ],
        similarities: dict[
            tuple[str, str],
            float,
        ],
    ) -> list[
        dict[str, Any]
    ]:
        output = []

        index = {
            record[
                "candidate_id"
            ]: record
            for record in records
        }

        for (
            left_id,
            right_id,
        ), similarity in sorted(
            similarities.items()
        ):
            left = index[
                left_id
            ]

            right = index[
                right_id
            ]

            objective_gap = abs(
                left[
                    "metrics"
                ][
                    "objective"
                ]
                - right[
                    "metrics"
                ][
                    "objective"
                ]
            )

            constraint_gap = abs(
                left[
                    "metrics"
                ][
                    "constraint_integrity"
                ]
                - right[
                    "metrics"
                ][
                    "constraint_integrity"
                ]
            )

            causal_gap = abs(
                left[
                    "metrics"
                ][
                    "causal_coherence"
                ]
                - right[
                    "metrics"
                ][
                    "causal_coherence"
                ]
            )

            tension = clamp(
                similarity
                * mean(
                    (
                        objective_gap,
                        constraint_gap,
                        causal_gap,
                    )
                )
            )

            if tension >= 0.18:
                output.append(
                    {
                        "left": left_id,
                        "right": (
                            right_id
                        ),
                        "semantic_similarity": (
                            similarity
                        ),
                        "objective_gap": (
                            objective_gap
                        ),
                        "constraint_gap": (
                            constraint_gap
                        ),
                        "causal_gap": (
                            causal_gap
                        ),
                        "tension": (
                            tension
                        ),
                    }
                )

        output.sort(
            key=lambda item: (
                -item[
                    "tension"
                ],
                item[
                    "left"
                ],
                item[
                    "right"
                ],
            )
        )

        return output

    def plan_experiments(
        self,
        records: list[
            dict[str, Any]
        ],
    ) -> list[Experiment]:
        templates = (
            (
                "cliche_collision",
                (
                    "Does the candidate still "
                    "depend on a familiar "
                    "cliche mechanism after "
                    "surface wording is removed?"
                ),
                0.20,
                0.05,
                1.00,
                "cliche_risk",
            ),
            (
                "baseline_dependence",
                (
                    "If the supplied baseline "
                    "is removed, does the idea "
                    "remain structurally "
                    "interesting?"
                ),
                0.18,
                0.03,
                1.00,
                "baseline_similarity",
            ),
            (
                "causal_falsification",
                (
                    "Can the decisive causal "
                    "link be removed without "
                    "collapsing the candidate?"
                ),
                0.28,
                0.08,
                1.00,
                "causal_coherence",
            ),
            (
                "constraint_escape",
                (
                    "Does the candidate satisfy "
                    "the hard constraints in "
                    "substance rather than by "
                    "word matching?"
                ),
                0.24,
                0.06,
                1.00,
                "constraint_integrity",
            ),
            (
                "negative_knowledge_recurrence",
                (
                    "Is this candidate repeating "
                    "a previously failed "
                    "mechanism under new prose?"
                ),
                0.16,
                0.03,
                1.00,
                "negative_knowledge_similarity",
            ),
            (
                "counterfactual_robustness",
                (
                    "If one major assumption is "
                    "inverted, does the candidate "
                    "retain a coherent mechanism?"
                ),
                0.32,
                0.10,
                0.95,
                "assumption_fragility",
            ),
        )

        experiments = []

        for record in records:
            candidate_id = record[
                "candidate_id"
            ]

            metrics = record[
                "metrics"
            ]

            uncertainty = metrics[
                "uncertainty"
            ]

            for (
                experiment_type,
                question,
                cost,
                risk,
                reversibility,
                target_metric,
            ) in templates:

                if target_metric in (
                    "cliche_risk",
                    "baseline_similarity",
                    "negative_knowledge_similarity",
                    "assumption_fragility",
                ):
                    target_uncertainty = (
                        metrics[
                            target_metric
                        ]
                    )
                else:
                    target_uncertainty = (
                        1.0
                        - metrics[
                            target_metric
                        ]
                    )

                information_gain = clamp(
                    (
                        uncertainty
                        * 0.55
                        + target_uncertainty
                        * 0.45
                    )
                )

                denominator = max(
                    0.05,
                    cost
                    + risk
                    + (
                        1.0
                        - reversibility
                    )
                    * 0.50,
                )

                priority = (
                    information_gain
                    / denominator
                )

                experiments.append(
                    Experiment(
                        candidate_id=(
                            candidate_id
                        ),
                        experiment_type=(
                            experiment_type
                        ),
                        question=question,
                        expected_information_gain=(
                            information_gain
                        ),
                        cost=cost,
                        risk=risk,
                        reversibility=(
                            reversibility
                        ),
                        priority=(
                            priority
                        ),
                    )
                )

        experiments.sort(
            key=lambda item: (
                -item.priority,
                item.candidate_id,
                item.experiment_type,
            )
        )

        return experiments[
            :self.experiment_limit
        ]

    def stopping_policy(
        self,
        records: list[
            dict[str, Any]
        ],
        archive: list[
            dict[str, Any]
        ],
        experiments: list[
            Experiment
        ],
        collapse: bool,
    ) -> dict[str, Any]:
        strong = [
            record
            for record in records
            if (
                record[
                    "metrics"
                ][
                    "objective"
                ]
                >= 0.68
                and record[
                    "metrics"
                ][
                    "constraint_integrity"
                ]
                >= 0.85
                and record[
                    "metrics"
                ][
                    "anti_cliche"
                ]
                >= 0.65
            )
        ]

        unresolved_information = max(
            (
                experiment
                .expected_information_gain
                for experiment
                in experiments
            ),
            default=0.0,
        )

        stop = (
            len(
                strong
            )
            >= self.minimum_elites
            and len(
                archive
            )
            >= self.minimum_elites
            and not collapse
            and unresolved_information
            < 0.58
        )

        reasons = []

        if len(
            strong
        ) < self.minimum_elites:
            reasons.append(
                "insufficient_strong_elites"
            )

        if len(
            archive
        ) < self.minimum_elites:
            reasons.append(
                "insufficient_behavioral_coverage"
            )

        if collapse:
            reasons.append(
                "diversity_collapse"
            )

        if unresolved_information >= 0.58:
            reasons.append(
                "high_information_gain_tests_remain"
            )

        if stop:
            reasons.append(
                "bounded_completion_condition_met"
            )

        return {
            "stop": stop,
            "strong_elite_count": len(
                strong
            ),
            "archive_cell_count": len(
                archive
            ),
            "maximum_remaining_information_gain": (
                unresolved_information
            ),
            "reasons": reasons,
        }

    @staticmethod
    def recall_query_packet(
        subject: str,
        payload: dict[str, Any],
        records: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        negative = payload.get(
            "negative_knowledge",
            {},
        )

        mechanisms = []

        if isinstance(
            negative,
            dict,
        ):
            counts = negative.get(
                "mechanism_counts",
                {},
            )

            if isinstance(
                counts,
                dict,
            ):
                mechanisms = [
                    key
                    for key, _
                    in sorted(
                        counts.items(),
                        key=lambda item: (
                            -int(
                                item[
                                    1
                                ]
                            ),
                            str(
                                item[
                                    0
                                ]
                            ),
                        ),
                    )[:8]
                ]

        weak = [
            record
            for record in records
            if (
                record[
                    "metrics"
                ][
                    "objective"
                ]
                < 0.50
                or record[
                    "metrics"
                ][
                    "cliche_risk"
                ]
                > 0.60
            )
        ]

        query = (
            "underscore vessel negative "
            "knowledge for "
            + subject
        )

        if mechanisms:
            query += (
                "; failed mechanisms: "
                + ", ".join(
                    mechanisms
                )
            )

        return {
            "query": query,
            "limit": 9,
            "memory_type": None,
            "authority_effect": "none",
            "consumer": "underscore",
            "purpose": (
                "avoid_repeated_divergence_failures"
            ),
            "weak_candidate_count": len(
                weak
            ),
            "direct_write_requested": False,
        }


def self_check() -> dict[str, Any]:
    payload = {
        "subject": (
            "subvert a conventional "
            "victory ending"
        ),
        "baselines": [
            (
                "the hero defeats the enemy "
                "and receives the reward"
            )
        ],
        "cliches": [
            "it was all a dream",
            "secret identity reveal",
            "last-second rescue",
        ],
        "constraints": {
            "required": [],
            "forbidden": [
                "dream",
            ],
        },
        "negative_knowledge": {
            "mechanism_counts": {
                "cliche_pressure": 2,
            },
            "packets": [
                {
                    "evidence": {
                        "text": (
                            "the hero secretly "
                            "has another identity"
                        )
                    }
                }
            ],
        },
        "candidates": [
            {
                "instance_id": "candidate_1",
                "text": (
                    "The victor discovers that "
                    "winning activated the rule "
                    "that transfers command to "
                    "the defeated side because "
                    "the treaty defines victory "
                    "as proof of instability."
                ),
                "assumptions": [
                    (
                        "victory grants control"
                    )
                ],
                "lineage": [
                    "assignment_1"
                ],
            },
            {
                "instance_id": "candidate_2",
                "text": (
                    "The hero wins, everyone "
                    "celebrates, and a secret "
                    "identity is revealed."
                ),
                "assumptions": [],
                "lineage": [
                    "assignment_2"
                ],
            },
            {
                "instance_id": "candidate_3",
                "text": (
                    "The enemy deliberately "
                    "loses because defeat is "
                    "the only legal mechanism "
                    "that permits it to appoint "
                    "the next government."
                ),
                "assumptions": [
                    (
                        "losing removes agency"
                    )
                ],
                "lineage": [
                    "assignment_3"
                ],
            },
            {
                "instance_id": "candidate_4",
                "text": (
                    "The winner refuses the "
                    "reward, not from morality, "
                    "but because accepting it "
                    "would legally validate the "
                    "enemy's original claim."
                ),
                "assumptions": [
                    (
                        "reward acceptance "
                        "confirms success"
                    )
                ],
                "lineage": [
                    "assignment_4"
                ],
            },
        ],
    }

    engine = (
        IdealStateEngine(
            archive_size=12,
            experiment_limit=8,
            minimum_elites=2,
        )
    )

    first = engine.analyze(
        payload
    )

    second = engine.analyze(
        payload
    )

    if (
        first[
            "fingerprint"
        ]
        != second[
            "fingerprint"
        ]
    ):
        raise RuntimeError(
            "determinism failed"
        )

    if (
        first[
            "authority_effect"
        ]
        != "none"
    ):
        raise RuntimeError(
            "authority invariant failed"
        )

    if (
        first[
            "candidate_count"
        ]
        != 4
    ):
        raise RuntimeError(
            "candidate count failed"
        )

    if (
        first[
            "enhancement_count"
        ]
        < 20
    ):
        raise RuntimeError(
            "enhancement coverage failed"
        )

    if not first[
        "quality_diversity"
    ][
        "archive"
    ]:
        raise RuntimeError(
            "quality diversity archive failed"
        )

    if not first[
        "pareto_frontier"
    ]:
        raise RuntimeError(
            "pareto frontier failed"
        )

    if first[
        "scrybe_recall_query"
    ][
        "direct_write_requested"
    ]:
        raise RuntimeError(
            "memory ownership failed"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "enhancement_count": (
            first[
                "enhancement_count"
            ]
        ),
        "candidate_count": (
            first[
                "candidate_count"
            ]
        ),
        "pareto_count": len(
            first[
                "pareto_frontier"
            ]
        ),
        "archive_cells": (
            first[
                "quality_diversity"
            ][
                "occupied_cells"
            ]
        ),
        "experiment_count": len(
            first[
                "experiments"
            ]
        ),
        "rapidfuzz": (
            first[
                "dependency_state"
            ][
                "rapidfuzz"
            ]
        ),
        "pydantic": (
            first[
                "dependency_state"
            ][
                "pydantic"
            ]
        ),
        "hypothesis": (
            first[
                "dependency_state"
            ][
                "hypothesis"
            ]
        ),
        "fingerprint": (
            first[
                "fingerprint"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-vessel-ideal-state"
        ),
        description=(
            "advanced non-authoritative "
            "quality-diversity and "
            "falsification analysis for "
            "underscore vessel candidates"
        ),
    )

    parser.add_argument(
        "--archive-size",
        type=int,
        default=18,
    )

    parser.add_argument(
        "--experiment-limit",
        type=int,
        default=12,
    )

    parser.add_argument(
        "--collapse-similarity",
        type=float,
        default=0.86,
    )

    parser.add_argument(
        "--minimum-elites",
        type=int,
        default=4,
    )

    commands = (
        parser.add_subparsers(
            dest="action",
            required=True,
        )
    )

    analyze = commands.add_parser(
        "analyze"
    )

    analyze.add_argument(
        "--input",
        required=True,
    )

    commands.add_parser(
        "self-check"
    )

    return parser


def main() -> int:
    args = (
        build_parser()
        .parse_args()
    )

    if args.action == (
        "self-check"
    ):
        result = self_check()

    elif args.action == (
        "analyze"
    ):
        engine = (
            IdealStateEngine(
                archive_size=(
                    args.archive_size
                ),
                experiment_limit=(
                    args.experiment_limit
                ),
                collapse_similarity=(
                    args.collapse_similarity
                ),
                minimum_elites=(
                    args.minimum_elites
                ),
            )
        )

        result = engine.analyze(
            load_json(
                args.input
            )
        )

    else:
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
