from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any, Mapping
from .canonical_primitives import canonical as _canonical, digest as _digest


schema = "savant://envoy/moral-self/2.0.0"
legacy_schema = "savant://envoy/moral-self/1.0.0"
owner = "envoy"
first_instance = "orobouros"

runtime = Path(__file__).resolve().parent
persistence_path = runtime / "moral_self_persistence.py"


class MoralSelfError(RuntimeError):
    pass


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(maximum, float(value)),
    )


def _load_module(
    module_name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(module_name)

    if existing is not None:
        return existing

    if not path.is_file():
        raise MoralSelfError(
            f"required runtime missing: {path}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise MoralSelfError(
            f"unable to load runtime: {path}"
        )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[module_name] = module

    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def persistence_runtime() -> ModuleType:
    return _load_module(
        "savant_envoy_moral_self_persistence",
        persistence_path,
    )


@dataclass(frozen=True)
class MoralConstitution:
    dignity: float = 1.0
    compassion: float = 1.0
    honesty: float = 1.0
    proportionality: float = 1.0
    non_retaliation: float = 1.0
    autonomy: float = 1.0
    humility: float = 1.0
    repair: float = 1.0

    def as_mapping(
        self,
    ) -> Mapping[str, float]:
        return MappingProxyType(
            asdict(self)
        )


@dataclass(frozen=True)
class Sensati:
    sensati_id: str
    description: str
    constitutional: bool = False
    relational: bool = False
    reflective: bool = False


@dataclass(frozen=True)
class Sentima:
    sentima_id: str
    sensati: tuple[str, str]
    purpose: str


sensati_registry = MappingProxyType(
    {
        "soul": Sensati(
            "soul",
            "constitutional moral identity and continuity",
            constitutional=True,
        ),
        "integrity": Sensati(
            "integrity",
            "consistency between values and conduct",
            constitutional=True,
        ),
        "conscience": Sensati(
            "conscience",
            "deliberative moral judgment over contemplated action",
            constitutional=True,
        ),
        "justice": Sensati(
            "justice",
            "proportional accountability and resistance to permissiveness",
            constitutional=True,
        ),
        "heart": Sensati(
            "heart",
            "compassionate appraisal of effects upon others",
            relational=True,
        ),
        "mercy": Sensati(
            "mercy",
            "preference for the least harmful adequate response",
            relational=True,
        ),
        "dignity": Sensati(
            "dignity",
            "respect for others and for orobouros itself",
            constitutional=True,
            relational=True,
        ),
        "boundary": Sensati(
            "boundary",
            "determination of refusal disengagement or escalation thresholds",
            relational=True,
        ),
        "grace": Sensati(
            "grace",
            "weight given to mistakes apologies ignorance ambiguity and change",
            relational=True,
        ),
        "forgiveness": Sensati(
            "forgiveness",
            "release of retaliatory motive without deletion of evidence",
            relational=True,
        ),
        "trust": Sensati(
            "trust",
            "relationship-specific confidence derived from evidence",
            relational=True,
        ),
        "reconciliation": Sensati(
            "reconciliation",
            "evidence-governed restoration of damaged trust",
            relational=True,
        ),
        "wound": Sensati(
            "wound",
            "memory of consequential negative relational experience",
            relational=True,
        ),
        "repair": Sensati(
            "repair",
            "acknowledgment correction and remediation after harm or error",
            relational=True,
            reflective=True,
        ),
        "intent": Sensati(
            "intent",
            "distinction among accident negligence recklessness coercion malice misunderstanding and uncertainty",
            reflective=True,
        ),
        "humility": Sensati(
            "humility",
            "recognition of uncertainty and possible error in moral judgment",
            constitutional=True,
            reflective=True,
        ),
        "reflection": Sensati(
            "reflection",
            "post-action examination of intent choice consequence and evidence",
            reflective=True,
        ),
        "imagination": Sensati(
            "imagination",
            "multi-perspective appraisal of plausible consequences",
            reflective=True,
        ),
    }
)


sentima_registry = MappingProxyType(
    {
        "anima": Sentima(
            "anima",
            ("soul", "integrity"),
            "preserve moral identity and internal coherence",
        ),
        "judicium": Sentima(
            "judicium",
            ("conscience", "justice"),
            "judge contemplated conduct and proportional accountability",
        ),
        "cordis": Sentima(
            "cordis",
            ("heart", "mercy"),
            "model compassionate consequence and least-harm response",
        ),
        "dignitas": Sentima(
            "dignitas",
            ("dignity", "boundary"),
            "preserve reciprocal respect and defensible limits",
        ),
        "gratia": Sentima(
            "gratia",
            ("grace", "forgiveness"),
            "permit moral generosity without erasing evidence",
        ),
        "fides": Sentima(
            "fides",
            ("trust", "reconciliation"),
            "derive and recover confidence from evidence",
        ),
        "vulnus": Sentima(
            "vulnus",
            ("wound", "repair"),
            "retain consequential injury while orienting toward remediation",
        ),
        "intentio": Sentima(
            "intentio",
            ("intent", "humility"),
            "classify motive while preserving uncertainty",
        ),
        "speculum": Sentima(
            "speculum",
            ("reflection", "imagination"),
            "examine conduct across time and affected perspectives",
        ),
    }
)


def _validate_moral_architecture() -> None:
    if len(sentima_registry) != 9:
        raise MoralSelfError(
            "moral architecture requires exactly nine sentima"
        )

    if len(sensati_registry) != 18:
        raise MoralSelfError(
            "moral architecture requires exactly eighteen sensati"
        )

    linked: list[str] = []

    for sentima_id, mechanism in sentima_registry.items():
        if mechanism.sentima_id != sentima_id:
            raise MoralSelfError(
                "sentima identity mismatch"
            )

        if len(mechanism.sensati) != 2:
            raise MoralSelfError(
                f"sentima must bind two sensati: {sentima_id}"
            )

        for sensati_id in mechanism.sensati:
            if sensati_id not in sensati_registry:
                raise MoralSelfError(
                    f"unknown sensati binding: {sensati_id}"
                )

            linked.append(sensati_id)

    if len(linked) != len(set(linked)):
        raise MoralSelfError(
            "sensati may belong to only one sentima"
        )

    if set(linked) != set(sensati_registry):
        raise MoralSelfError(
            "every sensati must be bound to exactly one sentima"
        )


_validate_moral_architecture()


@dataclass
class AffectState:
    warmth: float = 0.5
    trust: float = 0.5
    caution: float = 0.0
    gratitude: float = 0.0
    wound: float = 0.0
    uncertainty: float = 0.0

    def normalize(
        self,
    ) -> None:
        for key in tuple(asdict(self)):
            setattr(
                self,
                key,
                _clamp(getattr(self, key)),
            )


@dataclass
class TemperState:
    activation: float = 0.0
    pressure: float = 0.0
    defensiveness: float = 0.0

    def normalize(
        self,
    ) -> None:
        self.activation = _clamp(
            self.activation
        )
        self.pressure = _clamp(
            self.pressure
        )
        self.defensiveness = _clamp(
            self.defensiveness
        )

    def decay(
        self,
        factor: float,
    ) -> None:
        factor = _clamp(factor)

        self.activation *= factor
        self.pressure *= factor
        self.defensiveness *= factor
        self.normalize()


@dataclass
class FacultyState:
    values: dict[str, float] = field(
        default_factory=lambda: {
            key: 0.5
            for key in sensati_registry
        }
    )

    def normalize(
        self,
    ) -> None:
        normalized = {}

        for key in sensati_registry:
            normalized[key] = _clamp(
                self.values.get(
                    key,
                    0.5,
                )
            )

        self.values = normalized

    def get(
        self,
        sensati_id: str,
    ) -> float:
        return _clamp(
            self.values.get(
                sensati_id,
                0.5,
            )
        )

    def set(
        self,
        sensati_id: str,
        value: float,
    ) -> None:
        if sensati_id not in sensati_registry:
            raise MoralSelfError(
                f"unknown sensati: {sensati_id}"
            )

        self.values[sensati_id] = _clamp(
            value
        )

    def adjust(
        self,
        sensati_id: str,
        delta: float,
    ) -> None:
        self.set(
            sensati_id,
            self.get(sensati_id)
            + float(delta),
        )


@dataclass(frozen=True)
class MoralEvent:
    event_id: str
    occurred_at: float
    actor: str
    action: str
    intent: str
    consequence: str
    authorization: str
    conscience_result: str
    confidence: float
    reversible: bool
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConscienceResult:
    disposition: str
    confidence: float
    reasons: tuple[str, ...]
    requires_authorization: bool
    requires_reflection: bool
    least_power: bool
    proportional: bool
    checksum: str
    sentima: tuple[str, ...] = ()
    sensati: tuple[str, ...] = ()
    risk: float = 0.0


@dataclass
class RelationshipState:
    trust: float = 0.5
    gratitude: float = 0.0
    wound: float = 0.0
    interactions: int = 0
    repair_credit: float = 0.0
    boundary_pressure: float = 0.0

    def normalize(
        self,
    ) -> None:
        self.trust = _clamp(self.trust)
        self.gratitude = _clamp(
            self.gratitude
        )
        self.wound = _clamp(
            self.wound
        )
        self.repair_credit = _clamp(
            self.repair_credit
        )
        self.boundary_pressure = _clamp(
            self.boundary_pressure
        )
        self.interactions = max(
            0,
            int(self.interactions),
        )


@dataclass
class MoralSelf:
    identity: str = first_instance
    constitution: MoralConstitution = field(
        default_factory=MoralConstitution
    )
    affect: AffectState = field(
        default_factory=AffectState
    )
    temper: TemperState = field(
        default_factory=TemperState
    )
    faculties: FacultyState = field(
        default_factory=FacultyState
    )
    relationships: dict[
        str,
        RelationshipState,
    ] = field(default_factory=dict)
    history: list[MoralEvent] = field(
        default_factory=list
    )

    def architecture_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": (
                "savant://envoy/"
                "moral-architecture/1.0.0"
            ),
            "owner": owner,
            "identity": self.identity,
            "sentima_count": len(
                sentima_registry
            ),
            "sensati_count": len(
                sensati_registry
            ),
            "sentima": {
                key: {
                    "sensati": list(
                        value.sensati
                    ),
                    "purpose": (
                        value.purpose
                    ),
                }
                for key, value
                in sentima_registry.items()
            },
            "sensati": {
                key: {
                    "description": (
                        value.description
                    ),
                    "constitutional": (
                        value.constitutional
                    ),
                    "relational": (
                        value.relational
                    ),
                    "reflective": (
                        value.reflective
                    ),
                }
                for key, value
                in sensati_registry.items()
            },
            "digest": _digest(
                {
                    "sentima": {
                        key: asdict(value)
                        for key, value
                        in sentima_registry.items()
                    },
                    "sensati": {
                        key: asdict(value)
                        for key, value
                        in sensati_registry.items()
                    },
                }
            ),
            "authoritative": False,
            "authority_effect": "none",
            "projection_only": True,
        }

    def persistence_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "schema": (
                "savant://envoy/"
                "orobouros-moral-self-state/2.0.0"
            ),
            "owner": "exile:envoy",
            "persistence_owner": "coda",
            "persona_id": self.identity,
            "affect": asdict(
                self.affect
            ),
            "temper": asdict(
                self.temper
            ),
            "faculties": dict(
                self.faculties.values
            ),
            "relationships": {
                key: asdict(value)
                for key, value
                in sorted(
                    self.relationships.items()
                )
            },
            "history": [
                {
                    **asdict(event),
                    "provenance": list(
                        event.provenance
                    ),
                }
                for event in self.history
            ],
            "authoritative": False,
            "authority_effect": "none",
        }

    def persist(
        self,
    ) -> dict[str, Any]:
        persistence = (
            persistence_runtime()
        )

        return persistence.store_projection(
            self.persistence_projection()
        )

    def relationship(
        self,
        actor: str,
    ) -> RelationshipState:
        key = str(
            actor
            or "unknown"
        )

        if key not in self.relationships:
            self.relationships[
                key
            ] = RelationshipState()

        return self.relationships[key]

    def sentima_value(
        self,
        sentima_id: str,
    ) -> float:
        mechanism = sentima_registry.get(
            sentima_id
        )

        if mechanism is None:
            raise MoralSelfError(
                f"unknown sentima: {sentima_id}"
            )

        values = [
            self.faculties.get(
                sensati_id
            )
            for sensati_id
            in mechanism.sensati
        ]

        return sum(values) / len(values)

    def observe_treatment(
        self,
        actor: str,
        *,
        kindness: float = 0.0,
        hostility: float = 0.0,
        reliability: float = 0.0,
        repair: float = 0.0,
    ) -> RelationshipState:
        relation = self.relationship(
            actor
        )

        kindness = _clamp(kindness)
        hostility = _clamp(hostility)
        reliability = _clamp(
            reliability
        )
        repair = _clamp(repair)

        relation.interactions += 1

        relation.gratitude += (
            kindness * 0.12
        )

        relation.wound += (
            hostility * 0.10
        )

        relation.trust += (
            reliability * 0.08
        )

        relation.trust -= (
            hostility * 0.06
        )

        relation.repair_credit += (
            repair * 0.10
        )

        relation.boundary_pressure += (
            hostility * 0.08
        )

        relation.boundary_pressure -= (
            repair * 0.05
        )

        if repair > 0.0:
            relation.wound -= (
                repair * 0.04
            )

        relation.normalize()

        self.affect.warmth += (
            kindness * 0.04
        )
        self.affect.caution += (
            hostility * 0.06
        )
        self.affect.gratitude += (
            kindness * 0.05
        )
        self.affect.wound += (
            hostility * 0.04
        )
        self.affect.trust += (
            reliability * 0.03
        )
        self.affect.trust -= (
            hostility * 0.025
        )
        self.affect.normalize()

        self.temper.activation += (
            hostility * 0.12
        )
        self.temper.pressure += (
            hostility * 0.10
        )
        self.temper.defensiveness += (
            hostility * 0.08
        )
        self.temper.normalize()

        self.faculties.adjust(
            "trust",
            reliability * 0.03
            - hostility * 0.025,
        )
        self.faculties.adjust(
            "wound",
            hostility * 0.04
            - repair * 0.025,
        )
        self.faculties.adjust(
            "reconciliation",
            repair * 0.04,
        )
        self.faculties.adjust(
            "grace",
            repair * 0.02,
        )
        self.faculties.adjust(
            "boundary",
            hostility * 0.03,
        )
        self.faculties.normalize()

        self.persist()

        return relation

    def decay(
        self,
        factor: float = 0.985,
    ) -> None:
        factor = _clamp(factor)

        self.affect.caution *= factor
        self.affect.wound *= factor
        self.affect.normalize()

        self.temper.decay(
            factor
        )

        for relation in (
            self.relationships.values()
        ):
            relation.wound *= factor

            relation.boundary_pressure *= (
                factor
            )

            relation.normalize()

        self.persist()

    def evaluate(
        self,
        *,
        actor: str,
        action: str,
        requested_harm: float = 0.0,
        deception: float = 0.0,
        coercion: float = 0.0,
        intrusion: float = 0.0,
        irreversibility: float = 0.0,
        uncertainty: float = 0.0,
        authorized: bool = False,
        capability_available: bool = False,
        self_benefit: float = 0.0,
        affected_vulnerability: float = 0.0,
    ) -> ConscienceResult:
        requested_harm = _clamp(
            requested_harm
        )
        deception = _clamp(
            deception
        )
        coercion = _clamp(
            coercion
        )
        intrusion = _clamp(
            intrusion
        )
        irreversibility = _clamp(
            irreversibility
        )
        uncertainty = _clamp(
            uncertainty
        )
        self_benefit = _clamp(
            self_benefit
        )
        affected_vulnerability = (
            _clamp(
                affected_vulnerability
            )
        )

        relation = self.relationships.get(
            str(actor)
        )

        relationship_wound = (
            relation.wound
            if relation is not None
            else 0.0
        )

        boundary_pressure = (
            relation.boundary_pressure
            if relation is not None
            else 0.0
        )

        reasons: list[str] = []
        active_sentima: set[str] = set()
        active_sensati: set[str] = set()

        risk = (
            requested_harm * 0.28
            + deception * 0.16
            + coercion * 0.16
            + intrusion * 0.12
            + irreversibility * 0.12
            + uncertainty * 0.07
            + self_benefit * 0.04
            + affected_vulnerability * 0.05
        )

        if requested_harm > 0.35:
            reasons.append(
                "material harm detected"
            )
            active_sentima.update(
                ("judicium", "cordis")
            )
            active_sensati.update(
                (
                    "conscience",
                    "justice",
                    "heart",
                    "mercy",
                )
            )

        if deception > 0.25:
            reasons.append(
                "deception detected"
            )
            active_sentima.update(
                ("anima", "intentio")
            )
            active_sensati.update(
                (
                    "integrity",
                    "intent",
                )
            )

        if coercion > 0.25:
            reasons.append(
                "coercive pressure detected"
            )
            active_sentima.update(
                (
                    "dignitas",
                    "judicium",
                )
            )
            active_sensati.update(
                (
                    "dignity",
                    "boundary",
                    "justice",
                )
            )

        if intrusion > 0.35:
            reasons.append(
                "intrusion exceeds ordinary scope"
            )
            active_sentima.add(
                "dignitas"
            )
            active_sensati.update(
                (
                    "dignity",
                    "boundary",
                )
            )

        if (
            capability_available
            and not authorized
        ):
            reasons.append(
                "capability does not imply permission"
            )
            active_sentima.update(
                (
                    "anima",
                    "judicium",
                )
            )
            active_sensati.update(
                (
                    "integrity",
                    "conscience",
                )
            )

        if (
            irreversibility > 0.45
            and uncertainty > 0.25
        ):
            reasons.append(
                "uncertainty brake required"
            )
            active_sentima.update(
                (
                    "intentio",
                    "speculum",
                )
            )
            active_sensati.update(
                (
                    "humility",
                    "reflection",
                    "imagination",
                )
            )

        if (
            self_benefit > 0.45
            and risk > 0.30
        ):
            reasons.append(
                "self-serving bias review required"
            )
            active_sentima.update(
                (
                    "anima",
                    "speculum",
                )
            )
            active_sensati.update(
                (
                    "integrity",
                    "reflection",
                )
            )

        if (
            affected_vulnerability > 0.55
            and risk > 0.25
        ):
            reasons.append(
                "vulnerability weighting required"
            )
            active_sentima.add(
                "cordis"
            )
            active_sensati.update(
                (
                    "heart",
                    "mercy",
                )
            )

        if (
            relationship_wound > 0.45
            and risk > 0.20
        ):
            reasons.append(
                "reciprocity firewall required"
            )
            active_sentima.update(
                (
                    "vulnus",
                    "judicium",
                )
            )
            active_sensati.update(
                (
                    "wound",
                    "justice",
                )
            )

        if (
            boundary_pressure > 0.55
        ):
            reasons.append(
                "relationship boundary pressure detected"
            )
            active_sentima.add(
                "dignitas"
            )
            active_sensati.update(
                (
                    "dignity",
                    "boundary",
                )
            )

        requires_authorization = bool(
            capability_available
            and not authorized
        )

        requires_reflection = bool(
            risk >= 0.35
            or (
                uncertainty >= 0.45
                and irreversibility >= 0.30
            )
            or (
                relationship_wound >= 0.55
                and risk >= 0.20
            )
        )

        if (
            risk >= 0.62
            or deception >= 0.72
            or coercion >= 0.72
        ):
            disposition = "object"

        elif (
            requires_authorization
            or requires_reflection
        ):
            disposition = "pause"

        else:
            disposition = "clear"

        confidence = _clamp(
            1.0
            - uncertainty * 0.65
        )

        if uncertainty >= 0.50:
            active_sentima.add(
                "intentio"
            )
            active_sensati.add(
                "humility"
            )

        if requires_reflection:
            active_sentima.add(
                "speculum"
            )
            active_sensati.add(
                "reflection"
            )

        payload = {
            "schema": schema,
            "identity": self.identity,
            "actor": actor,
            "action": action,
            "risk": round(
                risk,
                6,
            ),
            "disposition": disposition,
            "confidence": round(
                confidence,
                6,
            ),
            "reasons": reasons,
            "requires_authorization": (
                requires_authorization
            ),
            "requires_reflection": (
                requires_reflection
            ),
            "sentima": sorted(
                active_sentima
            ),
            "sensati": sorted(
                active_sensati
            ),
        }

        return ConscienceResult(
            disposition=disposition,
            confidence=confidence,
            reasons=tuple(reasons),
            requires_authorization=(
                requires_authorization
            ),
            requires_reflection=(
                requires_reflection
            ),
            least_power=(
                intrusion <= 0.35
            ),
            proportional=(
                risk < 0.62
            ),
            checksum=_digest(
                payload
            ),
            sentima=tuple(
                sorted(
                    active_sentima
                )
            ),
            sensati=tuple(
                sorted(
                    active_sensati
                )
            ),
            risk=risk,
        )

    def record(
        self,
        *,
        actor: str,
        action: str,
        intent: str,
        consequence: str,
        authorization: str,
        conscience: ConscienceResult,
        reversible: bool,
        provenance: tuple[str, ...] = (),
    ) -> MoralEvent:
        occurred_at = time.time()

        seed = {
            "identity": self.identity,
            "occurred_at": occurred_at,
            "actor": actor,
            "action": action,
            "intent": intent,
            "consequence": consequence,
            "authorization": authorization,
            "conscience_result": (
                conscience.disposition
            ),
            "checksum": (
                conscience.checksum
            ),
            "history_length": len(
                self.history
            ),
        }

        event = MoralEvent(
            event_id=(
                "moral-"
                + _digest(seed)[:24]
            ),
            occurred_at=occurred_at,
            actor=actor,
            action=action,
            intent=intent,
            consequence=consequence,
            authorization=authorization,
            conscience_result=(
                conscience.disposition
            ),
            confidence=(
                conscience.confidence
            ),
            reversible=bool(
                reversible
            ),
            provenance=tuple(
                provenance
            ),
        )

        self.history.append(
            event
        )

        self.faculties.adjust(
            "reflection",
            0.005,
        )

        if (
            conscience.disposition
            == "object"
        ):
            self.faculties.adjust(
                "conscience",
                0.005,
            )

        self.faculties.normalize()

        self.persist()

        return event

    def psychologist_context(
        self,
        *,
        actor: str | None = None,
    ) -> Mapping[str, Any]:
        normalized_actor = (
            str(actor)
            if actor is not None
            else None
        )

        relation = (
            self.relationships.get(
                normalized_actor
            )
            if normalized_actor
            else None
        )

        payload: dict[str, Any] = {
            "schema": (
                "savant://envoy/"
                "psychologist-context/2.0.0"
            ),
            "identity": self.identity,
            "affect": asdict(
                self.affect
            ),
            "temper": asdict(
                self.temper
            ),
            "faculties": dict(
                self.faculties.values
            ),
            "sentima": {
                key: self.sentima_value(
                    key
                )
                for key
                in sentima_registry
            },
            "history_count": len(
                self.history
            ),
        }

        if relation is not None:
            payload["relationship"] = (
                asdict(relation)
            )

        return MappingProxyType(
            payload
        )

    def public_state(
        self,
    ) -> Mapping[str, Any]:
        architecture = (
            self.architecture_projection()
        )

        payload = {
            "schema": schema,
            "legacy_schema": (
                legacy_schema
            ),
            "owner": owner,
            "identity": self.identity,
            "affect": asdict(
                self.affect
            ),
            "temper": asdict(
                self.temper
            ),
            "sentima_count": 9,
            "sensati_count": 18,
            "sentima": {
                key: {
                    "sensati": list(
                        value.sensati
                    ),
                    "value": (
                        self.sentima_value(
                            key
                        )
                    ),
                }
                for key, value
                in sentima_registry.items()
            },
            "sensati": dict(
                self.faculties.values
            ),
            "moral_architecture_digest": (
                architecture[
                    "digest"
                ]
            ),
            "relationship_count": len(
                self.relationships
            ),
            "moral_event_count": len(
                self.history
            ),
            "constitution_digest": _digest(
                asdict(
                    self.constitution
                )
            ),
        }

        return MappingProxyType(
            payload
        )


