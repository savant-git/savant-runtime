#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


runtime_root = Path("/root/savant-runtime")

underscore_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "underscore"
)

vessel_root = underscore_root / "runtime" / "vessel"
database_path = vessel_root / "vessel.sqlite3"

schema_version = "savant.underscore.vessel.v1"
authority_effect = "none"

default_similarity_threshold = 0.74
default_cliche_threshold = 0.68
default_frontier_size = 7
default_mutation_depth = 2
default_mmr_lambda = 0.68


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
    width: int = 24,
) -> str:
    return f"{prefix}_{fingerprint(value)[:width]}"


def now_ns() -> int:
    return time.time_ns()


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def normalize_text(value: str) -> str:
    value = value.casefold()
    value = re.sub(
        r"[^\w\s'-]+",
        " ",
        value,
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    )
    return value.strip()


def tokens(value: str) -> list[str]:
    return re.findall(
        r"[a-z0-9][a-z0-9'-]*",
        normalize_text(value),
    )


def token_set(value: str) -> set[str]:
    return {
        token
        for token in tokens(value)
        if len(token) >= 2
    }


def ngrams(
    value: str,
    width: int,
) -> set[tuple[str, ...]]:
    values = tokens(value)

    if len(values) < width:
        return set()

    return {
        tuple(values[index : index + width])
        for index in range(
            len(values) - width + 1
        )
    }


def jaccard(
    left: Iterable[Any],
    right: Iterable[Any],
) -> float:
    a = set(left)
    b = set(right)

    if not a and not b:
        return 1.0

    union = a | b

    if not union:
        return 0.0

    return len(a & b) / len(union)


def fuzzy_similarity(
    left: str,
    right: str,
) -> float:
    if not left and not right:
        return 1.0

    if fuzz is not None:
        scores = (
            fuzz.ratio(
                left,
                right,
            ),
            fuzz.token_set_ratio(
                left,
                right,
            ),
            fuzz.WRatio(
                left,
                right,
            ),
        )

        return max(scores) / 100.0

    return SequenceMatcher(
        None,
        normalize_text(left),
        normalize_text(right),
    ).ratio()


def blended_similarity(
    left: str,
    right: str,
) -> float:
    token_similarity = jaccard(
        token_set(left),
        token_set(right),
    )

    bigram_similarity = jaccard(
        ngrams(left, 2),
        ngrams(right, 2),
    )

    fuzzy = fuzzy_similarity(
        left,
        right,
    )

    return clamp(
        fuzzy * 0.52
        + token_similarity * 0.28
        + bigram_similarity * 0.20
    )


def lexical_entropy(value: str) -> float:
    values = tokens(value)

    if not values:
        return 0.0

    counts = Counter(values)
    total = len(values)

    entropy = 0.0

    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(
            probability
        )

    maximum = math.log2(
        max(len(counts), 2)
    )

    if maximum <= 0:
        return 0.0

    return clamp(
        entropy / maximum
    )


def repetition_penalty(value: str) -> float:
    values = tokens(value)

    if len(values) < 4:
        return 0.0

    counts = Counter(values)
    repeated = sum(
        max(count - 1, 0)
        for count in counts.values()
    )

    return clamp(
        repeated / len(values)
    )


def phrase_density(
    value: str,
    phrases: Sequence[str],
) -> tuple[float, list[dict[str, Any]]]:
    matches = []

    for phrase in phrases:
        phrase = phrase.strip()

        if not phrase:
            continue

        similarity = blended_similarity(
            value,
            phrase,
        )

        normalized_phrase = normalize_text(
            phrase
        )

        direct = (
            normalized_phrase
            and normalized_phrase
            in normalize_text(value)
        )

        score = max(
            similarity,
            1.0 if direct else 0.0,
        )

        if score >= 0.45:
            matches.append(
                {
                    "phrase": phrase,
                    "similarity": round(
                        score,
                        6,
                    ),
                    "direct": direct,
                }
            )

    matches.sort(
        key=lambda item: (
            -item["similarity"],
            item["phrase"],
        )
    )

    if not matches:
        return 0.0, []

    weighted = sum(
        item["similarity"]
        for item in matches[:5]
    ) / min(
        len(matches),
        5,
    )

    return clamp(weighted), matches


