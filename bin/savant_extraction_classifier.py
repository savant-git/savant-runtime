#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


VERSION = "3.0.0"
SCHEMA = "savant://extract/classifier/3.0.0"


try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz  # type: ignore
except Exception:
    rapidfuzz_fuzz = None


@dataclass(frozen=True, slots=True)
class Signal:
    value: str
    weight: int
    specificity: str
    family: str


@dataclass(frozen=True, slots=True)
class Classification:
    score: int
    confidence: float
    exact_hits: tuple[str, ...]
    fuzzy_hits: tuple[str, ...]
    include_hits: tuple[str, ...]
    ambiguous_hits: tuple[str, ...]
    corroborated_hits: tuple[str, ...]
    families: tuple[str, ...]
    path_hits: tuple[str, ...]
    phrase_hits: tuple[str, ...]
    title_hits: tuple[str, ...]
    negative_hits: tuple[str, ...]
    excluded: bool
    title_score: int
    evidence_digest: str

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "classifier_version": VERSION,
            "score": self.score,
            "confidence": self.confidence,
            "exact_hits": list(self.exact_hits),
            "fuzzy_hits": list(self.fuzzy_hits),
            "include_hits": list(self.include_hits),
            "ambiguous_hits": list(self.ambiguous_hits),
            "corroborated_hits": list(
                self.corroborated_hits
            ),
            "families": list(self.families),
            "path_hits": list(self.path_hits),
            "phrase_hits": list(self.phrase_hits),
            "title_hits": list(self.title_hits),
            "negative_hits": list(
                self.negative_hits
            ),
            "excluded": self.excluded,
            "title_score": self.title_score,
            "evidence_digest": (
                self.evidence_digest
            ),
        }


