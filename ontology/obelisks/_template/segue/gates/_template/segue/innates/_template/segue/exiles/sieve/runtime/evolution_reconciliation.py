#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator, Mapping


schema = (
    "savant://runtime/sieve/"
    "evolution-reconciliation/2.0.1"
)

record_schema = (
    "savant://runtime/sieve/"
    "evolution-reconciliation-record/2.0.1"
)

cluster_schema = (
    "savant://runtime/sieve/"
    "evidence-clusters/2.0.1"
)

owner = "sieve"
authority_effect = "none"


class evolution_reconciliation_error(
    RuntimeError
):
    pass


supersession_terms = frozenset(
    {
        "supersede",
        "superseded",
        "supersedes",
        "replace",
        "replaced",
        "replaces",
        "obsolete",
        "deprecated",
        "formerly",
        "no longer",
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
        "earlier",
        "formerly",
        "obsolete",
        "deprecated",
        "superseded",
    }
)

authority_terms = frozenset(
    {
        "accepted decision",
        "accepted authority",
        "authoritative",
        "authority",
        "canon",
        "canonical",
        "constitutional",
    }
)

code_fence_pattern = re.compile(
    r"```(?P<header>[^\n`]*)\n?"
    r"(?P<body>.*?)```",
    re.DOTALL,
)


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
        ).encode("utf-8")
    ).hexdigest()


def text_digest(
    text: str,
) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def normalized_text(
    text: str,
) -> str:
    return " ".join(
        text.casefold().split()
    )


def normalized_text_digest(
    text: str,
) -> str:
    return text_digest(
        normalized_text(text)
    )


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
                value = json.loads(
                    line
                )
            except json.JSONDecodeError as exc:
                raise (
                    evolution_reconciliation_error(
                        "invalid jsonl at "
                        f"{path}:{line_number}: "
                        f"{exc}"
                    )
                ) from exc

            if isinstance(
                value,
                Mapping,
            ):
                yield value


def candidate_text(
    candidate: Mapping[str, Any],
) -> str:
    text = candidate.get(
        "text"
    )

    if isinstance(
        text,
        str,
    ):
        return text

    return ""


def candidate_id(
    candidate: Mapping[str, Any],
) -> str:
    value = candidate.get(
        "candidate_id"
    )

    if isinstance(
        value,
        str,
    ) and value:
        return value

    return digest(
        {
            "source_digest": (
                candidate.get(
                    "source_digest"
                )
            ),
            "source_ref": (
                candidate.get(
                    "source_ref"
                )
            ),
            "text_sha256": (
                candidate.get(
                    "text_sha256"
                )
                or text_digest(
                    candidate_text(
                        candidate
                    )
                )
            ),
        }
    )


def contains_term(
    text: str,
    terms: frozenset[str],
) -> bool:
    lowered = text.casefold()

    return any(
        term in lowered
        for term in terms
    )


def code_fences(
    text: str,
) -> list[dict[str, Any]]:
    fences: list[
        dict[str, Any]
    ] = []

    for index, match in enumerate(
        code_fence_pattern.finditer(
            text
        )
    ):
        full_text = match.group(0)
        header = (
            match.group(
                "header"
            )
            or ""
        )
        body = (
            match.group(
                "body"
            )
            or ""
        )

        fences.append(
            {
                "index": index,
                "language_hint": (
                    header.strip()
                    or None
                ),
                "text": full_text,
                "body": body,
                "text_sha256": (
                    text_digest(
                        full_text
                    )
                ),
                "body_sha256": (
                    text_digest(
                        body
                    )
                ),
                "start": (
                    match.start()
                ),
                "end": (
                    match.end()
                ),
            }
        )

    return fences


def source_role(
    candidate: Mapping[str, Any],
) -> str | None:
    message = candidate.get(
        "message"
    )

    if not isinstance(
        message,
        Mapping,
    ):
        return None

    author = message.get(
        "author"
    )

    if not isinstance(
        author,
        Mapping,
    ):
        return None

    role = author.get(
        "role"
    )

    if isinstance(
        role,
        str,
    ):
        return role

    return None


