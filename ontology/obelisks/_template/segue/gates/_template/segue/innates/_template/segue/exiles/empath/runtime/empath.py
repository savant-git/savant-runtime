#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "savant.empath.projection.v1"
ENGINE = "savant-empath"
VERSION = "1.0.0"

TOKEN_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
QUESTION_RE = re.compile(r"\?")
EXCLAMATION_RE = re.compile(r"!")
ELLIPSIS_RE = re.compile(r"(?:\.{3,}|…)")
REPEATED_PUNCT_RE = re.compile(r"([!?])\1{1,}")
FIRST_PERSON_RE = re.compile(r"\b(?:i|i'm|i've|i'd|me|my|mine)\b", re.I)
SECOND_PERSON_RE = re.compile(r"\b(?:you|you're|you've|you'd|your|yours)\b", re.I)

LEXICONS: dict[str, frozenset[str]] = {
    "positive": frozenset({
        "appreciate", "awesome", "excellent", "fine", "glad", "good",
        "great", "happy", "helpful", "love", "perfect", "pleased",
        "thank", "thanks", "wonderful", "works"
    }),
    "negative": frozenset({
        "awful", "bad", "broken", "confusing", "disappointed", "fail",
        "failed", "failing", "frustrated", "frustrating", "hate",
        "horrible", "problem", "ridiculous", "terrible", "unacceptable",
        "useless", "wrong"
    }),
    "friction": frozenset({
        "again", "already", "broken", "can't", "cannot", "confusing",
        "doesn't", "failed", "failing", "fix", "frustrated",
        "frustrating", "issue", "problem", "still", "stuck", "wrong"
    }),
    "urgency": frozenset({
        "asap", "critical", "emergency", "immediately", "now", "quick",
        "quickly", "soon", "today", "urgent", "urgently"
    }),
    "uncertainty": frozenset({
        "apparently", "guess", "maybe", "might", "perhaps", "possibly",
        "probably", "seem", "seems", "unsure", "uncertain", "wonder"
    }),
    "certainty": frozenset({
        "absolutely", "certain", "certainly", "clearly", "definitely",
        "exactly", "must", "obviously", "sure"
    }),
    "hedging": frozenset({
        "approximately", "generally", "kind", "maybe", "perhaps",
        "possibly", "roughly", "seems", "somewhat", "sort"
    }),
    "gratitude": frozenset({
        "appreciate", "grateful", "thank", "thanks"
    }),
    "apology": frozenset({
        "apologies", "apologize", "sorry"
    }),
    "directness": frozenset({
        "build", "continue", "create", "do", "fix", "implement",
        "make", "proceed", "repair", "run", "stop", "update", "use"
    }),
    "escalation": frozenset({
        "always", "completely", "every", "everything", "never",
        "nothing", "totally", "unacceptable", "worst"
    }),
    "constraint": frozenset({
        "avoid", "cannot", "don't", "must", "never", "only",
        "preserve", "require", "required", "without"
    }),
    "cooperation": frozenset({
        "can", "could", "help", "please", "together", "would"
    }),
    "negation": frozenset({
        "ain't", "aren't", "can't", "cannot", "didn't", "doesn't",
        "don't", "isn't", "never", "no", "not", "nothing", "won't"
    })
}


@dataclass(frozen=True)
class EvidenceSpan:
    signal: str
    token: str
    start: int
    end: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "token": self.token,
            "start": self.start,
            "end": self.end,
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _round(value: float) -> float:
    return round(_clamp(value), 4)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _tokens(text: str) -> list[str]:
    return [match.group(0) for match in TOKEN_RE.finditer(text)]


def _sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in SENTENCE_RE.split(text)
        if part.strip()
    ]


def _lexical_hits(
    text: str,
    lexicon: frozenset[str],
    signal: str,
) -> tuple[list[str], list[EvidenceSpan]]:
    hits: list[str] = []
    spans: list[EvidenceSpan] = []

    for match in TOKEN_RE.finditer(text):
        token = match.group(0)
        lowered = token.casefold()

        if lowered in lexicon:
            hits.append(lowered)
            spans.append(
                EvidenceSpan(
                    signal=signal,
                    token=token,
                    start=match.start(),
                    end=match.end(),
                )
            )

    return hits, spans


def _caps_ratio(tokens: Sequence[str]) -> float:
    candidates = [
        token
        for token in tokens
        if len(token) >= 3 and any(char.isalpha() for char in token)
    ]

    if not candidates:
        return 0.0

    uppercase = sum(
        1
        for token in candidates
        if token.upper() == token
    )

    return _safe_ratio(uppercase, len(candidates))


