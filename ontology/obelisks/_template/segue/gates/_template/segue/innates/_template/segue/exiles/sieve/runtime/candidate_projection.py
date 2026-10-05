#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator, Mapping


schema = "savant://runtime/sieve/candidate-projection/2.0.1"
record_schema = (
    "savant://runtime/sieve/"
    "candidate-projection-record/2.0.1"
)
owner = "sieve"
authority_effect = "none"


savant_terms = frozenset(
    {
        "savant",
        "straub",
        "datrix",
        "carbon",
        "coda",
        "pryme",
        "thryce",
        "notary",
        "kindred",
        "scrybe",
        "filament",
        "oriel",
        "fruition",
        "opus",
        "urge",
        "niche",
        "lythe",
        "lore",
        "sieve",
        "isotope",
        "dyad",
        "umbra",
        "membrane",
        "obelisk",
        "exile",
        "prodigal",
        "quirk",
        "segue",
        "innate",
        "glyph",
        "source intelligence",
        "fluid canon",
        "universal nine",
    }
)


implementation_terms = frozenset(
    {
        "implement",
        "implementation",
        "implemented",
        "runtime",
        "source code",
        "python",
        "class ",
        "def ",
        "schema",
        "module",
        "function",
        "api",
        "cli",
        "database",
        "persistence",
        "projection",
        "adapter",
        "interface",
        "contract",
        "dependency",
        "dependencies",
    }
)


decision_terms = frozenset(
    {
        "accepted",
        "accept",
        "decision",
        "decided",
        "canonical",
        "canon",
        "authority",
        "authoritative",
        "supersede",
        "superseded",
        "replace",
        "replaced",
        "obsolete",
        "deprecated",
        "deferred",
        "reject",
        "rejected",
        "must",
        "shall",
        "never",
    }
)


historical_terms = frozenset(
    {
        "historical",
        "previous",
        "previously",
        "old",
        "older",
        "legacy",
        "obsolete",
        "deprecated",
        "superseded",
        "formerly",
        "earlier",
    }
)


code_fence_pattern = re.compile(
    r"```(?:[^\n`]*)\n?.*?```",
    re.DOTALL,
)