def source_time(
    candidate: Mapping[str, Any],
) -> Any:
    message = candidate.get(
        "message"
    )

    if isinstance(
        message,
        Mapping,
    ):
        value = message.get(
            "create_time"
        )

        if value is not None:
            return value

    conversation = candidate.get(
        "conversation"
    )

    if isinstance(
        conversation,
        Mapping,
    ):
        return conversation.get(
            "create_time"
        )

    return None


def reconcile_candidate(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    text = candidate_text(
        candidate
    )

    candidate_identifier = (
        candidate_id(
            candidate
        )
    )

    semantic_fingerprint = (
        normalized_text_digest(
            text
        )
    )

    fences = code_fences(
        text
    )

    historical = contains_term(
        text,
        historical_terms,
    )

    supersession = contains_term(
        text,
        supersession_terms,
    )

    authority_language = (
        contains_term(
            text,
            authority_terms,
        )
    )

    role = source_role(
        candidate
    )

    user_source = (
        role == "user"
    )

    evidence_lane = (
        "historical-evidence"
        if historical
        else "unresolved-evidence"
    )

    lifecycle_lane = (
        "supersession-review"
        if supersession
        else "authority-review"
    )

    result = {
        "schema": record_schema,
        "owner": owner,
        "authority_effect": (
            authority_effect
        ),
        "authoritative": False,
        "candidate_id": (
            candidate_identifier
        ),
        "source_digest": (
            candidate.get(
                "source_digest"
            )
        ),
        "source_ref": (
            candidate.get(
                "source_ref"
            )
        ),
        "conversation": (
            candidate.get(
                "conversation"
            )
        ),
        "message": (
            candidate.get(
                "message"
            )
        ),
        "text": text,
        "text_sha256": (
            candidate.get(
                "text_sha256"
            )
            or text_digest(
                text
            )
        ),
        "semantic_fingerprint": (
            semantic_fingerprint
        ),
        "signals": (
            candidate.get(
                "signals"
            )
        ),
        "reconciliation": {
            "evidence_lane": (
                evidence_lane
            ),
            "lifecycle_lane": (
                lifecycle_lane
            ),
            "historical_signal": (
                historical
            ),
            "supersession_signal": (
                supersession
            ),
            "authority_language_signal": (
                authority_language
            ),
            "source_role": role,
            "user_source": (
                user_source
            ),
            "user_source_auto_authority": (
                False
            ),
            "duplicate_merge_allowed": (
                False
            ),
            "automatic_supersession": (
                False
            ),
            "automatic_conflict_resolution": (
                False
            ),
            "automatic_authority_resolution": (
                False
            ),
            "modernization_required": (
                True
            ),
            "implementation_eligible": (
                False
            ),
        },
        "code": {
            "fence_count": len(
                fences
            ),
            "fences": fences,
            "exact_source_projection": (
                True
            ),
        },
        "implementation_gate": [
            "preserve-original-evidence",
            "establish-historical-context",
            "compare-current-authority",
            "resolve-supersession",
            "resolve-conflicts",
            "determine-surviving-capability",
            "redesign-for-current-savant",
            "massively-modernize",
            "resolve-current-owner",
            "verify-current-primitives",
            "verify-current-invariants",
            "authorize-implementation",
        ],
        "boundaries": {
            "source_mutated": False,
            "canon_mutated": False,
            "authority_created": False,
            "historical_source_rewritten": (
                False
            ),
            "duplicate_source_merged": (
                False
            ),
            "recovered_content_implemented": (
                False
            ),
        },
    }

    result[
        "reconciliation_digest"
    ] = digest(
        {
            "candidate_id": (
                candidate_identifier
            ),
            "semantic_fingerprint": (
                semantic_fingerprint
            ),
            "reconciliation": (
                result[
                    "reconciliation"
                ]
            ),
            "code_fence_digests": [
                fence[
                    "text_sha256"
                ]
                for fence in fences
            ],
        }
    )

    return result


def cluster_projection(
    clusters: Mapping[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:
    projected: list[
        dict[str, Any]
    ] = []

    duplicate_cluster_count = 0
    duplicate_candidate_count = 0

    for fingerprint in sorted(
        clusters
    ):
        records = clusters[
            fingerprint
        ]

        identifiers = sorted(
            str(
                record[
                    "candidate_id"
                ]
            )
            for record in records
        )

        duplicate = (
            len(records) > 1
        )

        if duplicate:
            duplicate_cluster_count += 1
            duplicate_candidate_count += (
                len(records)
            )

        source_digests = sorted(
            {
                str(value)
                for value in (
                    record.get(
                        "source_digest"
                    )
                    for record in records
                )
                if value is not None
            }
        )

        source_refs = [
            record.get(
                "source_ref"
            )
            for record in records
        ]

        cluster_id = digest(
            {
                "semantic_fingerprint": (
                    fingerprint
                ),
                "candidate_ids": (
                    identifiers
                ),
            }
        )

        projected.append(
            {
                "cluster_id": (
                    cluster_id
                ),
                "semantic_fingerprint": (
                    fingerprint
                ),
                "candidate_count": (
                    len(records)
                ),
                "duplicate": (
                    duplicate
                ),
                "candidate_ids": (
                    identifiers
                ),
                "source_digests": (
                    source_digests
                ),
                "source_refs": (
                    source_refs
                ),
                "merge_performed": (
                    False
                ),
                "authority_effect": (
                    "none"
                ),
            }
        )

    projection = {
        "schema": cluster_schema,
        "owner": owner,
        "authority_effect": (
            authority_effect
        ),
        "authoritative": False,
        "cluster_count": len(
            projected
        ),
        "duplicate_cluster_count": (
            duplicate_cluster_count
        ),
        "duplicate_candidate_count": (
            duplicate_candidate_count
        ),
        "clusters": projected,
        "boundaries": {
            "duplicate_detection_only": (
                True
            ),
            "duplicates_merged": False,
            "authority_created": False,
            "canon_mutated": False,
        },
    }

    projection[
        "projection_digest"
    ] = digest(
        {
            "cluster_count": (
                projection[
                    "cluster_count"
                ]
            ),
            "duplicate_cluster_count": (
                duplicate_cluster_count
            ),
            "duplicate_candidate_count": (
                duplicate_candidate_count
            ),
            "clusters": projected,
        }
    )

    return projection


def reconcile(
    source: Path,
    output: Path,
    clusters_output: Path,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    clusters_output = (
        clusters_output.resolve()
    )

    if not source.is_file():
        raise (
            evolution_reconciliation_error(
                "source is not a file: "
                f"{source}"
            )
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    clusters_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_count = 0
    historical_count = 0
    supersession_count = 0
    authority_language_count = 0
    code_fence_count = 0

    output_hasher = hashlib.sha256()

    clusters: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    with output.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as sink:
        for candidate in iter_jsonl(
            source
        ):
            reconciled = (
                reconcile_candidate(
                    candidate
                )
            )

            candidate_count += 1

            reconciliation = (
                reconciled[
                    "reconciliation"
                ]
            )

            if reconciliation[
                "historical_signal"
            ]:
                historical_count += 1

            if reconciliation[
                "supersession_signal"
            ]:
                supersession_count += 1

            if reconciliation[
                "authority_language_signal"
            ]:
                authority_language_count += 1

            code_fence_count += int(
                reconciled[
                    "code"
                ][
                    "fence_count"
                ]
            )

            fingerprint = str(
                reconciled[
                    "semantic_fingerprint"
                ]
            )

            clusters.setdefault(
                fingerprint,
                [],
            ).append(
                {
                    "candidate_id": (
                        reconciled[
                            "candidate_id"
                        ]
                    ),
                    "source_digest": (
                        reconciled.get(
                            "source_digest"
                        )
                    ),
                    "source_ref": (
                        reconciled.get(
                            "source_ref"
                        )
                    ),
                }
            )

            rendered = canonical_json(
                reconciled
            )

            sink.write(
                rendered
            )
            sink.write(
                "\n"
            )

            output_hasher.update(
                rendered.encode(
                    "utf-8"
                )
            )
            output_hasher.update(
                b"\n"
            )

    clusters_projection = (
        cluster_projection(
            clusters
        )
    )

    clusters_rendered = json.dumps(
        clusters_projection,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    clusters_output.write_text(
        clusters_rendered + "\n",
        encoding="utf-8",
    )

    projection = {
        "candidate_count": (
            candidate_count
        ),
        "cluster_count": (
            clusters_projection[
                "cluster_count"
            ]
        ),
        "duplicate_cluster_count": (
            clusters_projection[
                "duplicate_cluster_count"
            ]
        ),
        "historical_count": (
            historical_count
        ),
        "supersession_count": (
            supersession_count
        ),
        "authority_language_count": (
            authority_language_count
        ),
        "code_fence_count": (
            code_fence_count
        ),
        "output_sha256": (
            output_hasher.hexdigest()
        ),
        "clusters_sha256": (
            text_digest(
                clusters_rendered
                + "\n"
            )
        ),
    }

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": (
            authority_effect
        ),
        "authoritative": False,
        "source": str(
            source
        ),
        "output": str(
            output
        ),
        "clusters_output": str(
            clusters_output
        ),
        **projection,
        "projection_digest": (
            digest(
                projection
            )
        ),
        "boundaries": {
            "source_mutated": False,
            "canon_mutated": False,
            "authority_created": False,
            "duplicates_merged": False,
            "automatic_supersession": (
                False
            ),
            "automatic_conflict_resolution": (
                False
            ),
            "automatic_implementation": (
                False
            ),
            "modernization_required": (
                True
            ),
            "implementation_eligible": (
                False
            ),
        },
    }


def selftest() -> dict[str, Any]:
    source_text = (
        "savant historical implementation "
        "was superseded by a newer design.\n"
        "```python\n"
        "def old_runtime():\n"
        "    return 'historical'\n"
        "```"
    )

    candidate = {
        "candidate_id": "candidate-a",
        "source_digest": "source-a",
        "source_ref": {
            "source_file": (
                "conversations-000.json"
            ),
            "conversation_id": "c1",
            "node_id": "n1",
        },
        "conversation": {
            "id": "c1",
        },
        "message": {
            "id": "m1",
            "create_time": 1.0,
            "author": {
                "role": "user",
            },
        },
        "text": source_text,
        "text_sha256": (
            text_digest(
                source_text
            )
        ),
    }

    first = reconcile_candidate(
        candidate
    )

    duplicate = dict(
        candidate
    )

    duplicate[
        "candidate_id"
    ] = "candidate-b"

    duplicate[
        "source_digest"
    ] = "source-b"

    second = reconcile_candidate(
        duplicate
    )

    clusters = cluster_projection(
        {
            first[
                "semantic_fingerprint"
            ]: [
                {
                    "candidate_id": (
                        first[
                            "candidate_id"
                        ]
                    ),
                    "source_digest": (
                        first[
                            "source_digest"
                        ]
                    ),
                    "source_ref": (
                        first[
                            "source_ref"
                        ]
                    ),
                },
                {
                    "candidate_id": (
                        second[
                            "candidate_id"
                        ]
                    ),
                    "source_digest": (
                        second[
                            "source_digest"
                        ]
                    ),
                    "source_ref": (
                        second[
                            "source_ref"
                        ]
                    ),
                },
            ]
        }
    )

    checks = {
        "authority_none": (
            authority_effect
            == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "code_preserved": (
            first[
                "code"
            ][
                "fence_count"
            ]
            == 1
            and first[
                "code"
            ][
                "fences"
            ][0][
                "text"
            ]
            in source_text
        ),
        "duplicate_clustered": (
            clusters[
                "duplicate_cluster_count"
            ]
            == 1
        ),
        "duplicate_not_merged": (
            clusters[
                "clusters"
            ][0][
                "merge_performed"
            ]
            is False
        ),
        "historical_detected": (
            first[
                "reconciliation"
            ][
                "historical_signal"
            ]
            is True
        ),
        "supersession_detected": (
            first[
                "reconciliation"
            ][
                "supersession_signal"
            ]
            is True
        ),
        "user_not_auto_authority": (
            first[
                "reconciliation"
            ][
                "user_source_auto_authority"
            ]
            is False
        ),
        "modernization_required": (
            first[
                "reconciliation"
            ][
                "modernization_required"
            ]
            is True
        ),
        "implementation_not_ready": (
            first[
                "reconciliation"
            ][
                "implementation_eligible"
            ]
            is False
        ),
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "evolution-reconciliation-selftest/"
            "2.0.1"
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

    parser.add_argument(
        "--clusters-output",
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

        if not arguments.clusters_output:
            parser.error(
                "--clusters-output is required"
            )

        result = reconcile(
            Path(
                arguments.source
            ),
            Path(
                arguments.output
            ),
            Path(
                arguments.clusters_output
            ),
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