def _lexical_diversity(tokens: Sequence[str]) -> float:
    lowered = [token.casefold() for token in tokens]

    if not lowered:
        return 0.0

    return _safe_ratio(len(set(lowered)), len(lowered))


def _sentence_variance(sentences: Sequence[str]) -> float:
    lengths = [len(_tokens(sentence)) for sentence in sentences]

    if len(lengths) < 2:
        return 0.0

    mean = sum(lengths) / len(lengths)

    if mean <= 0:
        return 0.0

    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    standard_deviation = math.sqrt(variance)

    return _clamp(standard_deviation / max(1.0, mean))


def _score_hits(
    hits: Sequence[str],
    token_count: int,
    *,
    multiplier: float = 7.5,
) -> float:
    return _clamp(
        _safe_ratio(len(hits), max(1, token_count)) * multiplier
    )


def _confidence(
    token_count: int,
    evidence_count: int,
    *,
    structural_support: int = 0,
) -> float:
    length_support = min(1.0, token_count / 80.0)
    evidence_support = min(1.0, evidence_count / 6.0)
    structure_support = min(1.0, structural_support / 4.0)

    return _round(
        0.15 +
        length_support * 0.35 +
        evidence_support * 0.35 +
        structure_support * 0.15
    )


def _epistemic_label(score: float, confidence: float) -> str:
    if confidence < 0.32:
        return "unknown"

    if score >= 0.70:
        return "strong_signal"

    if score >= 0.40:
        return "moderate_signal"

    if score >= 0.16:
        return "weak_signal"

    return "not_observed_in_available_text"


def _extract_signal(
    text: str,
    token_count: int,
    name: str,
    *,
    multiplier: float = 7.5,
    structural_score: float = 0.0,
    structural_support: int = 0,
) -> tuple[dict[str, Any], list[EvidenceSpan]]:
    hits, spans = _lexical_hits(
        text,
        LEXICONS[name],
        name,
    )

    lexical_score = _score_hits(
        hits,
        token_count,
        multiplier=multiplier,
    )

    score = _round(
        lexical_score * 0.78 +
        _clamp(structural_score) * 0.22
    )

    confidence = _confidence(
        token_count,
        len(hits),
        structural_support=structural_support,
    )

    return (
        {
            "score": score,
            "confidence": confidence,
            "classification": _epistemic_label(score, confidence),
            "basis": "observable linguistic projection",
            "hit_count": len(hits),
            "hits": sorted(set(hits)),
        },
        spans,
    )


def _interaction_temperature(
    *,
    friction: float,
    urgency: float,
    escalation: float,
    caps: float,
    punctuation: float,
) -> float:
    return _round(
        friction * 0.31 +
        urgency * 0.24 +
        escalation * 0.20 +
        caps * 0.12 +
        punctuation * 0.13
    )


def _response_calibration(
    signals: Mapping[str, Mapping[str, Any]],
    interaction: Mapping[str, Any],
) -> dict[str, Any]:
    friction = float(signals["friction"]["score"])
    urgency = float(signals["urgency"]["score"])
    uncertainty = float(signals["uncertainty"]["score"])
    gratitude = float(signals["gratitude"]["score"])
    apology = float(signals["apology"]["score"])
    directness = float(signals["directness"]["score"])
    cognitive_load = float(interaction["cognitive_load"]["score"])

    recommendations: list[dict[str, str]] = []

    if friction >= 0.40:
        recommendations.append({
            "action": "reduce_repetition",
            "reason": "friction signal is materially represented",
        })
        recommendations.append({
            "action": "lead_with_concrete_resolution",
            "reason": "high-friction exchanges benefit from execution-first response structure",
        })

    if urgency >= 0.40:
        recommendations.append({
            "action": "prioritize_immediate_action",
            "reason": "urgency language is materially represented",
        })

    if uncertainty >= 0.40:
        recommendations.append({
            "action": "separate_known_unknown_inference",
            "reason": "uncertainty language is materially represented",
        })

    if cognitive_load >= 0.55:
        recommendations.append({
            "action": "compress_nonessential_exposition",
            "reason": "input contains comparatively high structural density",
        })

    if directness >= 0.40:
        recommendations.append({
            "action": "prefer_direct_execution_language",
            "reason": "directive language is materially represented",
        })

    if gratitude >= 0.30:
        recommendations.append({
            "action": "acknowledge_briefly",
            "reason": "gratitude signal is represented",
        })

    if apology >= 0.30:
        recommendations.append({
            "action": "avoid_overweighting_apology",
            "reason": "apology language is represented but does not change task authority",
        })

    if not recommendations:
        recommendations.append({
            "action": "neutral_technical_response",
            "reason": "no response-modifying signal reached the configured projection threshold",
        })

    return {
        "projection_only": True,
        "recommendations": recommendations,
        "must_not": [
            "claim certainty about internal emotion",
            "diagnose psychological or medical conditions",
            "alter authoritative task ordering",
            "alter persona authority",
            "promote projection to canon",
        ],
    }