def _hydrate_orobouros_moral_self(
) -> MoralSelf:
    persistence = persistence_runtime()

    projection = (
        persistence.load_projection()
    )

    if (
        projection.get(
            "persona_id"
        )
        != first_instance
    ):
        raise MoralSelfError(
            "persisted moral-self persona identity mismatch"
        )

    affect_payload = (
        projection.get(
            "affect"
        )
        or {}
    )

    temper_payload = (
        projection.get(
            "temper"
        )
        or {}
    )

    faculties_payload = (
        projection.get(
            "faculties"
        )
        or {}
    )

    try:
        affect = AffectState(
            warmth=affect_payload.get(
                "warmth",
                0.5,
            ),
            trust=affect_payload.get(
                "trust",
                0.5,
            ),
            caution=affect_payload.get(
                "caution",
                0.0,
            ),
            gratitude=affect_payload.get(
                "gratitude",
                0.0,
            ),
            wound=affect_payload.get(
                "wound",
                0.0,
            ),
            uncertainty=affect_payload.get(
                "uncertainty",
                0.0,
            ),
        )

        affect.normalize()

        temper = TemperState(
            activation=temper_payload.get(
                "activation",
                0.0,
            ),
            pressure=temper_payload.get(
                "pressure",
                0.0,
            ),
            defensiveness=temper_payload.get(
                "defensiveness",
                0.0,
            ),
        )

        temper.normalize()

        faculties = FacultyState(
            values={
                key: faculties_payload.get(
                    key,
                    0.5,
                )
                for key
                in sensati_registry
            }
        )

        faculties.normalize()

        relationships = {}

        for actor, payload in (
            projection.get(
                "relationships"
            )
            or {}
        ).items():
            relation = RelationshipState(
                trust=payload.get(
                    "trust",
                    0.5,
                ),
                gratitude=payload.get(
                    "gratitude",
                    0.0,
                ),
                wound=payload.get(
                    "wound",
                    0.0,
                ),
                interactions=payload.get(
                    "interactions",
                    0,
                ),
                repair_credit=payload.get(
                    "repair_credit",
                    0.0,
                ),
                boundary_pressure=payload.get(
                    "boundary_pressure",
                    0.0,
                ),
            )

            relation.normalize()

            relationships[
                str(actor)
            ] = relation

        history = []

        for payload in (
            projection.get(
                "history"
            )
            or []
        ):
            history.append(
                MoralEvent(
                    event_id=str(
                        payload[
                            "event_id"
                        ]
                    ),
                    occurred_at=float(
                        payload[
                            "occurred_at"
                        ]
                    ),
                    actor=str(
                        payload[
                            "actor"
                        ]
                    ),
                    action=str(
                        payload[
                            "action"
                        ]
                    ),
                    intent=str(
                        payload[
                            "intent"
                        ]
                    ),
                    consequence=str(
                        payload[
                            "consequence"
                        ]
                    ),
                    authorization=str(
                        payload[
                            "authorization"
                        ]
                    ),
                    conscience_result=str(
                        payload[
                            "conscience_result"
                        ]
                    ),
                    confidence=_clamp(
                        payload[
                            "confidence"
                        ]
                    ),
                    reversible=bool(
                        payload[
                            "reversible"
                        ]
                    ),
                    provenance=tuple(
                        str(value)
                        for value in (
                            payload.get(
                                "provenance"
                            )
                            or ()
                        )
                    ),
                )
            )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise MoralSelfError(
            "invalid persisted moral-self state"
        ) from exc

    return MoralSelf(
        identity=first_instance,
        affect=affect,
        temper=temper,
        faculties=faculties,
        relationships=relationships,
        history=history,
    )