SIGNALS: tuple[Signal, ...] = (
    Signal(
        "savant",
        10,
        "identity",
        "identity",
    ),
    Signal(
        "savant-runtime",
        12,
        "identity",
        "identity",
    ),
    Signal(
        "savant runtime",
        12,
        "identity",
        "identity",
    ),
    Signal(
        "/root/savant-runtime",
        14,
        "path",
        "implementation",
    ),
    Signal(
        "fluid canon",
        11,
        "phrase",
        "canon",
    ),
    Signal(
        "fluid-canon",
        11,
        "phrase",
        "canon",
    ),
    Signal(
        "authority graph",
        11,
        "phrase",
        "authority",
    ),
    Signal(
        "authority_graph",
        11,
        "phrase",
        "authority",
    ),
    Signal(
        "authority precedence",
        10,
        "phrase",
        "authority",
    ),
    Signal(
        "living trait crown",
        11,
        "phrase",
        "persona",
    ),
    Signal(
        "recursive capsule",
        9,
        "phrase",
        "composition",
    ),
    Signal(
        "recursive capsules",
        9,
        "phrase",
        "composition",
    ),
    Signal(
        "composition graph",
        9,
        "phrase",
        "composition",
    ),
    Signal(
        "living substrate",
        9,
        "phrase",
        "composition",
    ),
    Signal(
        "living substrates",
        9,
        "phrase",
        "composition",
    ),
    Signal(
        "canon system",
        9,
        "phrase",
        "canon",
    ),
    Signal(
        "canon-system",
        9,
        "phrase",
        "canon",
    ),
    Signal(
        "masterplan",
        8,
        "distinctive",
        "planning",
    ),
    Signal(
        "palaver",
        8,
        "distinctive",
        "palaver",
    ),
    Signal(
        "orobouros",
        10,
        "distinctive",
        "persona",
    ),
    Signal(
        "coalesce",
        9,
        "distinctive",
        "composition",
    ),
    Signal(
        "scrybe",
        9,
        "distinctive",
        "memory",
    ),
    Signal(
        "pryme",
        9,
        "distinctive",
        "identity",
    ),
    Signal(
        "scyon",
        9,
        "distinctive",
        "identity",
    ),
    Signal(
        "splyce",
        9,
        "distinctive",
        "composition",
    ),
    Signal(
        "spyral",
        9,
        "distinctive",
        "composition",
    ),
    Signal(
        "lythe",
        9,
        "distinctive",
        "identity",
    ),
    Signal(
        "dryve",
        9,
        "distinctive",
        "identity",
    ),
    Signal(
        "thryce",
        9,
        "distinctive",
        "identity",
    ),
    Signal(
        "sliver",
        8,
        "distinctive",
        "composition",
    ),
    Signal(
        "slivers",
        8,
        "distinctive",
        "composition",
    ),
    Signal(
        "polestar",
        7,
        "distinctive",
        "governance",
    ),
    Signal(
        "prodigal",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "prodigals",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "kindred",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "obelisk",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "obelisks",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "segue",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "segues",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "innate",
        6,
        "distinctive",
        "ontology",
    ),
    Signal(
        "innates",
        6,
        "distinctive",
        "ontology",
    ),
    Signal(
        "alloy",
        6,
        "distinctive",
        "composition",
    ),
    Signal(
        "alloys",
        6,
        "distinctive",
        "composition",
    ),
    Signal(
        "rubric",
        6,
        "distinctive",
        "governance",
    ),
    Signal(
        "cabal",
        6,
        "distinctive",
        "ontology",
    ),
    Signal(
        "shardsense",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "goldthread",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "echomap",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "harmonic convergence",
        7,
        "phrase",
        "ontology",
    ),
    Signal(
        "gate_vi",
        7,
        "distinctive",
        "ontology",
    ),
    Signal(
        "vm_chat",
        6,
        "distinctive",
        "implementation",
    ),
    Signal(
        "vm chat",
        6,
        "phrase",
        "implementation",
    ),
    Signal(
        "csc_",
        6,
        "prefix",
        "implementation",
    ),
    Signal(
        "opus",
        5,
        "ambiguous",
        "provider",
    ),
    Signal(
        "envoy",
        5,
        "ambiguous",
        "persona",
    ),
    Signal(
        "niche",
        5,
        "ambiguous",
        "task",
    ),
    Signal(
        "coda",
        5,
        "ambiguous",
        "mutation",
    ),
    Signal(
        "notary",
        5,
        "ambiguous",
        "authority",
    ),
    Signal(
        "modus",
        5,
        "ambiguous",
        "governance",
    ),
    Signal(
        "cypher",
        5,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "filament",
        5,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "focal",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "shard",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "shards",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "iota",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "exile",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "exiles",
        4,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "quirk",
        3,
        "generic",
        "persona",
    ),
    Signal(
        "quirks",
        3,
        "generic",
        "persona",
    ),
    Signal(
        "trait",
        2,
        "generic",
        "persona",
    ),
    Signal(
        "traits",
        2,
        "generic",
        "persona",
    ),
    Signal(
        "gate",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "gates",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "mood",
        2,
        "generic",
        "persona",
    ),
    Signal(
        "moods",
        2,
        "generic",
        "persona",
    ),
    Signal(
        "projection",
        2,
        "generic",
        "composition",
    ),
    Signal(
        "provenance",
        3,
        "generic",
        "authority",
    ),
    Signal(
        "lineage",
        3,
        "generic",
        "authority",
    ),
    Signal(
        "dependency",
        2,
        "generic",
        "implementation",
    ),
    Signal(
        "dependencies",
        2,
        "generic",
        "implementation",
    ),
    Signal(
        "canonical",
        2,
        "generic",
        "authority",
    ),
    Signal(
        "cresco",
        3,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "crescendo",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "fugue",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "vortex",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "praxis",
        3,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "covenant",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "graffiti",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "carbon",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "occam",
        3,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "tempo",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "underscore",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "urge",
        2,
        "generic",
        "ontology",
    ),
    Signal(
        "oriel",
        3,
        "ambiguous",
        "ontology",
    ),
    Signal(
        "endgame",
        2,
        "generic",
        "ontology",
    ),
)


PATH_PATTERNS = (
    "/root/savant-runtime/",
    "savant-runtime/",
    "/ontology/obelisks/",
    "/segue/gates/",
    "/segue/innates/",
    "/segue/exiles/",
    "/fluid-canon/",
    "/runtime/",
)


TECHNICAL_PATTERNS = (
    "python3 ",
    "nano /root/savant-runtime/",
    "chmod ",
    "systemctl ",
    "journalctl ",
    "sha256",
    ".py",
    ".json",
    ".jsonl",
    ".md",
    "api/",
    "runtime/",
    "ontology/",
    "authority_effect",
    "persona_id",
    "composition_digest",
)


SIGNAL_BY_VALUE = {
    signal.value: signal
    for signal in SIGNALS
}


FUZZY_SIGNALS = tuple(
    signal
    for signal in SIGNALS
    if signal.specificity
    in {
        "identity",
        "distinctive",
    }
    and len(signal.value) >= 5
)


def normalize(value: Any) -> str:
    return unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).casefold()


def tokenize(value: Any) -> tuple[str, ...]:
    return tuple(
        re.findall(
            r"[a-z0-9_]+",
            normalize(value),
        )
    )


def token_set(value: Any) -> frozenset[str]:
    return frozenset(
        tokenize(value)
    )


