
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

schema = "savant://runtime/urge/opus-method-compiler/1.0.0"

methods = frozenset({
    "combine",
    "idealize",
    "collab",
    "cascade",
    "council",
    "dialectic",
    "swarm",
    "relay",
    "evolve",
})


class method_error(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise method_error(f"{name} is required")
    return value.strip()


def _participants(
    participants: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(participants, (str, bytes)):
        raise method_error("invalid participants")

    result = []
    seen = set()

    for participant in participants:
        if not isinstance(participant, Mapping):
            raise method_error("invalid participant")

        identity = _nonempty(
            participant.get("id"),
            "participant id",
        )

        if identity in seen:
            raise method_error("duplicate participant")

        seen.add(identity)
        result.append(dict(participant))

    if not result:
        raise method_error("participants are required")

    return result


def _step(
    index: int,
    participant: str,
    role: str,
    dependencies: Sequence[int],
    instruction: str,
) -> dict[str, Any]:
    return {
        "index": index,
        "participant": participant,
        "role": role,
        "dependencies": list(dependencies),
        "instruction": instruction,
    }


def compile_method(
    *,
    method: str,
    goal: str,
    participants: Sequence[Mapping[str, Any]],
    previous_result: Any = None,
) -> dict[str, Any]:
    if method not in methods:
        raise method_error("unsupported method")

    goal = _nonempty(goal, "goal")
    members = _participants(participants)
    identities = [p["id"] for p in members]
    count = len(identities)

    if method in {"collab", "council", "dialectic"} and count < 2:
        raise method_error(
            f"{method} requires at least two participants"
        )

    steps: list[dict[str, Any]] = []

    def add(
        participant: str,
        role: str,
        dependencies: Sequence[int],
        instruction: str,
    ) -> int:
        index = len(steps) + 1
        steps.append(
            _step(
                index,
                participant,
                role,
                dependencies,
                instruction,
            )
        )
        return index

    if method == "combine":
        for identity in identities:
            add(
                identity,
                "independent",
                [],
                "Develop an independent solution to the goal.",
            )

        add(
            identities[0],
            "synthesis",
            list(range(1, count + 1)),
            "Integrate compatible contributions. "
            "Preserve disagreements and provenance.",
        )

    elif method == "idealize":
        first = add(
            identities[0],
            "initial",
            [],
            "Develop a feasible baseline solution.",
        )

        for identity in identities:
            first = add(
                identity,
                "refinement",
                [first],
                "Improve the preceding solution while "
                "preserving its justified strengths.",
            )

    elif method == "collab":
        proposals = [
            add(
                identity,
                "proposal",
                [],
                "Propose a complementary contribution.",
            )
            for identity in identities
        ]

        for identity in identities:
            add(
                identity,
                "collaboration",
                proposals,
                "Reconcile the proposals, explicitly "
                "identifying compatible and conflicting ideas.",
            )

    elif method == "cascade":
        dependency = []

        for identity in identities:
            index = add(
                identity,
                "cascade",
                dependency,
                "Extend and improve the preceding output. "
                "Retain its source attribution.",
            )
            dependency = [index]

    elif method == "council":
        opinions = [
            add(
                identity,
                "council_member",
                [],
                "Provide an independent, evidence-aware "
                "assessment of the goal.",
            )
            for identity in identities
        ]

        add(
            identities[0],
            "council_resolution",
            opinions,
            "Identify consensus, disagreement, and "
            "unresolved questions without forcing agreement.",
        )

    elif method == "dialectic":
        thesis = add(
            identities[0],
            "thesis",
            [],
            "Develop a defensible thesis.",
        )

        antithesis = add(
            identities[1],
            "antithesis",
            [thesis],
            "Challenge the thesis with its strongest "
            "supported counterarguments.",
        )

        add(
            identities[0],
            "synthesis",
            [thesis, antithesis],
            "Resolve only justified contradictions. "
            "Preserve unresolved disagreements.",
        )

    elif method == "swarm":
        proposals = [
            add(
                identity,
                "parallel_exploration",
                [],
                "Explore a distinct viable approach. "
                "Identify tradeoffs and assumptions.",
            )
            for identity in identities
        ]

        add(
            identities[0],
            "swarm_selection",
            proposals,
            "Compare alternatives using explicit criteria. "
            "Do not invent evaluation results.",
        )

    elif method == "relay":
        dependency = []

        for identity in identities:
            index = add(
                identity,
                "relay",
                dependency,
                "Advance the shared work from the previous "
                "participant's result.",
            )
            dependency = [index]

    elif method == "evolve":
        dependency = []

        for identity in identities:
            index = add(
                identity,
                "evolution",
                dependency,
                "Produce a materially improved candidate. "
                "State improvements and remaining weaknesses.",
            )
            dependency = [index]

        add(
            identities[0],
            "evolution_selection",
            dependency,
            "Compare the final candidate with the original "
            "goal and available evidence.",
        )

    plan = {
        "schema": schema,
        "method": method,
        "goal": goal,
        "participants": members,
        "previous_result": previous_result,
        "steps": steps,
    }

    plan["digest"] = digest(plan)
    return plan


def verify_plan(
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise method_error("plan must be a mapping")

    supplied = dict(plan)
    signature = supplied.pop("digest", None)

    if signature != digest(supplied):
        raise method_error("plan digest mismatch")

    if supplied.get("schema") != schema:
        raise method_error("unsupported plan schema")

    steps = supplied.get("steps")

    if not isinstance(steps, list) or not steps:
        raise method_error("invalid steps")

    for position, step in enumerate(steps, 1):
        if step.get("index") != position:
            raise method_error("invalid step order")

        dependencies = step.get("dependencies")

        if not isinstance(dependencies, list):
            raise method_error("invalid dependencies")

        if any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or item < 1
            or item >= position
            for item in dependencies
        ):
            raise method_error(
                "invalid dependency reference"
            )

    supplied["digest"] = signature
    return supplied
