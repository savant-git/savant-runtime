
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any


SCHEMA = "savant://cataxis/catalysts/1"

CATALYST_DEFINITIONS = (
    ("assimilation-segregation", "assimilation", "segregation"),
    ("integrity-corruption", "integrity", "corruption"),
    ("clarity-ambiguity", "clarity", "ambiguity"),
    ("expression-suppression", "expression", "suppression"),
    ("authority-autonomy", "authority", "autonomy"),
    ("continuity-disruption", "continuity", "disruption"),
    ("cliche-novelty", "cliche", "novelty"),
    ("alignment-dissonance", "alignment", "dissonance"),
    ("foundation-adaptation", "foundation", "adaptation"),
)

SUPERSESSION = {
    "predecessor": "relevance-superfluosity",
    "successor": "cliche-novelty",
    "historical_record_preserved": True,
    "canonical_registration_claimed": False,
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _coordinate(value: int | float) -> float:
    if isinstance(value, bool):
        raise ValueError("coordinate must be numeric")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError("coordinate must be finite")

    if not 0.0 <= result <= 100.0:
        raise ValueError("coordinate must be between 0 and 100")

    return result


@dataclass(frozen=True, slots=True)
class Catalyst:
    identity: str
    first_pole: str
    second_pole: str

    def position(self, value: int | float) -> dict[str, Any]:
        coordinate = _coordinate(value)
        first_weight = 1.0 - coordinate / 100.0
        second_weight = coordinate / 100.0

        if coordinate < 50.0:
            region = "first-pole-dominant"
        elif coordinate > 50.0:
            region = "second-pole-dominant"
        else:
            region = "midpoint"

        return {
            "catalyst_ref": self.identity,
            "coordinate": coordinate,
            "first_pole": self.first_pole,
            "second_pole": self.second_pole,
            "first_pole_weight": first_weight,
            "second_pole_weight": second_weight,
            "polarity": second_weight - first_weight,
            "region": region,
            "interpolation": "linear",
            "semantic_assessment_performed": False,
            "weights_are_not_observed_probabilities": True,
            "authority_effect": "none",
        }

    def projection(self) -> dict[str, Any]:
        body = {
            "schema": SCHEMA,
            "identity": self.identity,
            "identity_level": "trait",
            "owner_exile": "cataxis",
            "first_pole": self.first_pole,
            "second_pole": self.second_pole,
            "coordinate_min": 0.0,
            "coordinate_midpoint": 50.0,
            "coordinate_max": 100.0,
            "interpolation": "linear",
            "cross_exile_reusable": True,
            "ontology_instance_registered": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }
        body["digest"] = _digest(body)
        return body


CATALYSTS = tuple(
    Catalyst(*definition)
    for definition in CATALYST_DEFINITIONS
)

CATALYST_INDEX = {
    catalyst.identity: catalyst
    for catalyst in CATALYSTS
}


def get_catalyst(identity: str) -> Catalyst:
    return CATALYST_INDEX[identity]


def project_position(
    identity: str,
    coordinate: int | float,
) -> dict[str, Any]:
    return get_catalyst(identity).position(coordinate)


def catalyst_registry() -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "owner_exile": "cataxis",
        "identity_level": "trait",
        "catalyst_count": len(CATALYSTS),
        "catalysts": [
            catalyst.projection()
            for catalyst in CATALYSTS
        ],
        "supersessions": [dict(SUPERSESSION)],
        "historical_cataxes_modified": False,
        "ntempor_modified": False,
        "canonical_registration_claimed": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }
    body["digest"] = _digest(body)
    return body