def boundary_pattern(value: str) -> re.Pattern[str]:
    normalized = normalize(value)

    escaped = re.escape(
        normalized
    )

    return re.compile(
        rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])"
    )


_PATTERN_CACHE = {
    signal.value: boundary_pattern(
        signal.value
    )
    for signal in SIGNALS
    if signal.specificity
    not in {
        "path",
        "prefix",
    }
}


def contains_signal(
    normalized_text: str,
    signal: Signal,
) -> bool:
    if signal.specificity == "path":
        return signal.value in normalized_text

    if signal.specificity == "prefix":
        return signal.value in normalized_text

    pattern = _PATTERN_CACHE[
        signal.value
    ]

    return bool(
        pattern.search(
            normalized_text
        )
    )


def exact_hits(
    text: Any,
) -> tuple[Signal, ...]:
    normalized_text = normalize(
        text
    )

    return tuple(
        signal
        for signal in SIGNALS
        if contains_signal(
            normalized_text,
            signal,
        )
    )


def explicit_term_hits(
    text: Any,
    terms: Sequence[str],
) -> tuple[str, ...]:
    normalized_text = normalize(
        text
    )

    hits: set[str] = set()

    for raw_term in terms:
        term = normalize(
            raw_term
        ).strip()

        if not term:
            continue

        pattern = boundary_pattern(
            term
        )

        if pattern.search(
            normalized_text
        ):
            hits.add(
                raw_term
            )

    return tuple(
        sorted(
            hits
        )
    )


def path_hits(
    text: Any,
) -> tuple[str, ...]:
    normalized_text = normalize(
        text
    )

    return tuple(
        sorted(
            {
                pattern
                for pattern
                in PATH_PATTERNS
                if pattern
                in normalized_text
            }
        )
    )


def technical_hits(
    text: Any,
) -> tuple[str, ...]:
    normalized_text = normalize(
        text
    )

    return tuple(
        sorted(
            {
                pattern
                for pattern
                in TECHNICAL_PATTERNS
                if pattern
                in normalized_text
            }
        )
    )


def candidate_ngrams(
    text: Any,
    *,
    minimum: int = 1,
    maximum: int = 3,
) -> tuple[str, ...]:
    words = tokenize(
        text
    )

    values: set[str] = set()

    for size in range(
        minimum,
        maximum + 1,
    ):
        if len(words) < size:
            continue

        for index in range(
            0,
            len(words) - size + 1,
        ):
            values.add(
                " ".join(
                    words[
                        index:
                        index + size
                    ]
                )
            )

    return tuple(
        sorted(
            values
        )
    )


def fuzzy_hits(
    text: Any,
    *,
    enabled: bool,
    cutoff: int,
) -> tuple[str, ...]:
    if (
        not enabled
        or rapidfuzz_fuzz is None
    ):
        return ()

    candidates = candidate_ngrams(
        text,
        minimum=1,
        maximum=3,
    )

    if not candidates:
        return ()

    hits: set[str] = set()

    for signal in FUZZY_SIGNALS:
        target = normalize(
            signal.value
        )

        target_words = len(
            tokenize(
                target
            )
        )

        for candidate in candidates:
            candidate_words = len(
                tokenize(
                    candidate
                )
            )

            if candidate_words != target_words:
                continue

            if (
                abs(
                    len(candidate)
                    - len(target)
                )
                > max(
                    2,
                    math.ceil(
                        len(target)
                        * 0.20
                    ),
                )
            ):
                continue

            ratio = (
                rapidfuzz_fuzz.ratio(
                    target,
                    candidate,
                )
            )

            if ratio >= cutoff:
                hits.add(
                    signal.value
                )
                break

    return tuple(
        sorted(
            hits
        )
    )


def signal_families(
    hits: Iterable[Signal],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                signal.family
                for signal in hits
            }
        )
    )


def specificity_hits(
    hits: Iterable[Signal],
    specificity: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                signal.value
                for signal in hits
                if signal.specificity
                == specificity
            }
        )
    )


def distinctive_count(
    hits: Iterable[Signal],
) -> int:
    return sum(
        1
        for signal in hits
        if signal.specificity
        in {
            "identity",
            "path",
            "phrase",
            "distinctive",
            "prefix",
        }
    )