def constraint_coverage(
    value: str,
    required: Sequence[str],
    forbidden: Sequence[str],
) -> tuple[float, list[str], list[str]]:
    normalized = normalize_text(value)

    missing = []
    violations = []

    for term in required:
        term = normalize_text(term)

        if term and term not in normalized:
            missing.append(term)

    for term in forbidden:
        term = normalize_text(term)

        if term and term in normalized:
            violations.append(term)

    required_score = 1.0

    if required:
        required_score = (
            len(required) - len(missing)
        ) / len(required)

    forbidden_score = 1.0

    if forbidden:
        forbidden_score = (
            len(forbidden) - len(violations)
        ) / len(forbidden)

    return (
        clamp(
            required_score * 0.65
            + forbidden_score * 0.35
        ),
        missing,
        violations,
    )


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    text: str
    source: str
    lineage: list[str]


@dataclass
class CandidateScore:
    candidate_id: str
    text: str
    source: str
    lineage: list[str]

    cliche_similarity: float
    cliche_risk: float

    baseline_similarity: float
    baseline_distance: float

    sibling_similarity: float
    sibling_distance: float

    lexical_entropy: float
    repetition_penalty: float

    constraint_score: float

    divergence_score: float
    subversion_score: float
    survivability_score: float

    missing_constraints: list[str]
    forbidden_violations: list[str]

    cliche_matches: list[dict[str, Any]]
    discriminants: list[dict[str, Any]]

    flags: list[str]


mutation_operators: tuple[
    tuple[str, str],
    ...,
] = (
    (
        "invert_expectation",
        "Reverse the expected outcome while preserving every established cause.",
    ),
    (
        "invert_agency",
        "Give the decisive action to the character or system least expected to possess agency.",
    ),
    (
        "invert_reward",
        "Make achieving the apparent goal create the central loss instead of resolving it.",
    ),
    (
        "remove_payoff",
        "Remove the expected emotional or practical payoff and make the absence causally meaningful.",
    ),
    (
        "swap_cause_effect",
        "Reframe the supposed consequence as the actual cause and rebuild the chain consistently.",
    ),
    (
        "change_scale",
        "Translate the mechanism to a radically different scale without changing its governing logic.",
    ),
    (
        "temporal_dislocation",
        "Move the decisive event earlier or later and let consequences reveal it indirectly.",
    ),
    (
        "false_binary",
        "Assume the apparent either-or choice is structurally false and derive a third mechanism.",
    ),
    (
        "literalize_metaphor",
        "Convert the governing metaphor into an actual causal mechanism without turning it into a gag.",
    ),
    (
        "abstract_literal",
        "Convert the obvious literal mechanism into a structural or relational mechanism.",
    ),
    (
        "constraint_as_engine",
        "Make the hardest constraint generate the solution rather than merely obstruct it.",
    ),
    (
        "preserve_surface_change_engine",
        "Keep the familiar surface form but replace the mechanism producing it.",
    ),
    (
        "preserve_engine_change_surface",
        "Keep the causal mechanism but express it through an unfamiliar surface form.",
    ),
    (
        "remove_explanation",
        "Remove explanatory material and require the structure itself to reveal the truth.",
    ),
    (
        "hostile_reading",
        "Interpret every convenient assumption in the least charitable internally consistent way.",
    ),
    (
        "beneficial_failure",
        "Make the apparent failure create the only route to the deeper objective.",
    ),
    (
        "cost_transfer",
        "Preserve the victory but move its cost onto a different dimension, party, or timescale.",
    ),
    (
        "identity_exchange",
        "Exchange the structural roles of two participants while preserving their established traits.",
    ),
    (
        "information_asymmetry",
        "Change who knows the decisive fact and derive consequences without adding arbitrary secrecy.",
    ),
    (
        "negative_space",
        "Build the outcome around what never happens, while keeping the absence causally legible.",
    ),
    (
        "self_refutation",
        "Make the strategy succeed in a way that disproves the belief that motivated it.",
    ),
    (
        "orthogonal_solution",
        "Solve the actual underlying problem without directly addressing the apparent problem.",
    ),
    (
        "mechanism_substitution",
        "Replace the most genre-typical mechanism with a different mechanism producing equivalent pressure.",
    ),
    (
        "value_collision",
        "Force two independently defensible values to become mutually incompatible.",
    ),
    (
        "recursive_consequence",
        "Make the solution recreate the original problem at a higher structural level.",
    ),
    (
        "symmetry_break",
        "Establish an apparent symmetry and violate it at the precise point the audience expects completion.",
    ),
    (
        "mundane_causality",
        "Replace a dramatic explanation with an ordinary mechanism whose consequences are more disturbing.",
    ),
    (
        "extreme_specificity",
        "Replace generic motivation with one highly specific causal detail that changes the structure.",
    ),
    (
        "deferred_meaning",
        "Let an early mundane event acquire its true meaning only after later consequences.",
    ),
    (
        "category_error",
        "Test whether the problem has been placed in the wrong conceptual category entirely.",
    ),
)