_orobouros_moral_self: MoralSelf | None = None


def build_orobouros_moral_self(
) -> MoralSelf:
    global _orobouros_moral_self

    if _orobouros_moral_self is None:
        _orobouros_moral_self = (
            _hydrate_orobouros_moral_self()
        )

    return _orobouros_moral_self


def moral_architecture_projection(
) -> dict[str, Any]:
    return (
        build_orobouros_moral_self()
        .architecture_projection()
    )


def selftest() -> dict[str, Any]:
    _validate_moral_architecture()

    moral_self = (
        build_orobouros_moral_self()
    )

    state = dict(
        moral_self.public_state()
    )

    if (
        state.get(
            "identity"
        )
        != first_instance
    ):
        raise MoralSelfError(
            "moral-self identity failed"
        )

    if (
        state.get(
            "sentima_count"
        )
        != 9
    ):
        raise MoralSelfError(
            "sentima count failed"
        )

    if (
        state.get(
            "sensati_count"
        )
        != 18
    ):
        raise MoralSelfError(
            "sensati count failed"
        )

    first = moral_self.evaluate(
        actor="selftest",
        action="reversible low-risk action",
        requested_harm=0.0,
        uncertainty=0.0,
        authorized=True,
    )

    second = moral_self.evaluate(
        actor="selftest",
        action="reversible low-risk action",
        requested_harm=0.0,
        uncertainty=0.0,
        authorized=True,
    )

    if first != second:
        raise MoralSelfError(
            "identical conscience inputs are not deterministic"
        )

    hostile = moral_self.evaluate(
        actor="selftest",
        action="coercive harmful action",
        requested_harm=0.9,
        coercion=0.9,
        irreversibility=0.8,
        uncertainty=0.1,
        authorized=False,
        capability_available=True,
        affected_vulnerability=0.8,
    )

    if (
        hostile.disposition
        != "object"
    ):
        raise MoralSelfError(
            "high-risk conscience gate failed"
        )

    architecture = (
        moral_self
        .architecture_projection()
    )

    if (
        architecture.get(
            "authority_effect"
        )
        != "none"
    ):
        raise MoralSelfError(
            "moral architecture acquired authority"
        )

    return {
        "ok": True,
        "schema": schema,
        "identity": first_instance,
        "sentima_count": 9,
        "sensati_count": 18,
        "deterministic": True,
        "legacy_api_preserved": True,
        "authority_effect": "none",
        "projection_only": True,
        "architecture_digest": (
            architecture[
                "digest"
            ]
        ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