def _history_projection(
    current: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    if not history:
        return {
            "available": False,
            "classification": "not_projected",
            "reason": "no prior empath projections supplied",
        }

    previous = history[-1]
    previous_signals = previous.get("signals")

    if not isinstance(previous_signals, Mapping):
        return {
            "available": False,
            "classification": "unknown",
            "reason": "prior projection lacks compatible signal structure",
        }

    deltas: dict[str, float] = {}

    for name, signal in current["signals"].items():
        if not isinstance(signal, Mapping):
            continue

        current_score = signal.get("score")
        previous_signal = previous_signals.get(name)

        if (
            isinstance(current_score, (int, float))
            and isinstance(previous_signal, Mapping)
            and isinstance(previous_signal.get("score"), (int, float))
        ):
            deltas[name] = round(
                float(current_score) -
                float(previous_signal["score"]),
                4,
            )

    materially_changed = {
        name: delta
        for name, delta in deltas.items()
        if abs(delta) >= 0.15
    }

    return {
        "available": True,
        "classification": (
            "changed"
            if materially_changed
            else "stable_within_projection_threshold"
        ),
        "deltas": deltas,
        "material_deltas": materially_changed,
        "authority_effect": "none",
    }


def analyze(
    text: str,
    *,
    history: Sequence[Mapping[str, Any]] | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    normalized = _canonical_text(text)

    tokens = _tokens(normalized)
    sentences = _sentences(normalized)

    token_count = len(tokens)
    sentence_count = len(sentences)

    question_count = len(QUESTION_RE.findall(normalized))
    exclamation_count = len(EXCLAMATION_RE.findall(normalized))
    ellipsis_count = len(ELLIPSIS_RE.findall(normalized))
    repeated_punctuation_count = len(REPEATED_PUNCT_RE.findall(normalized))

    caps = _caps_ratio(tokens)
    lexical_diversity = _lexical_diversity(tokens)
    sentence_variance = _sentence_variance(sentences)

    punctuation_intensity = _clamp(
        _safe_ratio(
            exclamation_count +
            repeated_punctuation_count * 2,
            max(1, sentence_count),
        ) / 2.5
    )

    question_density = _clamp(
        _safe_ratio(question_count, max(1, sentence_count))
    )

    first_person_density = _clamp(
        _safe_ratio(
            len(FIRST_PERSON_RE.findall(normalized)),
            max(1, token_count),
        ) * 6.0
    )

    second_person_density = _clamp(
        _safe_ratio(
            len(SECOND_PERSON_RE.findall(normalized)),
            max(1, token_count),
        ) * 6.0
    )

    structural_density = _clamp(
        min(1.0, token_count / 220.0) * 0.45 +
        sentence_variance * 0.20 +
        lexical_diversity * 0.15 +
        question_density * 0.10 +
        punctuation_intensity * 0.10
    )

    signals: dict[str, dict[str, Any]] = {}
    evidence: list[EvidenceSpan] = []

    signal_specs = {
        "positive": 7.0,
        "negative": 7.0,
        "friction": 8.5,
        "urgency": 9.0,
        "uncertainty": 8.0,
        "certainty": 7.0,
        "hedging": 8.0,
        "gratitude": 11.0,
        "apology": 11.0,
        "directness": 5.0,
        "escalation": 8.0,
        "constraint": 5.5,
        "cooperation": 5.5,
        "negation": 6.5,
    }

    for name, multiplier in signal_specs.items():
        structural_score = 0.0
        structural_support = 0

        if name == "friction":
            structural_score = (
                punctuation_intensity * 0.55 +
                caps * 0.45
            )
            structural_support = (
                int(exclamation_count > 0) +
                int(repeated_punctuation_count > 0) +
                int(caps > 0.10)
            )

        elif name == "urgency":
            structural_score = punctuation_intensity
            structural_support = int(exclamation_count > 0)

        elif name == "uncertainty":
            structural_score = question_density
            structural_support = int(question_count > 0)

        elif name == "escalation":
            structural_score = (
                punctuation_intensity * 0.65 +
                caps * 0.35
            )
            structural_support = (
                int(repeated_punctuation_count > 0) +
                int(caps > 0.10)
            )

        signal, spans = _extract_signal(
            normalized,
            token_count,
            name,
            multiplier=multiplier,
            structural_score=structural_score,
            structural_support=structural_support,
        )

        signals[name] = signal
        evidence.extend(spans)

    valence_support = (
        float(signals["positive"]["score"]) -
        float(signals["negative"]["score"])
    )

    interaction_temperature = _interaction_temperature(
        friction=float(signals["friction"]["score"]),
        urgency=float(signals["urgency"]["score"]),
        escalation=float(signals["escalation"]["score"]),
        caps=caps,
        punctuation=punctuation_intensity,
    )

    cognitive_load = _round(
        structural_density * 0.62 +
        float(signals["constraint"]["score"]) * 0.22 +
        question_density * 0.16
    )

    contradiction_signal = _round(
        min(
            float(signals["certainty"]["score"]),
            float(signals["uncertainty"]["score"]),
        ) * 0.75 +
        min(
            float(signals["positive"]["score"]),
            float(signals["negative"]["score"]),
        ) * 0.25
    )

    interaction = {
        "temperature": {
            "score": interaction_temperature,
            "classification": _epistemic_label(
                interaction_temperature,
                _confidence(
                    token_count,
                    len(evidence),
                    structural_support=4,
                ),
            ),
            "basis": "composite deterministic projection",
        },
        "cognitive_load": {
            "score": cognitive_load,
            "classification": _epistemic_label(
                cognitive_load,
                _confidence(
                    token_count,
                    0,
                    structural_support=3,
                ),
            ),
            "basis": "text structural-density projection, not a claim about human cognitive capacity",
        },
        "question_density": _round(question_density),
        "punctuation_intensity": _round(punctuation_intensity),
        "caps_intensity": _round(caps),
        "lexical_diversity": _round(lexical_diversity),
        "sentence_length_variance": _round(sentence_variance),
        "first_person_density": _round(first_person_density),
        "second_person_density": _round(second_person_density),
        "valence_balance": round(valence_support, 4),
        "contradiction_signal": {
            "score": contradiction_signal,
            "classification": _epistemic_label(
                contradiction_signal,
                _confidence(token_count, 0, structural_support=2),
            ),
            "basis": "co-occurrence projection only",
        },
    }

    projection_id = (
        "empath:"
        + hashlib.sha256(
            (
                SCHEMA +
                "\x00" +
                normalized
            ).encode("utf-8")
        ).hexdigest()[:24]
    )

    projection: dict[str, Any] = {
        "schema": SCHEMA,
        "projection_id": projection_id,
        "engine": ENGINE,
        "engine_version": VERSION,
        "authority_effect": "none",
        "projection_only": True,
        "input": {
            "sha256": _sha256(normalized),
            "source_id": source_id,
            "characters": len(normalized),
            "tokens": token_count,
            "sentences": sentence_count,
            "language_support": "english_lexical_projection_with_language_agnostic_structural_signals",
        },
        "signals": signals,
        "interaction": interaction,
        "evidence": {
            "span_count": len(evidence),
            "spans": [
                span.as_dict()
                for span in evidence[:128]
            ],
            "truncated": len(evidence) > 128,
        },
        "response_calibration": {},
        "epistemics": {
            "observable": "input text and structural features",
            "derived": "signal scores, classifications, interaction projections, response calibration",
            "not_observable": "the person's actual private emotional or psychological state",
            "diagnostic": False,
            "deception_detection": False,
            "clinical_classification": False,
            "confidence_changes_authority": False,
            "unknown_preserved": True,
            "absence_of_signal_proves_absence": False,
        },
        "provenance": {
            "source_id": source_id,
            "input_sha256": _sha256(normalized),
            "algorithm": "deterministic-local-empath-v1",
            "generated_at_unix": time.time(),
            "replay_key": hashlib.sha256(
                (
                    VERSION +
                    "\x00" +
                    _sha256(normalized)
                ).encode("utf-8")
            ).hexdigest(),
        },
    }

    projection["response_calibration"] = _response_calibration(
        signals,
        interaction,
    )

    projection["history"] = _history_projection(
        projection,
        history,
    )

    return projection


def analyze_many(
    messages: Iterable[str],
) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []

    for index, message in enumerate(messages):
        projection = analyze(
            message,
            history=history,
            source_id=f"message:{index}",
        )

        projections.append(projection)
        history.append(projection)

    return projections


__all__ = [
    "SCHEMA",
    "ENGINE",
    "VERSION",
    "analyze",
    "analyze_many",
]