class VesselStore:
    def __init__(
        self,
        path: Path = database_path,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            str(path)
        )

        self.connection.row_factory = (
            sqlite3.Row
        )

        self.connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        self.connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        self.connection.execute(
            "PRAGMA busy_timeout=5000"
        )

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS vessel_runs (
                run_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                created_ns INTEGER NOT NULL,
                schema_version TEXT NOT NULL,
                authority_effect TEXT NOT NULL,
                subject TEXT NOT NULL,
                input_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS vessel_runs_fingerprint_idx
            ON vessel_runs(fingerprint);

            CREATE TABLE IF NOT EXISTS vessel_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                created_ns INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                segue_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(run_id)
                    REFERENCES vessel_runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS vessel_events_run_idx
            ON vessel_events(run_id, event_id);
            """
        )

        self.connection.commit()

    def save_run(
        self,
        run_id: str,
        run_fingerprint: str,
        subject: str,
        payload: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO vessel_runs (
                run_id,
                fingerprint,
                created_ns,
                schema_version,
                authority_effect,
                subject,
                input_json,
                result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_fingerprint,
                now_ns(),
                schema_version,
                authority_effect,
                subject,
                canonical_json(payload),
                canonical_json(result),
            ),
        )

        self.connection.commit()

    def event(
        self,
        run_id: str,
        event_type: str,
        segue_type: str,
        payload: Any,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO vessel_events (
                run_id,
                created_ns,
                event_type,
                segue_type,
                payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                now_ns(),
                event_type,
                segue_type,
                canonical_json(payload),
            ),
        )

        self.connection.commit()

    def replay(
        self,
        run_id: str,
    ) -> dict[str, Any] | None:
        run = self.connection.execute(
            """
            SELECT *
            FROM vessel_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        if run is None:
            return None

        events = self.connection.execute(
            """
            SELECT *
            FROM vessel_events
            WHERE run_id = ?
            ORDER BY event_id
            """,
            (run_id,),
        ).fetchall()

        return {
            "run": dict(run),
            "events": [
                dict(row)
                for row in events
            ],
        }


class Vessel:
    def __init__(
        self,
        *,
        cliche_threshold: float,
        similarity_threshold: float,
        frontier_size: int,
        mmr_lambda: float,
    ) -> None:
        self.cliche_threshold = clamp(
            cliche_threshold
        )

        self.similarity_threshold = clamp(
            similarity_threshold
        )

        self.frontier_size = max(
            frontier_size,
            1,
        )

        self.mmr_lambda = clamp(
            mmr_lambda
        )

        self.store = VesselStore()

    @staticmethod
    def _candidate(
        value: Any,
        index: int,
    ) -> Candidate:
        if isinstance(
            value,
            str,
        ):
            text = value.strip()
            source = "supplied"
            lineage = []

        elif isinstance(
            value,
            dict,
        ):
            text = str(
                value.get(
                    "text",
                    "",
                )
            ).strip()

            source = str(
                value.get(
                    "source",
                    "supplied",
                )
            ).strip() or "supplied"

            lineage = [
                str(item).strip()
                for item
                in value.get(
                    "lineage",
                    [],
                )
                if str(item).strip()
            ]

        else:
            raise TypeError(
                "candidate must be string or object"
            )

        if not text:
            raise ValueError(
                f"candidate {index} is empty"
            )

        return Candidate(
            candidate_id=stable_id(
                "candidate",
                {
                    "index": index,
                    "text": normalize_text(
                        text
                    ),
                },
            ),
            text=text,
            source=source,
            lineage=lineage,
        )

    @staticmethod
    def _max_similarity(
        value: str,
        references: Sequence[str],
    ) -> float:
        if not references:
            return 0.0

        return max(
            blended_similarity(
                value,
                reference,
            )
            for reference
            in references
            if reference.strip()
        )

    def _sibling_similarity(
        self,
        candidate: Candidate,
        candidates: Sequence[Candidate],
    ) -> float:
        siblings = [
            other
            for other in candidates
            if (
                other.candidate_id
                != candidate.candidate_id
            )
        ]

        if not siblings:
            return 0.0

        return max(
            blended_similarity(
                candidate.text,
                sibling.text,
            )
            for sibling in siblings
        )

    @staticmethod
    def _discriminants(
        candidate: Candidate,
        *,
        cliche_similarity: float,
        baseline_similarity: float,
        sibling_similarity: float,
        constraint_score: float,
    ) -> list[dict[str, Any]]:
        output = []

        if cliche_similarity >= 0.68:
            output.append(
                {
                    "test": (
                        "Replace the surface details while preserving "
                        "the mechanism. If it immediately resembles a "
                        "known cliché, the mechanism itself is conventional."
                    ),
                    "targets": [
                        "cliche_mechanism",
                    ],
                }
            )

        if baseline_similarity >= 0.72:
            output.append(
                {
                    "test": (
                        "Remove all stylistic wording and compare only "
                        "cause, agency, consequence, and resolution."
                    ),
                    "targets": [
                        "baseline_dependence",
                    ],
                }
            )

        if sibling_similarity >= 0.76:
            output.append(
                {
                    "test": (
                        "State the decisive causal difference between "
                        "this candidate and its nearest sibling in one sentence."
                    ),
                    "targets": [
                        "false_diversity",
                    ],
                }
            )

        if constraint_score < 0.70:
            output.append(
                {
                    "test": (
                        "Re-run the candidate with all hard constraints "
                        "held fixed and reject any novelty created by violating them."
                    ),
                    "targets": [
                        "constraint_escape",
                    ],
                }
            )

        output.append(
            {
                "test": (
                    "Ask what the audience or operator predicts next, "
                    "then identify the exact causal mechanism that invalidates "
                    "that prediction without withholding necessary information."
                ),
                "targets": [
                    "earned_subversion",
                ],
            }
        )

        return output

    def _score(
        self,
        candidate: Candidate,
        candidates: Sequence[Candidate],
        *,
        cliches: Sequence[str],
        baselines: Sequence[str],
        required: Sequence[str],
        forbidden: Sequence[str],
    ) -> CandidateScore:
        cliche_similarity = (
            self._max_similarity(
                candidate.text,
                cliches,
            )
        )

        cliche_density, cliche_matches = (
            phrase_density(
                candidate.text,
                cliches,
            )
        )

        cliche_risk = clamp(
            cliche_similarity * 0.66
            + cliche_density * 0.34
        )

        baseline_similarity = (
            self._max_similarity(
                candidate.text,
                baselines,
            )
        )

        baseline_distance = (
            1.0
            - baseline_similarity
        )

        sibling_similarity = (
            self._sibling_similarity(
                candidate,
                candidates,
            )
        )

        sibling_distance = (
            1.0
            - sibling_similarity
        )

        entropy = lexical_entropy(
            candidate.text
        )

        repetition = repetition_penalty(
            candidate.text
        )

        (
            constraint_score,
            missing,
            violations,
        ) = constraint_coverage(
            candidate.text,
            required,
            forbidden,
        )

        divergence_score = clamp(
            baseline_distance * 0.42
            + sibling_distance * 0.28
            + entropy * 0.20
            + (1.0 - repetition) * 0.10
        )

        subversion_score = clamp(
            divergence_score * 0.52
            + (1.0 - cliche_risk) * 0.38
            + constraint_score * 0.10
        )

        novelty_without_structure = max(
            divergence_score
            - constraint_score,
            0.0,
        )

        survivability_score = clamp(
            subversion_score * 0.52
            + constraint_score * 0.30
            + (1.0 - cliche_risk) * 0.18
            - novelty_without_structure * 0.22
        )

        flags = []

        if cliche_risk >= self.cliche_threshold:
            flags.append(
                "cliche_pressure"
            )

        if baseline_similarity >= (
            self.similarity_threshold
        ):
            flags.append(
                "baseline_convergence"
            )

        if sibling_similarity >= (
            self.similarity_threshold
        ):
            flags.append(
                "false_diversity"
            )

        if constraint_score < 0.70:
            flags.append(
                "constraint_escape"
            )

        if repetition >= 0.30:
            flags.append(
                "lexical_repetition"
            )

        if (
            divergence_score >= 0.75
            and survivability_score < 0.55
        ):
            flags.append(
                "novelty_without_survival"
            )

        if (
            cliche_risk < 0.45
            and survivability_score >= 0.72
        ):
            flags.append(
                "strong_subversion_candidate"
            )

        return CandidateScore(
            candidate_id=(
                candidate.candidate_id
            ),
            text=candidate.text,
            source=candidate.source,
            lineage=candidate.lineage,

            cliche_similarity=round(
                cliche_similarity,
                6,
            ),
            cliche_risk=round(
                cliche_risk,
                6,
            ),

            baseline_similarity=round(
                baseline_similarity,
                6,
            ),
            baseline_distance=round(
                baseline_distance,
                6,
            ),

            sibling_similarity=round(
                sibling_similarity,
                6,
            ),
            sibling_distance=round(
                sibling_distance,
                6,
            ),

            lexical_entropy=round(
                entropy,
                6,
            ),
            repetition_penalty=round(
                repetition,
                6,
            ),

            constraint_score=round(
                constraint_score,
                6,
            ),

            divergence_score=round(
                divergence_score,
                6,
            ),
            subversion_score=round(
                subversion_score,
                6,
            ),
            survivability_score=round(
                survivability_score,
                6,
            ),

            missing_constraints=missing,
            forbidden_violations=violations,

            cliche_matches=cliche_matches,

            discriminants=self._discriminants(
                candidate,
                cliche_similarity=cliche_similarity,
                baseline_similarity=baseline_similarity,
                sibling_similarity=sibling_similarity,
                constraint_score=constraint_score,
            ),

            flags=flags,
        )

    def _mmr_frontier(
        self,
        scores: Sequence[CandidateScore],
    ) -> list[CandidateScore]:
        remaining = list(scores)
        selected = []

        while (
            remaining
            and len(selected)
            < self.frontier_size
        ):
            best = None
            best_score = -float("inf")

            for candidate in remaining:
                relevance = (
                    candidate.survivability_score
                )

                redundancy = 0.0

                if selected:
                    redundancy = max(
                        blended_similarity(
                            candidate.text,
                            item.text,
                        )
                        for item in selected
                    )

                mmr = (
                    self.mmr_lambda
                    * relevance
                    - (
                        1.0
                        - self.mmr_lambda
                    )
                    * redundancy
                )

                deterministic_tiebreak = (
                    int(
                        fingerprint(
                            candidate.candidate_id
                        )[:8],
                        16,
                    )
                    / 0xFFFFFFFF
                    * 0.000001
                )

                mmr += (
                    deterministic_tiebreak
                )

                if mmr > best_score:
                    best_score = mmr
                    best = candidate

            if best is None:
                break

            selected.append(best)
            remaining.remove(best)

        return selected

    @staticmethod
    def _pareto_frontier(
        scores: Sequence[CandidateScore],
    ) -> list[str]:
        frontier = []

        for candidate in scores:
            dominated = False

            for other in scores:
                if (
                    other.candidate_id
                    == candidate.candidate_id
                ):
                    continue

                equal_or_better = (
                    other.divergence_score
                    >= candidate.divergence_score
                    and other.constraint_score
                    >= candidate.constraint_score
                    and (
                        1.0
                        - other.cliche_risk
                    )
                    >= (
                        1.0
                        - candidate.cliche_risk
                    )
                )

                strictly_better = (
                    other.divergence_score
                    > candidate.divergence_score
                    or other.constraint_score
                    > candidate.constraint_score
                    or other.cliche_risk
                    < candidate.cliche_risk
                )

                if (
                    equal_or_better
                    and strictly_better
                ):
                    dominated = True
                    break

            if not dominated:
                frontier.append(
                    candidate.candidate_id
                )

        return sorted(frontier)

    @staticmethod
    def mutations(
        text: str,
        depth: int,
    ) -> list[dict[str, Any]]:
        text = text.strip()

        if not text:
            raise ValueError(
                "text cannot be empty"
            )

        depth = max(
            1,
            min(depth, 3),
        )

        output = []

        for name, instruction in mutation_operators:
            output.append(
                {
                    "mutation_id": stable_id(
                        "mutation",
                        {
                            "text": normalize_text(
                                text
                            ),
                            "operator": name,
                            "depth": 1,
                        },
                    ),
                    "operator": name,
                    "depth": 1,
                    "source": text,
                    "instruction": instruction,
                }
            )

        if depth >= 2:
            first_layer = list(output)

            for index, first in enumerate(
                first_layer
            ):
                second_name, second_instruction = (
                    mutation_operators[
                        (
                            index * 7 + 11
                        )
                        % len(
                            mutation_operators
                        )
                    ]
                )

                if second_name == (
                    first["operator"]
                ):
                    continue

                output.append(
                    {
                        "mutation_id": stable_id(
                            "mutation",
                            {
                                "text": normalize_text(
                                    text
                                ),
                                "operators": [
                                    first[
                                        "operator"
                                    ],
                                    second_name,
                                ],
                                "depth": 2,
                            },
                        ),
                        "operator": (
                            f"{first['operator']}+"
                            f"{second_name}"
                        ),
                        "depth": 2,
                        "source": text,
                        "instruction": (
                            first[
                                "instruction"
                            ]
                            + " Then: "
                            + second_instruction
                        ),
                    }
                )

        return output

    def analyze(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        subject = str(
            payload.get(
                "subject",
                "",
            )
        ).strip()

        raw_candidates = payload.get(
            "candidates",
            [],
        )

        if not isinstance(
            raw_candidates,
            list,
        ):
            raise TypeError(
                "candidates must be a list"
            )

        if len(raw_candidates) < 2:
            raise ValueError(
                "vessel requires at least two candidates"
            )

        candidates = [
            self._candidate(
                item,
                index,
            )
            for index, item
            in enumerate(
                raw_candidates
            )
        ]

        cliches = [
            str(value).strip()
            for value
            in payload.get(
                "cliches",
                [],
            )
            if str(value).strip()
        ]

        baselines = [
            str(value).strip()
            for value
            in payload.get(
                "baselines",
                [],
            )
            if str(value).strip()
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

        required = [
            str(value).strip()
            for value
            in constraints.get(
                "required",
                [],
            )
            if str(value).strip()
        ]

        forbidden = [
            str(value).strip()
            for value
            in constraints.get(
                "forbidden",
                [],
            )
            if str(value).strip()
        ]

        scores = [
            self._score(
                candidate,
                candidates,
                cliches=cliches,
                baselines=baselines,
                required=required,
                forbidden=forbidden,
            )
            for candidate in candidates
        ]

        ranked = sorted(
            scores,
            key=lambda item: (
                -item.survivability_score,
                -item.subversion_score,
                -item.divergence_score,
                item.cliche_risk,
                item.candidate_id,
            ),
        )

        mmr_frontier = (
            self._mmr_frontier(
                ranked
            )
        )

        pareto = (
            self._pareto_frontier(
                ranked
            )
        )

        run_fingerprint = fingerprint(
            {
                "schema": schema_version,
                "payload": payload,
                "configuration": {
                    "cliche_threshold": (
                        self.cliche_threshold
                    ),
                    "similarity_threshold": (
                        self.similarity_threshold
                    ),
                    "frontier_size": (
                        self.frontier_size
                    ),
                    "mmr_lambda": (
                        self.mmr_lambda
                    ),
                    "rapidfuzz": (
                        fuzz is not None
                    ),
                },
            }
        )

        run_id = (
            f"vessel_{uuid.uuid4().hex}"
        )

        result = {
            "schema": schema_version,
            "run_id": run_id,
            "fingerprint": (
                run_fingerprint
            ),
            "owner": "exile:underscore",
            "capability": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "subject": subject,
            "engine": {
                "fuzzy_backend": (
                    "rapidfuzz"
                    if fuzz is not None
                    else "difflib"
                ),
                "deterministic_projection": True,
                "novelty_is_not_authority": True,
                "novelty_alone_cannot_win": True,
            },
            "ranked_candidates": [
                asdict(score)
                for score in ranked
            ],
            "divergent_frontier": [
                {
                    "candidate_id": (
                        item.candidate_id
                    ),
                    "survivability_score": (
                        item.survivability_score
                    ),
                    "subversion_score": (
                        item.subversion_score
                    ),
                    "divergence_score": (
                        item.divergence_score
                    ),
                    "cliche_risk": (
                        item.cliche_risk
                    ),
                }
                for item
                in mmr_frontier
            ],
            "pareto_frontier": pareto,
            "recommended_next_tests": [
                {
                    "candidate_id": (
                        item.candidate_id
                    ),
                    "tests": (
                        item.discriminants
                    ),
                }
                for item
                in mmr_frontier
            ],
            "enhancements": [
                "deterministic candidate identity",
                "replayable analysis fingerprints",
                "append-only analysis receipts",
                "typed vessel event ledger",
                "multi-metric cliche detection",
                "rapidfuzz accelerated similarity",
                "stdlib similarity fallback",
                "token-set similarity",
                "n-gram similarity",
                "weighted fuzzy similarity",
                "baseline distance measurement",
                "sibling redundancy detection",
                "false-diversity detection",
                "lexical entropy measurement",
                "repetition pressure detection",
                "hard-constraint preservation",
                "forbidden-mechanism detection",
                "novelty-without-structure penalty",
                "divergence scoring",
                "subversion scoring",
                "survivability scoring",
                "cliche pressure flags",
                "discriminating experiment generation",
                "mechanism-versus-surface testing",
                "constraint escape testing",
                "earned-subversion testing",
                "maximum marginal relevance selection",
                "diversity-aware frontier selection",
                "pareto frontier projection",
                "deterministic ranking",
                "thirty mutation operators",
                "compound mutation generation",
                "assumption inversion operators",
                "agency inversion",
                "causal reversal",
                "temporal dislocation",
                "false-binary escape",
                "mechanism substitution",
                "negative-space transformation",
                "recursive consequence transformation",
                "category-error probing",
                "candidate lineage preservation",
                "explicit non-authoritative output",
            ],
        }

        self.store.save_run(
            run_id,
            run_fingerprint,
            subject,
            payload,
            result,
        )

        self.store.event(
            run_id,
            "vessel_projection_complete",
            "divergent_candidates_to_survival_frontier",
            {
                "candidate_count": (
                    len(candidates)
                ),
                "frontier_count": (
                    len(mmr_frontier)
                ),
                "pareto_count": (
                    len(pareto)
                ),
                "authority_effect": (
                    authority_effect
                ),
            },
        )

        return result


def load_payload(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            "input must contain a JSON object"
        )

    return value


def self_check() -> dict[str, Any]:
    engine = Vessel(
        cliche_threshold=(
            default_cliche_threshold
        ),
        similarity_threshold=(
            default_similarity_threshold
        ),
        frontier_size=3,
        mmr_lambda=(
            default_mmr_lambda
        ),
    )

    payload = {
        "subject": (
            "subvert an expected rescue ending"
        ),
        "baselines": [
            (
                "the hero arrives at the last "
                "second and saves everyone"
            ),
        ],
        "cliches": [
            "saved at the last second",
            "it was all a dream",
            "the chosen one",
        ],
        "constraints": {
            "required": [],
            "forbidden": [],
        },
        "candidates": [
            (
                "the hero arrives at the last "
                "second and saves everyone"
            ),
            (
                "the rescue succeeds, but the "
                "people being rescued deliberately "
                "refuse to leave because the rescue "
                "itself proves the enemy's accusation"
            ),
            (
                "no rescue comes; the apparent victim "
                "has already changed the objective so "
                "survival is no longer the relevant victory"
            ),
        ],
    }

    result = engine.analyze(
        payload
    )

    ranked = result[
        "ranked_candidates"
    ]

    if len(ranked) != 3:
        raise RuntimeError(
            "candidate projection failed"
        )

    if (
        ranked[0]["candidate_id"]
        == ranked[-1]["candidate_id"]
    ):
        raise RuntimeError(
            "ranking failed"
        )

    mutations = engine.mutations(
        "the hero wins by defeating the villain",
        2,
    )

    if len(mutations) < 30:
        raise RuntimeError(
            "mutation lattice failed"
        )

    return {
        "schema": schema_version,
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "candidate_count": (
            len(ranked)
        ),
        "mutation_count": (
            len(mutations)
        ),
        "rapidfuzz": (
            fuzz is not None
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vessel",
        description=(
            "underscore divergent-option "
            "discrimination runtime"
        ),
    )

    parser.add_argument(
        "--cliche-threshold",
        type=float,
        default=(
            default_cliche_threshold
        ),
    )

    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=(
            default_similarity_threshold
        ),
    )

    parser.add_argument(
        "--frontier-size",
        type=int,
        default=(
            default_frontier_size
        ),
    )

    parser.add_argument(
        "--mmr-lambda",
        type=float,
        default=(
            default_mmr_lambda
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    analyze = commands.add_parser(
        "analyze"
    )

    analyze.add_argument(
        "--input",
        required=True,
    )

    mutate = commands.add_parser(
        "mutate"
    )

    mutate.add_argument(
        "--text",
        required=True,
    )

    mutate.add_argument(
        "--depth",
        type=int,
        default=(
            default_mutation_depth
        ),
    )

    replay = commands.add_parser(
        "replay"
    )

    replay.add_argument(
        "run_id"
    )

    commands.add_parser(
        "self-check"
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    engine = Vessel(
        cliche_threshold=(
            args.cliche_threshold
        ),
        similarity_threshold=(
            args.similarity_threshold
        ),
        frontier_size=(
            args.frontier_size
        ),
        mmr_lambda=(
            args.mmr_lambda
        ),
    )

    if args.command == "analyze":
        result = engine.analyze(
            load_payload(
                Path(args.input)
            )
        )

    elif args.command == "mutate":
        result = {
            "schema": schema_version,
            "owner": "exile:underscore",
            "capability": "vessel",
            "authority_effect": (
                authority_effect
            ),
            "mutations": engine.mutations(
                args.text,
                args.depth,
            ),
        }

    elif args.command == "replay":
        result = engine.store.replay(
            args.run_id
        )

        if result is None:
            print(
                f"unknown vessel run: "
                f"{args.run_id}",
                file=sys.stderr,
            )
            return 1

    elif args.command == "self-check":
        result = self_check()

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
    raise SystemExit(main())
