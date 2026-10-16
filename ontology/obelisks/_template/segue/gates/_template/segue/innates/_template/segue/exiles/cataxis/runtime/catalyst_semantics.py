
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping


SCHEMA = "savant://cataxis/catalyst-semantics/1"
TRAIT = "catalysts"
OWNER_EXILE = "cataxis"


@dataclass(frozen=True, slots=True)
class Pole:
    name: str
    meaning: str

    def __post_init__(self) -> None:
        if not self.name or not self.meaning:
            raise ValueError("pole name and meaning are required")


@dataclass(frozen=True, slots=True)
class CatalystMote:
    identity: str
    first: Pole
    second: Pole
    distinction: str

    def __post_init__(self) -> None:
        if not self.identity or not self.distinction:
            raise ValueError(
                "catalyst identity and distinction are required"
            )
        if self.first.name == self.second.name:
            raise ValueError("catalyst poles must differ")

    def position(self, coordinate: Any) -> dict[str, Any]:
        value = _coordinate(coordinate)
        first_weight = (Decimal(100) - value) / 100
        second_weight = value / 100
        polarity = second_weight - first_weight

        if value == 0:
            region = "first-pole-endpoint"
        elif value < 50:
            region = "first-pole-dominant"
        elif value == 50:
            region = "midpoint"
        elif value < 100:
            region = "second-pole-dominant"
        else:
            region = "second-pole-endpoint"

        return {
            "schema": SCHEMA,
            "catalyst_ref": self.identity,
            "trait_ref": TRAIT,
            "identity_level": "mote",
            "coordinate": _number(value),
            "first_pole": self.first.name,
            "second_pole": self.second.name,
            "first_weight": _number(first_weight),
            "second_weight": _number(second_weight),
            "polarity": _number(polarity),
            "region": region,
            "interpolation": "linear",
            "interpolation_is_semantic_proof": False,
            "coordinate_is_observation": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

    def describe(self, coordinate: Any) -> dict[str, Any]:
        position = self.position(coordinate)

        return {
            **position,
            "first_pole_meaning": self.first.meaning,
            "second_pole_meaning": self.second.meaning,
            "distinction": self.distinction,
            "interpretation": _interpret(position),
            "interpretation_kind": "coordinate-description",
            "independent_evidence_required": True,
        }

    def projection(self) -> dict[str, Any]:
        body = {
            "schema": SCHEMA,
            "identity": self.identity,
            "identity_level": "mote",
            "parent_trait": TRAIT,
            "owner_exile": OWNER_EXILE,
            "first_pole": {
                "name": self.first.name,
                "meaning": self.first.meaning,
            },
            "second_pole": {
                "name": self.second.name,
                "meaning": self.second.meaning,
            },
            "distinction": self.distinction,
            "coordinate_domain": [0, 100],
            "interpolation": "linear",
            "cross_exile_reusable": True,
            "ontology_registration_claimed": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }
        body["digest"] = _digest(body)
        return body


def _coordinate(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("coordinate must be numeric")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("coordinate must be numeric") from None

    if not result.is_finite():
        raise ValueError("coordinate must be finite")

    if result < 0 or result > 100:
        raise ValueError("coordinate must be between 0 and 100")

    return result


def _number(value: Decimal) -> float:
    return float(value)


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _interpret(position: Mapping[str, Any]) -> str:
    region = position["region"]
    first = position["first_pole"]
    second = position["second_pole"]

    if region == "first-pole-endpoint":
        return f"coordinate at the {first} endpoint"

    if region == "second-pole-endpoint":
        return f"coordinate at the {second} endpoint"

    if region == "first-pole-dominant":
        return f"coordinate favors {first} over {second}"

    if region == "second-pole-dominant":
        return f"coordinate favors {second} over {first}"

    return f"coordinate midpoint between {first} and {second}"


CATALYSTS = (
    CatalystMote(
        "assimilation-segregation",
        Pole(
            "assimilation",
            "integration into a shared structure or system",
        ),
        Pole(
            "segregation",
            "separation into distinct structures or groups",
        ),
        "integration versus separation",
    ),
    CatalystMote(
        "integrity-corruption",
        Pole(
            "integrity",
            "preservation of internal coherence and fidelity",
        ),
        Pole(
            "corruption",
            "degradation or distortion of internal coherence",
        ),
        "preservation versus degradation",
    ),
    CatalystMote(
        "clarity-ambiguity",
        Pole(
            "clarity",
            "explicitness and determinacy of interpretation",
        ),
        Pole(
            "ambiguity",
            "openness to multiple interpretations",
        ),
        "determinate versus multiple interpretation",
    ),
    CatalystMote(
        "expression-suppression",
        Pole(
            "expression",
            "manifestation or communication of content",
        ),
        Pole(
            "suppression",
            "inhibition or withholding of manifestation",
        ),
        "manifestation versus inhibition",
    ),
    CatalystMote(
        "authority-autonomy",
        Pole(
            "authority",
            "direction through an established governing source",
        ),
        Pole(
            "autonomy",
            "self-direction within applicable constraints",
        ),
        "external governance versus self-direction",
    ),
    CatalystMote(
        "continuity-disruption",
        Pole(
            "continuity",
            "preservation of connection across change",
        ),
        Pole(
            "disruption",
            "interruption or departure from an established course",
        ),
        "persistence versus interruption",
    ),
    CatalystMote(
        "cliche-novelty",
        Pole(
            "cliche",
            "preference for familiar and conventional patterns",
        ),
        Pole(
            "novelty",
            "preference for unfamiliar or original patterns",
        ),
        "conventionality versus originality preference",
    ),
    CatalystMote(
        "alignment-dissonance",
        Pole(
            "alignment",
            "correspondence between related elements",
        ),
        Pole(
            "dissonance",
            "tension or incompatibility between related elements",
        ),
        "correspondence versus tension",
    ),
    CatalystMote(
        "foundation-adaptation",
        Pole(
            "foundation",
            "reliance on established supporting structure",
        ),
        Pole(
            "adaptation",
            "adjustment in response to changed conditions",
        ),
        "structural stability versus adjustment",
    ),
)

CATALYST_INDEX = {
    catalyst.identity: catalyst
    for catalyst in CATALYSTS
}

if len(CATALYST_INDEX) != 9:
    raise ValueError("exactly nine distinct catalysts are required")


SUPERSESSION = {
    "predecessor": "relevance-superfluosity",
    "successor": "cliche-novelty",
    "predecessor_active": False,
    "historical_record_preserved": True,
    "canonical_registration_claimed": False,
}


def get_catalyst(identity: str) -> CatalystMote:
    return CATALYST_INDEX[identity]


def project_position(
    identity: str,
    coordinate: Any,
) -> dict[str, Any]:
    return get_catalyst(identity).position(coordinate)


def describe_position(
    identity: str,
    coordinate: Any,
) -> dict[str, Any]:
    return get_catalyst(identity).describe(coordinate)


def project_trait(
    coordinates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    supplied = {} if coordinates is None else dict(coordinates)
    unknown = set(supplied) - set(CATALYST_INDEX)

    if unknown:
        raise ValueError(
            "unknown catalyst identities: "
            + ", ".join(sorted(unknown))
        )

    body = {
        "schema": SCHEMA,
        "identity": TRAIT,
        "identity_level": "trait",
        "owner_exile": OWNER_EXILE,
        "mote_count": len(CATALYSTS),
        "motes": [
            catalyst.projection()
            for catalyst in CATALYSTS
        ],
        "positions": {
            identity: project_position(identity, supplied[identity])
            for identity in sorted(supplied)
        },
        "supersession": dict(SUPERSESSION),
        "historical_cataxes_modified": False,
        "ntempor_modified": False,
        "ontology_registration_claimed": False,
        "source_mutated": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
    body["digest"] = _digest(body)
    return body
