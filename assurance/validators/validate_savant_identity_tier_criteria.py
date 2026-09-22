#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_CRITERIA_PATH = Path(
    "/root/savant-runtime/canon/structure/"
    "SAVANT_IDENTITY_TIER_CRITERIA_v1.0.0.json"
)

EXPECTED_LEVELS = [
    "iota",
    "mote",
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "portal",
    "obelisk",
]

EXPECTED_EMERGENCE = [
    "Identity",
    "Coherence",
    "Disposition",
    "Behavior",
    "Capability",
    "Agency",
    "Faculty",
    "Access",
    "Sovereignty",
]

EXPECTED_MOODS = [
    "anima",
    "weld",
    "kiln",
    "graft",
    "aria",
    "mantle",
    "fulcrum",
    "echelon",
    "ascent",
]


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValueError(message)


def load(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"missing criteria file: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"criteria file is empty: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        "criteria root must be an object",
    )

    return value


def validate_tiers(
    tiers: object,
) -> None:
    require(
        isinstance(tiers, list),
        "tiers must be a list",
    )

    require(
        len(tiers) == 9,
        "exactly nine tiers are required",
    )

    require(
        all(
            isinstance(tier, dict)
            for tier in tiers
        ),
        "every tier must be an object",
    )

    require(
        [
            tier.get("rank")
            for tier in tiers
        ]
        == list(range(1, 10)),
        "tier ranks must be exactly 1 through 9",
    )

    require(
        [
            tier.get("name")
            for tier in tiers
        ]
        == EXPECTED_LEVELS,
        "tier names or order do not match authority",
    )

    require(
        [
            tier.get("emergence")
            for tier in tiers
        ]
        == EXPECTED_EMERGENCE,
        "emergent properties do not match authority",
    )

    require(
        len(
            {
                tier.get("emergence")
                for tier in tiers
            }
        )
        == 9,
        "every tier must have a distinct emergent property",
    )

    for index, tier in enumerate(tiers):
        name = str(
            tier.get(
                "name",
                f"rank-{index + 1}",
            )
        )

        expected_child = (
            None
            if index == 0
            else EXPECTED_LEVELS[index - 1]
        )

        expected_parent = (
            None
            if index == 8
            else EXPECTED_LEVELS[index + 1]
        )

        require(
            tier.get("child")
            == expected_child,
            f"{name} child mismatch",
        )

        require(
            tier.get("parent")
            == expected_parent,
            f"{name} parent mismatch",
        )

        require(
            isinstance(
                tier.get("essence"),
                str,
            )
            and bool(
                tier["essence"].strip()
            ),
            f"{name} lacks constitutive essence",
        )

        require(
            isinstance(
                tier.get("scope"),
                str,
            )
            and bool(
                tier["scope"].strip()
            ),
            f"{name} lacks canonical scope",
        )

        must = tier.get("must")

        require(
            isinstance(must, list),
            f"{name}.must must be a list",
        )

        require(
            len(must) == 9,
            f"{name} must have exactly nine required criteria",
        )

        require(
            all(
                isinstance(item, str)
                and bool(item.strip())
                for item in must
            ),
            f"{name} contains an invalid required criterion",
        )

        require(
            len(set(must))
            == len(must),
            f"{name} required criteria must be unique",
        )

        must_not = tier.get(
            "must_not"
        )

        require(
            isinstance(
                must_not,
                list,
            )
            and bool(must_not),
            f"{name} must have disqualifiers",
        )

        require(
            all(
                isinstance(item, str)
                and bool(item.strip())
                for item in must_not
            ),
            f"{name} contains an invalid disqualifier",
        )

        require(
            len(set(must_not))
            == len(must_not),
            f"{name} disqualifiers must be unique",
        )

        require(
            isinstance(
                tier.get("proof"),
                str,
            )
            and bool(
                tier["proof"].strip()
            ),
            f"{name} lacks substantiation proof",
        )


def validate_moods(
    moods: object,
) -> None:
    require(
        isinstance(moods, list),
        "criterion_mood_pipeline must be a list",
    )

    require(
        len(moods) == 9,
        "exactly nine mood operators are required",
    )

    require(
        all(
            isinstance(mood, dict)
            for mood in moods
        ),
        "every mood binding must be an object",
    )

    require(
        [
            mood.get("mood")
            for mood in moods
        ]
        == EXPECTED_MOODS,
        "mood operator order does not match authority",
    )

    for mood in moods:
        name = str(
            mood.get(
                "mood",
                "unknown",
            )
        )

        require(
            isinstance(
                mood.get("function"),
                str,
            )
            and bool(
                mood["function"].strip()
            ),
            f"{name} lacks criterion function",
        )