def corroborated_values(
    hits: Sequence[Signal],
) -> tuple[str, ...]:
    families = signal_families(
        hits
    )

    distinctive = distinctive_count(
        hits
    )

    corroborated: set[str] = set()

    for signal in hits:
        if signal.specificity in {
            "identity",
            "path",
            "phrase",
            "distinctive",
            "prefix",
        }:
            corroborated.add(
                signal.value
            )
            continue

        if (
            signal.specificity
            == "ambiguous"
            and (
                distinctive >= 1
                or len(families) >= 2
            )
        ):
            corroborated.add(
                signal.value
            )
            continue

        if (
            signal.specificity
            == "generic"
            and (
                distinctive >= 1
                or len(families) >= 3
            )
        ):
            corroborated.add(
                signal.value
            )

    return tuple(
        sorted(
            corroborated
        )
    )


def weighted_score(
    hits: Sequence[Signal],
) -> int:
    distinctive = distinctive_count(
        hits
    )

    families = signal_families(
        hits
    )

    total = 0

    family_counts: dict[str, int] = {}

    for signal in hits:
        family_counts[
            signal.family
        ] = (
            family_counts.get(
                signal.family,
                0,
            )
            + 1
        )

        if signal.specificity in {
            "identity",
            "path",
            "phrase",
            "distinctive",
            "prefix",
        }:
            total += signal.weight
            continue

        if signal.specificity == "ambiguous":
            if (
                distinctive >= 1
                or len(families) >= 2
            ):
                total += signal.weight
            else:
                total += min(
                    1,
                    signal.weight,
                )

            continue

        if signal.specificity == "generic":
            if distinctive >= 1:
                total += signal.weight
            elif len(families) >= 3:
                total += min(
                    2,
                    signal.weight,
                )

    saturation_bonus = min(
        6,
        max(
            0,
            len(families) - 1,
        ),
    )

    total += saturation_bonus

    repeated_family_penalty = sum(
        max(
            0,
            count - 4,
        )
        for count
        in family_counts.values()
    )

    total -= min(
        repeated_family_penalty,
        4,
    )

    return max(
        0,
        total,
    )


def title_evidence(
    title: Any,
) -> tuple[
    tuple[Signal, ...],
    int,
]:
    hits = exact_hits(
        title
    )

    if not hits:
        return (), 0

    distinctive = [
        signal
        for signal in hits
        if signal.specificity
        in {
            "identity",
            "path",
            "phrase",
            "distinctive",
            "prefix",
        }
    ]

    if distinctive:
        return (
            hits,
            min(
                5,
                max(
                    signal.weight
                    for signal
                    in distinctive
                ),
            ),
        )

    return hits, 0


def confidence_value(
    *,
    score: int,
    distinctive: int,
    family_count: int,
    path_count: int,
    fuzzy_count: int,
    ambiguous_only: bool,
) -> float:
    value = 0.0

    value += min(
        0.45,
        score / 40.0,
    )

    value += min(
        0.25,
        distinctive * 0.08,
    )

    value += min(
        0.15,
        family_count * 0.04,
    )

    value += min(
        0.15,
        path_count * 0.08,
    )

    if fuzzy_count:
        value -= min(
            0.10,
            fuzzy_count * 0.025,
        )

    if ambiguous_only:
        value = min(
            value,
            0.34,
        )

    return round(
        max(
            0.0,
            min(
                1.0,
                value,
            ),
        ),
        4,
    )


