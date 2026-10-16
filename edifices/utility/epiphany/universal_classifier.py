#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://utility/epiphany/universal-classifier/1.0.0"
owner = "utility"
authority_effect = "none"
utility_level = "epiphany"
utility_ordinal = 4
universally_reusable = True


class universal_classifier_error(RuntimeError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class classification_rule:
    identifier: str
    label: str
    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    minimum_score: float = 1.0
    weight: float = 1.0

    def projection(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "label": self.label,
            "include_terms": list(
                self.include_terms
            ),
            "exclude_terms": list(
                self.exclude_terms
            ),
            "include_patterns": list(
                self.include_patterns
            ),
            "exclude_patterns": list(
                self.exclude_patterns
            ),
            "minimum_score": self.minimum_score,
            "weight": self.weight,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class rule_evidence:
    rule_identifier: str
    label: str
    score: float
    included_terms: tuple[str, ...]
    excluded_terms: tuple[str, ...]
    included_patterns: tuple[str, ...]
    excluded_patterns: tuple[str, ...]
    matched: bool

    def projection(self) -> dict[str, Any]:
        return {
            "rule_identifier":
                self.rule_identifier,
            "label":
                self.label,
            "score":
                self.score,
            "included_terms":
                list(
                    self.included_terms
                ),
            "excluded_terms":
                list(
                    self.excluded_terms
                ),
            "included_patterns":
                list(
                    self.included_patterns
                ),
            "excluded_patterns":
                list(
                    self.excluded_patterns
                ),
            "matched":
                self.matched,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class classification:
    input_digest: str
    labels: tuple[str, ...]
    evidence: tuple[rule_evidence, ...]
    disposition: str
    unresolved: bool

    def projection(self) -> dict[str, Any]:
        return {
            "schema": schema,
            "owner": owner,
            "authority_effect":
                authority_effect,
            "utility_level":
                utility_level,
            "utility_ordinal":
                utility_ordinal,
            "universally_reusable":
                universally_reusable,
            "input_digest":
                self.input_digest,
            "labels":
                list(
                    self.labels
                ),
            "disposition":
                self.disposition,
            "unresolved":
                self.unresolved,
            "evidence": [
                item.projection()
                for item
                in self.evidence
            ],
        }


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
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.casefold(),
    ).strip()


def normalize_term(
    value: str,
) -> str:
    return normalize_text(
        value
    )


def term_present(
    text: str,
    term: str,
) -> bool:
    normalized = normalize_term(
        term
    )

    if not normalized:
        return False

    if re.fullmatch(
        r"[a-z0-9_-]+",
        normalized,
    ):
        return (
            re.search(
                (
                    r"(?<![a-z0-9_-])"
                    + re.escape(
                        normalized
                    )
                    + r"(?![a-z0-9_-])"
                ),
                text,
            )
            is not None
        )

    return normalized in text


def matching_terms(
    text: str,
    terms: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                term
                for term in terms
                if term_present(
                    text,
                    term,
                )
            }
        )
    )


def matching_patterns(
    text: str,
    patterns: Iterable[str],
) -> tuple[str, ...]:
    matched: list[str] = []

    for pattern in patterns:
        try:
            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                matched.append(
                    pattern
                )
        except re.error as exc:
            raise universal_classifier_error(
                "invalid-pattern:"
                f"{pattern}"
            ) from exc

    return tuple(
        sorted(
            set(
                matched
            )
        )
    )


def evaluate_rule(
    *,
    text: str,
    rule: classification_rule,
) -> rule_evidence:
    normalized = normalize_text(
        text
    )

    included_terms = matching_terms(
        normalized,
        rule.include_terms,
    )

    excluded_terms = matching_terms(
        normalized,
        rule.exclude_terms,
    )

    included_patterns = matching_patterns(
        normalized,
        rule.include_patterns,
    )

    excluded_patterns = matching_patterns(
        normalized,
        rule.exclude_patterns,
    )

    positive_count = (
        len(
            included_terms
        )
        + len(
            included_patterns
        )
    )

    negative_count = (
        len(
            excluded_terms
        )
        + len(
            excluded_patterns
        )
    )

    score = (
        float(
            positive_count
            - negative_count
        )
        * float(
            rule.weight
        )
    )

    matched = (
        positive_count > 0
        and negative_count == 0
        and score
        >= float(
            rule.minimum_score
        )
    )

    return rule_evidence(
        rule_identifier=
            rule.identifier,
        label=
            rule.label,
        score=
            score,
        included_terms=
            included_terms,
        excluded_terms=
            excluded_terms,
        included_patterns=
            included_patterns,
        excluded_patterns=
            excluded_patterns,
        matched=
            matched,
    )