def validate_audit_matrix(
    audit: object,
) -> None:
    require(
        isinstance(audit, dict),
        "audit_matrix must be an object",
    )

    require(
        audit.get("passes") == 50,
        "audit matrix must declare fifty lenses",
    )

    lenses = audit.get(
        "lenses"
    )

    require(
        isinstance(lenses, list),
        "audit lenses must be a list",
    )

    require(
        len(lenses) == 50,
        "audit matrix must contain exactly fifty lenses",
    )

    require(
        all(
            isinstance(lens, str)
            and bool(lens.strip())
            for lens in lenses
        ),
        "audit matrix contains an invalid lens",
    )

    require(
        len(set(lenses)) == 50,
        "audit lenses must be unique",
    )


def validate_scaffolding(
    scaffolding: object,
) -> None:
    require(
        isinstance(
            scaffolding,
            dict,
        ),
        "scaffolding must be an object",
    )

    require(
        scaffolding.get(
            "roads"
        )
        == "Segues",
        "Segues must remain the scaffold roads",
    )

    require(
        scaffolding.get(
            "travel_unit"
        )
        == "typed transit envelope",
        "travel unit must be the typed transit envelope",
    )

    envelope_fields = (
        scaffolding.get(
            "transit_envelope_fields"
        )
    )

    require(
        isinstance(
            envelope_fields,
            list,
        )
        and bool(
            envelope_fields
        ),
        "transit envelope fields must be a non-empty list",
    )

    require(
        len(
            set(
                envelope_fields
            )
        )
        == len(
            envelope_fields
        ),
        "transit envelope fields must be unique",
    )

    shardization = (
        scaffolding.get(
            "runtime_shardization"
        )
    )

    require(
        isinstance(
            shardization,
            dict,
        ),
        "runtime_shardization must be an object",
    )

    require(
        shardization.get(
            "status"
        )
        == "semantics-deferred",
        "runtime shard semantics must remain deferred",
    )

    established = (
        shardization.get(
            "established_now"
        )
    )

    require(
        isinstance(
            established,
            list,
        )
        and bool(
            established
        ),
        "runtime shard constraints must be recorded",
    )


def validate_dependencies(
    dependency_decision: object,
) -> None:
    require(
        isinstance(
            dependency_decision,
            dict,
        ),
        "dependency_decision must be an object",
    )

    require(
        dependency_decision.get(
            "required_now"
        )
        == [],
        "no external dependency is required now",
    )

    recommended = (
        dependency_decision.get(
            "recommended_optional"
        )
    )

    require(
        isinstance(
            recommended,
            list,
        ),
        "recommended_optional must be a list",
    )

    names = [
        item.get("name")
        for item in recommended
        if isinstance(item, dict)
    ]

    require(
        names
        == [
            "CUE",
            "JSON Schema 2020-12",
            "Hypothesis",
            "NetworkX",
        ],
        "optional dependency decisions do not match the criteria",
    )


def main() -> int:
    path = (
        Path(sys.argv[1]).expanduser()
        if len(sys.argv) > 1
        else DEFAULT_CRITERIA_PATH
    )

    if not path.is_absolute():
        print(
            "ERROR: criteria path must be absolute",
            file=sys.stderr,
        )
        return 2

    try:
        data = load(path)

        require(
            data.get("status")
            in {
                "authority-candidate",
                "accepted-authority",
            },
            "invalid authority status",
        )

        require(
            data.get(
                "mutation_authorized"
            )
            is False,
            "criteria must not authorize mutation",
        )

        require(
            data.get("edifice")
            == EXPECTED_LEVELS,
            "identity edifice mismatch",
        )

        universal = data.get(
            "universal_instance_criteria"
        )

        require(
            isinstance(
                universal,
                list,
            )
            and len(
                universal
            )
            == 9,
            "exactly nine universal instance criteria are required",
        )

        require(
            len(
                set(
                    universal
                )
            )
            == 9,
            "universal instance criteria must be unique",
        )

        law = data.get(
            "composition_law"
        )

        require(
            isinstance(
                law,
                dict,
            ),
            "composition_law must be an object",
        )

        require(
            law.get(
                "stable_parent_minimum_distinct_active_children"
            )
            == 2,
            "minimum direct child cardinality must be two",
        )

        validate_tiers(
            data.get("tiers")
        )

        validate_moods(
            data.get(
                "criterion_mood_pipeline"
            )
        )

        validate_audit_matrix(
            data.get(
                "audit_matrix"
            )
        )

        validate_scaffolding(
            data.get(
                "scaffolding"
            )
        )

        validate_dependencies(
            data.get(
                "dependency_decision"
            )
        )

        print(
            f"CRITERIA: {path}"
        )
        print(
            "IDENTITY TIERS: 9"
        )
        print(
            "EMERGENT PROPERTIES: 9 distinct"
        )
        print(
            "MOOD OPERATORS: 9"
        )
        print(
            "AUDIT LENSES: 50"
        )
        print(
            "MINIMUM DIRECT CHILDREN: 2"
        )
        print(
            "RUNTIME SHARDIZATION: semantics deferred"
        )
        print(
            "MUTATION AUTHORIZED: false"
        )
        print(
            "SAVANT IDENTITY CRITERIA: validated"
        )

        return 0

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        TypeError,
    ) as exc:
        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