def evidence_digest(
    value: Mapping[str, Any],
) -> str:
    payload = repr(
        tuple(
            sorted(
                (
                    str(key),
                    repr(item),
                )
                for key, item
                in value.items()
            )
        )
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def classify(
    text: str,
    *,
    title: str = "",
    include_terms: Sequence[str] = (),
    exclude_terms: Sequence[str] = (),
    fuzzy: bool = False,
    fuzzy_cutoff: int = 94,
) -> Classification:
    exclude_hits = explicit_term_hits(
        text,
        exclude_terms,
    )

    if exclude_hits:
        digest = evidence_digest(
            {
                "excluded": True,
                "exclude_hits": (
                    exclude_hits
                ),
            }
        )

        return Classification(
            score=0,
            confidence=0.0,
            exact_hits=(),
            fuzzy_hits=(),
            include_hits=(),
            ambiguous_hits=(),
            corroborated_hits=(),
            families=(),
            path_hits=(),
            phrase_hits=(),
            title_hits=(),
            negative_hits=exclude_hits,
            excluded=True,
            title_score=0,
            evidence_digest=digest,
        )

    hits = exact_hits(
        text
    )

    exact_values = tuple(
        sorted(
            {
                signal.value
                for signal in hits
            }
        )
    )

    include_hits = (
        explicit_term_hits(
            text,
            include_terms,
        )
    )

    fuzzy_values = fuzzy_hits(
        text,
        enabled=fuzzy,
        cutoff=fuzzy_cutoff,
    )

    families = signal_families(
        hits
    )

    distinctive = distinctive_count(
        hits
    )

    ambiguous_values = tuple(
        sorted(
            {
                signal.value
                for signal in hits
                if signal.specificity
                in {
                    "ambiguous",
                    "generic",
                }
            }
        )
    )

    corroborated = (
        corroborated_values(
            hits
        )
    )

    paths = path_hits(
        text
    )

    phrases = specificity_hits(
        hits,
        "phrase",
    )

    title_signal_hits, title_score = (
        title_evidence(
            title
        )
    )

    title_values = tuple(
        sorted(
            {
                signal.value
                for signal
                in title_signal_hits
            }
        )
    )

    base_score = weighted_score(
        hits
    )

    include_score = min(
        20,
        len(include_hits) * 8,
    )

    fuzzy_score = min(
        3,
        len(
            set(fuzzy_values)
            - set(exact_values)
        ),
    )

    technical = technical_hits(
        text
    )

    technical_bonus = 0

    if (
        technical
        and (
            distinctive > 0
            or paths
        )
    ):
        technical_bonus = min(
            4,
            len(technical),
        )

    path_bonus = min(
        5,
        len(paths) * 2,
    )

    message_evidence = (
        base_score
        + include_score
        + fuzzy_score
        + technical_bonus
        + path_bonus
    )

    effective_title_score = (
        title_score
        if message_evidence > 0
        else 0
    )

    score = (
        message_evidence
        + effective_title_score
    )

    ambiguous_only = bool(
        hits
    ) and distinctive == 0

    if (
        ambiguous_only
        and len(families) < 2
        and not include_hits
    ):
        score = min(
            score,
            1,
        )

    if (
        ambiguous_only
        and len(families) == 2
        and not include_hits
    ):
        score = min(
            score,
            2,
        )

    confidence = confidence_value(
        score=score,
        distinctive=distinctive,
        family_count=len(families),
        path_count=len(paths),
        fuzzy_count=len(fuzzy_values),
        ambiguous_only=ambiguous_only,
    )

    digest = evidence_digest(
        {
            "score": score,
            "exact": exact_values,
            "fuzzy": fuzzy_values,
            "include": include_hits,
            "ambiguous": ambiguous_values,
            "corroborated": corroborated,
            "families": families,
            "paths": paths,
            "phrases": phrases,
            "title": title_values,
            "title_score": (
                effective_title_score
            ),
        }
    )

    return Classification(
        score=score,
        confidence=confidence,
        exact_hits=exact_values,
        fuzzy_hits=fuzzy_values,
        include_hits=include_hits,
        ambiguous_hits=ambiguous_values,
        corroborated_hits=corroborated,
        families=families,
        path_hits=paths,
        phrase_hits=phrases,
        title_hits=title_values,
        negative_hits=(),
        excluded=False,
        title_score=(
            effective_title_score
        ),
        evidence_digest=digest,
    )


def legacy_score_projection(
    text: str,
    *,
    title: str,
    include_terms: Sequence[str],
    exclude_terms: Sequence[str],
    fuzzy: bool,
    fuzzy_cutoff: int,
) -> dict[str, Any]:
    result = classify(
        text,
        title=title,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        fuzzy=fuzzy,
        fuzzy_cutoff=fuzzy_cutoff,
    )

    return result.projection()


def self_test() -> int:
    positive = (
        "Implement the Savant authority graph "
        "under /root/savant-runtime/ontology."
    )

    positive_result = classify(
        positive
    )

    if positive_result.score < 2:
        raise RuntimeError(
            "positive Savant fixture failed"
        )

    false_positive_fixtures = (
        "The mood of the novel changes.",
        "Open the gate before midnight.",
        "The carbon footprint is enormous.",
        "This dependency needs updating.",
        "The canonical novel is widely read.",
        "The projection screen is broken.",
        "I have an urge to buy groceries.",
        "The tempo of this song is slow.",
        "That is an unusual character trait.",
        "We reached the endgame yesterday.",
    )

    for fixture in false_positive_fixtures:
        result = classify(
            fixture
        )

        if result.score >= 2:
            raise RuntimeError(
                "false-positive fixture failed: "
                + fixture
            )

    boundary_fixture = (
        "The word savage must not match Savant."
    )

    boundary_result = classify(
        boundary_fixture
    )

    if "savant" in (
        boundary_result.exact_hits
    ):
        raise RuntimeError(
            "boundary matching fixture failed"
        )

    compound_fixture = (
        "Palaver delegates persona composition "
        "to Envoy inside Savant."
    )

    compound_result = classify(
        compound_fixture
    )

    if compound_result.score < 2:
        raise RuntimeError(
            "compound evidence fixture failed"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        self_test()
    )