class candidate_projection_error(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def text_digest(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def iter_jsonl(
    path: Path,
) -> Iterator[Mapping[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            if not line.strip():
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise candidate_projection_error(
                    "invalid jsonl at "
                    f"{path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(value, Mapping):
                continue

            yield value


def message_text(
    record: Mapping[str, Any],
) -> str:
    message = record.get("message")

    if isinstance(message, Mapping):
        text = message.get("text")

        if isinstance(text, str):
            return text

    text = record.get("text")

    if isinstance(text, str):
        return text

    return ""


def normalized_text(text: str) -> str:
    return " ".join(
        text.casefold().split()
    )


def matched_terms(
    text: str,
    terms: frozenset[str],
) -> list[str]:
    lowered = text.casefold()

    return sorted(
        term
        for term in terms
        if term in lowered
    )


def detect_code(
    text: str,
) -> bool:
    return bool(
        code_fence_pattern.search(text)
    )


def classify(
    text: str,
) -> dict[str, Any]:
    savant_matches = matched_terms(
        text,
        savant_terms,
    )

    implementation_matches = matched_terms(
        text,
        implementation_terms,
    )

    decision_matches = matched_terms(
        text,
        decision_terms,
    )

    historical_matches = matched_terms(
        text,
        historical_terms,
    )

    code_present = detect_code(text)

    savant_signal_present = bool(
        savant_matches
    )

    implementation_signal_present = bool(
        implementation_matches
        or code_present
    )

    decision_signal_present = bool(
        decision_matches
    )

    historical_signal_present = bool(
        historical_matches
    )

    return {
        "savant_signal_present": (
            savant_signal_present
        ),
        "implementation_signal_present": (
            implementation_signal_present
        ),
        "decision_signal_present": (
            decision_signal_present
        ),
        "historical_signal_present": (
            historical_signal_present
        ),
        "code_present": code_present,
        "savant_terms": savant_matches,
        "implementation_terms": (
            implementation_matches
        ),
        "decision_terms": decision_matches,
        "historical_terms": historical_matches,
    }


def source_ref_from_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    value = record.get("source_ref")

    if isinstance(value, Mapping):
        return dict(value)

    return {}


def candidate_from_record(
    record: Mapping[str, Any],
) -> dict[str, Any] | None:
    text = message_text(record)

    if not text:
        return None

    signals = classify(text)

    if not signals[
        "savant_signal_present"
    ]:
        return None

    source_ref = source_ref_from_record(
        record
    )

    source_digest = record.get(
        "source_digest"
    )

    message = record.get("message")

    if not isinstance(message, Mapping):
        message = {}

    conversation = record.get(
        "conversation"
    )

    if not isinstance(
        conversation,
        Mapping,
    ):
        conversation = {}

    text_sha256 = text_digest(text)

    candidate_identity = {
        "source_digest": source_digest,
        "source_ref": source_ref,
        "text_sha256": text_sha256,
    }

    candidate_id = digest(
        candidate_identity
    )

    return {
        "schema": record_schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "candidate_id": candidate_id,
        "source_digest": source_digest,
        "source_ref": source_ref,
        "conversation": dict(
            conversation
        ),
        "message": {
            "id": message.get("id"),
            "create_time": (
                message.get(
                    "create_time"
                )
            ),
            "update_time": (
                message.get(
                    "update_time"
                )
            ),
            "author": (
                message.get("author")
            ),
            "metadata": (
                message.get("metadata")
            ),
        },
        "text": text,
        "text_sha256": text_sha256,
        "normalized_text_sha256": (
            text_digest(
                normalized_text(text)
            )
        ),
        "signals": signals,
        "classification": {
            "lane": (
                "savant-recovery-candidate"
            ),
            "semantic_review_required": True,
            "authority_resolution_required": True,
            "owner_resolution_required": True,
            "supersession_resolution_required": True,
            "conflict_resolution_required": True,
            "modernization_required": True,
            "compatibility_verification_required": True,
            "implementation_eligible": False,
        },
        "implementation_gate": [
            "recover",
            "preserve-original-evidence",
            "establish-chronology",
            "resolve-authority",
            "identify-surviving-capability",
            "modernize-for-current-savant",
            "resolve-current-owner",
            "verify-current-compatibility",
            "authorize-implementation",
        ],
        "boundaries": {
            "source_mutated": False,
            "canon_mutated": False,
            "authority_created": False,
            "automatic_admission": False,
            "automatic_supersession": False,
            "automatic_implementation": False,
        },
    }


def project_candidates(
    source: Path,
    output: Path,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()

    if not source.is_file():
        raise candidate_projection_error(
            f"source is not a file: {source}"
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_records = 0
    retained_candidates = 0
    implementation_candidates = 0
    decision_candidates = 0
    historical_candidates = 0
    code_candidates = 0

    output_hasher = hashlib.sha256()

    with output.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as sink:
        for record in iter_jsonl(source):
            input_records += 1

            candidate = candidate_from_record(
                record
            )

            if candidate is None:
                continue

            signals = candidate[
                "signals"
            ]

            if signals[
                "implementation_signal_present"
            ]:
                implementation_candidates += 1

            if signals[
                "decision_signal_present"
            ]:
                decision_candidates += 1

            if signals[
                "historical_signal_present"
            ]:
                historical_candidates += 1

            if signals[
                "code_present"
            ]:
                code_candidates += 1

            rendered = canonical_json(
                candidate
            )

            sink.write(rendered)
            sink.write("\n")

            output_hasher.update(
                rendered.encode("utf-8")
            )
            output_hasher.update(b"\n")

            retained_candidates += 1

    projection = {
        "input_records": input_records,
        "retained_candidates": (
            retained_candidates
        ),
        "implementation_candidates": (
            implementation_candidates
        ),
        "decision_candidates": (
            decision_candidates
        ),
        "historical_candidates": (
            historical_candidates
        ),
        "code_candidates": (
            code_candidates
        ),
        "output_sha256": (
            output_hasher.hexdigest()
        ),
    }

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "source": str(source),
        "output": str(output),
        **projection,
        "projection_digest": digest(
            projection
        ),
        "boundaries": {
            "savant_only_candidate_filter": True,
            "source_mutated": False,
            "canon_mutated": False,
            "authority_created": False,
            "semantic_authority_inferred": False,
            "modernization_required": True,
            "implementation_eligible": False,
        },
    }


def selftest() -> dict[str, Any]:
    savant_text = (
        "savant straub implementation "
        "was previously superseded. "
        "```python\n"
        "def example():\n"
        "    return True\n"
        "```"
    )

    unrelated_text = (
        "ordinary unrelated conversation"
    )

    candidate = candidate_from_record(
        {
            "source_digest": "source",
            "source_ref": {
                "source_file": (
                    "conversations-000.json"
                ),
                "conversation_id": "c1",
                "node_id": "n1",
            },
            "conversation": {
                "id": "c1",
                "title": "test",
            },
            "message": {
                "id": "m1",
                "author": {
                    "role": "user",
                },
                "text": savant_text,
            },
        }
    )

    unrelated = candidate_from_record(
        {
            "message": {
                "text": unrelated_text,
            },
        }
    )

    checks = {
        "authority_none": (
            authority_effect == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "savant_detected": (
            candidate is not None
        ),
        "implementation_detected": (
            bool(
                candidate
                and candidate[
                    "signals"
                ][
                    "implementation_signal_present"
                ]
            )
        ),
        "decision_detected": (
            bool(
                candidate
                and candidate[
                    "signals"
                ][
                    "decision_signal_present"
                ]
            )
        ),
        "historical_detected": (
            bool(
                candidate
                and candidate[
                    "signals"
                ][
                    "historical_signal_present"
                ]
            )
        ),
        "code_detected": (
            bool(
                candidate
                and candidate[
                    "signals"
                ][
                    "code_present"
                ]
            )
        ),
        "unrelated_rejected": (
            unrelated is None
        ),
        "modernization_required": (
            bool(
                candidate
                and candidate[
                    "classification"
                ][
                    "modernization_required"
                ]
            )
        ),
        "implementation_blocked": (
            bool(
                candidate
                and not candidate[
                    "classification"
                ][
                    "implementation_eligible"
                ]
            )
        ),
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "candidate-projection-selftest/2.0.1"
        ),
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--source",
    )

    parser.add_argument(
        "--output",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

    else:
        if not arguments.source:
            parser.error(
                "--source is required"
            )

        if not arguments.output:
            parser.error(
                "--output is required"
            )

        result = project_candidates(
            Path(arguments.source),
            Path(arguments.output),
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
