#!/usr/bin/env python3

from __future__ import annotations

import json

from runtime.constitution import ConstitutionalRegistry
from runtime.memory import MemoryAssertion
from runtime.scrybe import Scrybe


ROOT = "/root/savant-runtime"


def build_scrybe() -> Scrybe:
    registry = ConstitutionalRegistry.load(
        ROOT
    )

    scrybe = Scrybe.install(
        registry,
        instance="lore",
    )

    first = MemoryAssertion.create(
        identity="memory:test:scrybe:001",
        memory_type="semantic",
        subject="scrybe verification",
        content=(
            "The verification raven "
            "prefers the eastern tower."
        ),
        asserted_by="verification",
        source="scrybe_recall_replay_verify",
        occurred_at="2026-08-12T20:00:00Z",
        confidence=0.80,
    )

    second = MemoryAssertion.create(
        identity="memory:test:scrybe:002",
        memory_type="semantic",
        subject="scrybe verification",
        content=(
            "The verification raven "
            "prefers the western tower."
        ),
        asserted_by="verification",
        source="scrybe_recall_replay_verify",
        occurred_at="2026-08-12T20:01:00Z",
        confidence=0.95,
        supersedes=(
            "memory:test:scrybe:001",
        ),
    )

    memory = scrybe.memory.contribute(
        (
            first,
            second,
        )
    )

    return Scrybe(
        memory,
        scrybe.instance,
    )


def main() -> int:
    first = build_scrybe()
    second = build_scrybe()

    query = (
        "Where does the verification "
        "raven prefer to be?"
    )

    recall_a = first.recall(
        query,
        limit=9,
    )

    recall_b = second.recall(
        query,
        limit=9,
    )

    if recall_a != recall_b:
        raise RuntimeError(
            "identical source state produced "
            "different recall"
        )

    identities = [
        item[
            "memory"
        ][
            "identity"
        ]
        for item in recall_a
    ]

    if (
        "memory:test:scrybe:001"
        in identities
    ):
        raise RuntimeError(
            "superseded memory leaked into "
            "current recall"
        )

    if (
        "memory:test:scrybe:002"
        not in identities
    ):
        raise RuntimeError(
            "current memory missing from recall"
        )

    context = first.hydrate(
        query,
        limit=1,
    )

    if context.get(
        "memory_count"
    ) > 1:
        raise RuntimeError(
            "context hydration exceeded limit"
        )

    if context.get(
        "limit"
    ) != 1:
        raise RuntimeError(
            "context hydration did not "
            "preserve requested bound"
        )

    if context.get(
        "authoritative"
    ) is not False:
        raise RuntimeError(
            "Scrybe context became authoritative"
        )

    if context.get(
        "rebuildable"
    ) is not True:
        raise RuntimeError(
            "Scrybe context is not rebuildable"
        )

    historical = first.recall(
        query,
        limit=9,
        at="2026-08-12T20:00:30Z",
    )

    historical_ids = [
        item[
            "memory"
        ][
            "identity"
        ]
        for item in historical
    ]

    if (
        "memory:test:scrybe:001"
        not in historical_ids
    ):
        raise RuntimeError(
            "historical recall failed to "
            "reconstruct prior state"
        )

    if (
        "memory:test:scrybe:002"
        in historical_ids
    ):
        raise RuntimeError(
            "future assertion leaked into "
            "historical recall"
        )

    explanation = first.explain(
        query,
        limit=1,
    )

    if explanation.get(
        "result_count"
    ) != 1:
        raise RuntimeError(
            "explanation result count invalid"
        )

    if not explanation.get(
        "ranking_policy"
    ):
        raise RuntimeError(
            "ranking explanation missing policy"
        )

    result = {
        "ok": True,
        "canonical_memory_store": (
            first.instance
            .canonical_memory_store
        ),
        "independent_memory_store": (
            first.instance
            .independent_memory_store
        ),
        "deterministic_recall": True,
        "current_supersession": True,
        "historical_replay": True,
        "bounded_context": True,
        "context_limit": (
            context[
                "limit"
            ]
        ),
        "context_memory_count": (
            context[
                "memory_count"
            ]
        ),
        "explainable_ranking": True,
        "current_identities": identities,
        "historical_identities": (
            historical_ids
        ),
        "recall_digest": [
            item[
                "scrybe_digest"
            ]
            for item in recall_a
        ],
        "context_digest": (
            context[
                "digest"
            ]
        ),
        "explanation_digest": (
            explanation[
                "digest"
            ]
        ),
        "persistent_mutation": False,
    }

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
