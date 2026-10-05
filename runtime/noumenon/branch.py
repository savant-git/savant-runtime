from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.noumenon.state import (
    NoumenonState,
)
from runtime.noumenon.store import (
    NoumenonStore,
)


SCHEMA = "savant://noumenon/branch/1"


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class BranchHead:
    noumenon_id: str
    state_digest: str
    generation: int
    predecessor_id: str | None

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "noumenon_id": (
                self.noumenon_id
            ),
            "state_digest": (
                self.state_digest
            ),
            "generation": (
                self.generation
            ),
            "predecessor_id": (
                self.predecessor_id
            ),
        }


@dataclass(frozen=True, slots=True)
class BranchProjection:
    noumenon_id: str
    heads: tuple[
        BranchHead,
        ...,
    ]
    fork_points: tuple[
        str,
        ...,
    ]

    def projection(
        self,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "noumenon_id": (
                self.noumenon_id
            ),
            "heads": [
                head.projection()
                for head in self.heads
            ],
            "fork_points": list(
                self.fork_points
            ),
            "ambiguous": (
                len(self.heads) > 1
            ),
            "derived": True,
            "authoritative": False,
        }

        body["digest"] = _digest(
            body
        )

        return body


def branch_heads(
    states: Sequence[
        NoumenonState
    ],
) -> tuple[
    NoumenonState,
    ...,
]:
    if not states:
        return ()

    state_by_digest = {
        state.state_digest: state
        for state in states
    }

    predecessor_digests = {
        state.predecessor_id
        for state in states
        if state.predecessor_id
        is not None
    }

    heads = tuple(
        state
        for digest, state
        in state_by_digest.items()
        if digest
        not in predecessor_digests
    )

    return tuple(
        sorted(
            heads,
            key=lambda state: (
                state.generation,
                state.state_digest,
            ),
        )
    )


def fork_points(
    states: Sequence[
        NoumenonState
    ],
) -> tuple[str, ...]:
    children: dict[
        str,
        set[str],
    ] = {}

    for state in states:
        if state.predecessor_id is None:
            continue

        children.setdefault(
            state.predecessor_id,
            set(),
        ).add(
            state.state_digest
        )

    return tuple(
        sorted(
            predecessor
            for predecessor, successors
            in children.items()
            if len(successors) > 1
        )
    )


def project_branches(
    states: Sequence[
        NoumenonState
    ],
) -> BranchProjection:
    if not states:
        raise ValueError(
            "at least one state is required"
        )

    identities = {
        state.noumenon_id
        for state in states
    }

    if len(identities) != 1:
        raise ValueError(
            "branch projection cannot mix "
            "noumenon identities"
        )

    identity = next(
        iter(identities)
    )

    heads = branch_heads(
        states
    )

    return BranchProjection(
        noumenon_id=identity,
        heads=tuple(
            BranchHead(
                noumenon_id=(
                    state.noumenon_id
                ),
                state_digest=(
                    state.state_digest
                ),
                generation=(
                    state.generation
                ),
                predecessor_id=(
                    state.predecessor_id
                ),
            )
            for state in heads
        ),
        fork_points=(
            fork_points(states)
        ),
    )


def store_branch_projection(
    store: NoumenonStore,
    noumenon_id: str,
) -> Mapping[str, Any]:
    states = store.lineage(
        noumenon_id
    )

    if not states:
        return {
            "schema": SCHEMA,
            "noumenon_id": noumenon_id,
            "heads": [],
            "fork_points": [],
            "ambiguous": False,
            "derived": True,
            "authoritative": False,
        }

    return project_branches(
        states
    ).projection()