def classify_text(
    text: str,
    rules: Sequence[
        classification_rule
    ],
) -> classification:
    if not isinstance(
        text,
        str,
    ):
        raise universal_classifier_error(
            "text-must-be-string"
        )

    evidence = tuple(
        evaluate_rule(
            text=text,
            rule=rule,
        )
        for rule in rules
    )

    labels = tuple(
        sorted(
            {
                item.label
                for item
                in evidence
                if item.matched
            }
        )
    )

    unresolved = (
        len(
            labels
        )
        != 1
    )

    if len(
        labels
    ) == 1:
        disposition = "classified"
    elif not labels:
        disposition = "unclassified"
    else:
        disposition = "ambiguous"

    return classification(
        input_digest=digest(
            text
        ),
        labels=labels,
        evidence=evidence,
        disposition=disposition,
        unresolved=unresolved,
    )


def classify_record(
    record: Mapping[
        str,
        Any,
    ],
    rules: Sequence[
        classification_rule
    ],
) -> classification:
    value = record.get(
        "text"
    )

    if value is None:
        return classification(
            input_digest=digest(
                record
            ),
            labels=(),
            evidence=(),
            disposition="non-textual",
            unresolved=True,
        )

    return classify_text(
        str(
            value
        ),
        rules,
    )


def rule_from_mapping(
    value: Mapping[
        str,
        Any,
    ],
) -> classification_rule:
    identifier = str(
        value.get(
            "identifier",
            "",
        )
    ).strip()

    label = str(
        value.get(
            "label",
            "",
        )
    ).strip()

    if not identifier:
        raise universal_classifier_error(
            "rule-identifier-required"
        )

    if not label:
        raise universal_classifier_error(
            "rule-label-required"
        )

    def strings(
        key: str,
    ) -> tuple[str, ...]:
        raw = value.get(
            key,
            ()
        )

        if raw is None:
            return ()

        if isinstance(
            raw,
            str,
        ):
            raw = [
                raw
            ]

        if not isinstance(
            raw,
            Sequence,
        ):
            raise universal_classifier_error(
                f"{key}-must-be-sequence"
            )

        return tuple(
            str(
                item
            )
            for item
            in raw
        )

    return classification_rule(
        identifier=identifier,
        label=label,
        include_terms=strings(
            "include_terms"
        ),
        exclude_terms=strings(
            "exclude_terms"
        ),
        include_patterns=strings(
            "include_patterns"
        ),
        exclude_patterns=strings(
            "exclude_patterns"
        ),
        minimum_score=float(
            value.get(
                "minimum_score",
                1.0,
            )
        ),
        weight=float(
            value.get(
                "weight",
                1.0,
            )
        ),
    )


def rules_from_json(
    path: str,
) -> tuple[
    classification_rule,
    ...,
]:
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(
                handle
            )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise universal_classifier_error(
            f"rules-unavailable:{path}"
        ) from exc

    if isinstance(
        payload,
        Mapping,
    ):
        raw_rules = payload.get(
            "rules"
        )
    else:
        raw_rules = payload

    if not isinstance(
        raw_rules,
        list,
    ):
        raise universal_classifier_error(
            "rules-must-be-list"
        )

    return tuple(
        rule_from_mapping(
            item
        )
        for item
        in raw_rules
        if isinstance(
            item,
            Mapping,
        )
    )


def selftest() -> dict[str, Any]:
    rules = (
        classification_rule(
            identifier="alpha",
            label="alpha",
            include_terms=(
                "savant",
                "glyph",
            ),
            minimum_score=1.0,
        ),
        classification_rule(
            identifier="beta",
            label="beta",
            include_terms=(
                "viscera",
            ),
            minimum_score=1.0,
        ),
    )

    first = classify_text(
        "Savant composes a glyph.",
        rules,
    )

    second = classify_text(
        "Savant composes a glyph.",
        rules,
    )

    ambiguous = classify_text(
        "Savant and Viscera",
        rules,
    )

    unknown = classify_text(
        "ordinary unrelated material",
        rules,
    )

    checks = {
        "authority_none":
            authority_effect
            == "none",
        "level_04":
            utility_ordinal
            == 4,
        "universally_reusable":
            universally_reusable
            is True,
        "classified":
            first.disposition
            == "classified",
        "label":
            first.labels
            == (
                "alpha",
            ),
        "deterministic":
            first
            == second,
        "ambiguous_preserved":
            ambiguous.disposition
            == "ambiguous"
            and ambiguous.unresolved,
        "unknown_preserved":
            unknown.disposition
            == "unclassified"
            and unknown.unresolved,
    }

    return {
        "schema":
            "savant://utility/epiphany/"
            "universal-classifier-selftest/1.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Apply reusable evidence-preserving "
            "classification rules to normalized text."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
    )

    parser.add_argument(
        "--rules",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        print(
            json.dumps(
                selftest(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0

    if not arguments.input:
        raise universal_classifier_error(
            "input-required"
        )

    if not arguments.rules:
        raise universal_classifier_error(
            "rules-required"
        )

    rules = rules_from_json(
        arguments.rules
    )

    with open(
        arguments.input,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        text = handle.read()

    result = classify_text(
        text,
        rules,
    )

    print(
        json.dumps(
            result.projection(),
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
