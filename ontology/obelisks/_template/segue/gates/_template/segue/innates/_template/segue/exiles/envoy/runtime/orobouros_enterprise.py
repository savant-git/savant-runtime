#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
from typing import Any, Iterable, Mapping, Sequence


try:
    from . import persona_engine
except ImportError:
    import persona_engine


schema = (
    "savant://envoy/"
    "orobouros-enterprise/1.0.0"
)

policy_schema = (
    "savant://envoy/"
    "orobouros-composition-policy/1.0.0"
)

receipt_schema = (
    "savant://envoy/"
    "orobouros-composition-receipt/1.0.0"
)

owner = "envoy"
execution_owner = "opus"
conversation_owner = "palaver"
task_owner = "niche"
context_owner = "scrybe"

persona_id = "orobouros"

default_policy_version = "1.0.0"

default_trait_cap = 4
absolute_trait_cap = 9

default_switch_threshold = 0.12
default_stickiness_bonus = 0.08

default_latency_weight = 0.04
default_cost_weight = 0.02

epsilon = 1e-9


class orobouros_enterprise_error(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class composition_request:
    domains: tuple[str, ...]
    signals: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    preferred_capabilities: tuple[str, ...]
    previous_traits: tuple[str, ...]
    unavailable_providers: tuple[str, ...]
    maximum_latency_ms: float | None
    maximum_cost: float | None
    requested_cap: int | None
    policy_version: str

    def semantic_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "domains":
                list(
                    self.domains
                ),
            "signals":
                list(
                    self.signals
                ),
            "required_capabilities":
                list(
                    self.required_capabilities
                ),
            "preferred_capabilities":
                list(
                    self.preferred_capabilities
                ),
            "previous_traits":
                list(
                    self.previous_traits
                ),
            "unavailable_providers":
                list(
                    self.unavailable_providers
                ),
            "maximum_latency_ms":
                self.maximum_latency_ms,
            "maximum_cost":
                self.maximum_cost,
            "requested_cap":
                self.requested_cap,
            "policy_version":
                self.policy_version,
        }


def canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return sha256(
        canonical_json(
            value
        )
    ).hexdigest()


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    normalized: set[str] = set()

    for raw in values:
        value = str(
            raw
            or ""
        ).strip().lower()

        if value:
            normalized.add(
                value
            )

    return tuple(
        sorted(
            normalized
        )
    )


def bounded_number(
    value: Any,
    *,
    default: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default

    if not math.isfinite(
        result
    ):
        return default

    return min(
        maximum,
        max(
            minimum,
            result,
        ),
    )


def positive_number(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if (
        not math.isfinite(
            result
        )
        or result < 0
    ):
        return None

    return result


def normalize_request(
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    required_capabilities: Iterable[Any] = (),
    preferred_capabilities: Iterable[Any] = (),
    previous_traits: Iterable[Any] = (),
    unavailable_providers: Iterable[Any] = (),
    maximum_latency_ms: float | None = None,
    maximum_cost: float | None = None,
    requested_cap: int | None = None,
    policy_version: str = default_policy_version,
) -> composition_request:
    normalized_policy = str(
        policy_version
        or default_policy_version
    ).strip()

    if not normalized_policy:
        normalized_policy = (
            default_policy_version
        )

    normalized_cap: int | None

    if requested_cap is None:
        normalized_cap = None
    else:
        normalized_cap = int(
            requested_cap
        )

        if normalized_cap < 0:
            normalized_cap = 0

        normalized_cap = min(
            absolute_trait_cap,
            normalized_cap,
        )

    return composition_request(
        domains=
            normalize_terms(
                domains
            ),
        signals=
            normalize_terms(
                signals
            ),
        required_capabilities=
            normalize_terms(
                required_capabilities
            ),
        preferred_capabilities=
            normalize_terms(
                preferred_capabilities
            ),
        previous_traits=
            normalize_terms(
                previous_traits
            ),
        unavailable_providers=
            normalize_terms(
                unavailable_providers
            ),
        maximum_latency_ms=
            positive_number(
                maximum_latency_ms
            ),
        maximum_cost=
            positive_number(
                maximum_cost
            ),
        requested_cap=
            normalized_cap,
        policy_version=
            normalized_policy,
    )


def trait_id(
    trait: Mapping[str, Any],
) -> str:
    return str(
        trait.get(
            "trait_id"
        )
        or trait.get(
            "id"
        )
        or ""
    ).strip().lower()


def trait_capabilities(
    trait: Mapping[str, Any],
) -> set[str]:
    capabilities: set[str] = {
        trait_id(
            trait
        )
    }

    for field in (
        "capabilities",
        "semantic_capabilities",
        "domains",
        "strengths",
    ):
        raw = trait.get(
            field
        )

        if isinstance(
            raw,
            (
                list,
                tuple,
                set,
            ),
        ):
            capabilities.update(
                normalize_terms(
                    raw
                )
            )

    semantic = trait.get(
        "semantic_capability"
    )

    if semantic:
        capabilities.add(
            str(
                semantic
            ).strip().lower()
        )

    capabilities.discard(
        ""
    )

    return capabilities


def trait_providers(
    trait: Mapping[str, Any],
) -> set[str]:
    providers: set[str] = set()

    direct = trait.get(
        "provider"
    )

    if direct:
        providers.add(
            str(
                direct
            ).strip().lower()
        )

    provenance = trait.get(
        "provenance"
    )

    if isinstance(
        provenance,
        Mapping,
    ):
        provider = provenance.get(
            "provider"
        )

        if provider:
            providers.add(
                str(
                    provider
                ).strip().lower()
            )

    evidence = trait.get(
        "provider_model_evidence"
    )

    if isinstance(
        evidence,
        Sequence,
    ) and not isinstance(
        evidence,
        (
            str,
            bytes,
        ),
    ):
        for item in evidence:
            if not isinstance(
                item,
                Mapping,
            ):
                continue

            provider = item.get(
                "provider"
            )

            if provider:
                providers.add(
                    str(
                        provider
                    )
                    .strip()
                    .lower()
                )

    providers.discard(
        ""
    )

    return providers


def relation_terms(
    trait: Mapping[str, Any],
    *names: str,
) -> set[str]:
    result: set[str] = set()

    for name in names:
        raw = trait.get(
            name
        )

        if isinstance(
            raw,
            (
                list,
                tuple,
                set,
            ),
        ):
            result.update(
                normalize_terms(
                    raw
                )
            )

    return result


def conflicts(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    left_id = trait_id(
        left
    )

    right_id = trait_id(
        right
    )

    left_conflicts = relation_terms(
        left,
        "conflicts",
        "conflicts_with",
    )

    right_conflicts = relation_terms(
        right,
        "conflicts",
        "conflicts_with",
    )

    return (
        right_id
        in left_conflicts
        or left_id
        in right_conflicts
    )


def confidence(
    trait: Mapping[str, Any],
) -> float:
    return bounded_number(
        trait.get(
            "confidence"
        ),
        default=0.70,
    )


def reliability(
    trait: Mapping[str, Any],
) -> float:
    return bounded_number(
        trait.get(
            "reliability"
        ),
        default=0.70,
    )


def priority(
    trait: Mapping[str, Any],
) -> float:
    try:
        raw = float(
            trait.get(
                "priority",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        raw = 0.0

    if not math.isfinite(
        raw
    ):
        return 0.0

    return max(
        0.0,
        raw,
    ) / 100.0


def latency_ms(
    trait: Mapping[str, Any],
) -> float | None:
    for key in (
        "latency_ms",
        "estimated_latency_ms",
        "p50_latency_ms",
    ):
        value = positive_number(
            trait.get(
                key
            )
        )

        if value is not None:
            return value

    return None


def estimated_cost(
    trait: Mapping[str, Any],
) -> float | None:
    for key in (
        "cost",
        "estimated_cost",
        "cost_score",
    ):
        value = positive_number(
            trait.get(
                key
            )
        )

        if value is not None:
            return value

    return None


def provider_available(
    trait: Mapping[str, Any],
    request: composition_request,
) -> bool:
    providers = trait_providers(
        trait
    )

    if not providers:
        return True

    unavailable = set(
        request.unavailable_providers
    )

    return not providers.issubset(
        unavailable
    )


def within_runtime_budgets(
    trait: Mapping[str, Any],
    request: composition_request,
) -> bool:
    if (
        request.maximum_latency_ms
        is not None
    ):
        observed = latency_ms(
            trait
        )

        if (
            observed is not None
            and observed
            > request.maximum_latency_ms
        ):
            return False

    if (
        request.maximum_cost
        is not None
    ):
        observed_cost = (
            estimated_cost(
                trait
            )
        )

        if (
            observed_cost
            is not None
            and observed_cost
            > request.maximum_cost
        ):
            return False

    return True


def trait_score(
    trait: Mapping[str, Any],
    request: composition_request,
) -> tuple[
    float,
    dict[str, Any],
]:
    capabilities = (
        trait_capabilities(
            trait
        )
    )

    domains = set(
        normalize_terms(
            trait.get(
                "domains"
            )
            or ()
        )
    )

    signals = set(
        normalize_terms(
            trait.get(
                "signals"
            )
            or ()
        )
    )

    request_domains = set(
        request.domains
    )

    request_signals = set(
        request.signals
    )

    required = set(
        request.required_capabilities
    )

    preferred = set(
        request.preferred_capabilities
    )

    previous = set(
        request.previous_traits
    )

    required_hits = len(
        capabilities.intersection(
            required
        )
    )

    preferred_hits = len(
        capabilities.intersection(
            preferred
        )
    )

    domain_hits = len(
        domains.intersection(
            request_domains
        )
    )

    signal_hits = len(
        signals.intersection(
            request_signals
        )
    )

    current_confidence = (
        confidence(
            trait
        )
    )

    current_reliability = (
        reliability(
            trait
        )
    )

    current_priority = (
        priority(
            trait
        )
    )

    stickiness = (
        default_stickiness_bonus
        if trait_id(
            trait
        )
        in previous
        else 0.0
    )

    complement_bonus = 0.0

    complements = relation_terms(
        trait,
        "complements",
    )

    if complements.intersection(
        previous
    ):
        complement_bonus = 0.03

    latency_penalty = 0.0

    current_latency = latency_ms(
        trait
    )

    if (
        current_latency is not None
        and request.maximum_latency_ms
    ):
        latency_penalty = min(
            default_latency_weight,
            (
                current_latency
                / max(
                    request.maximum_latency_ms,
                    epsilon,
                )
            )
            * default_latency_weight,
        )

    cost_penalty = 0.0

    current_cost = estimated_cost(
        trait
    )

    if (
        current_cost is not None
        and request.maximum_cost
    ):
        cost_penalty = min(
            default_cost_weight,
            (
                current_cost
                / max(
                    request.maximum_cost,
                    epsilon,
                )
            )
            * default_cost_weight,
        )

    score = (
        required_hits
        * 10.0
        + preferred_hits
        * 3.0
        + domain_hits
        * 2.0
        + signal_hits
        * 1.5
        + current_reliability
        * 2.0
        + current_confidence
        * 1.5
        + current_priority
        + stickiness
        + complement_bonus
        - latency_penalty
        - cost_penalty
    )

    reasons = {
        "required_hits":
            required_hits,
        "preferred_hits":
            preferred_hits,
        "domain_hits":
            domain_hits,
        "signal_hits":
            signal_hits,
        "confidence":
            current_confidence,
        "reliability":
            current_reliability,
        "priority":
            current_priority,
        "stickiness_bonus":
            stickiness,
        "complement_bonus":
            complement_bonus,
        "latency_penalty":
            latency_penalty,
        "cost_penalty":
            cost_penalty,
    }

    return (
        score,
        reasons,
    )


def trait_catalog(
    traits: Iterable[
        Mapping[str, Any]
    ],
) -> dict[
    str,
    Mapping[str, Any],
]:
    result: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for trait in traits:
        identifier = trait_id(
            trait
        )

        if not identifier:
            raise (
                orobouros_enterprise_error(
                    "trait without identity"
                )
            )

        if identifier in result:
            raise (
                orobouros_enterprise_error(
                    "duplicate trait identity: "
                    + identifier
                )
            )

        result[
            identifier
        ] = trait

    return result


def dependency_closure(
    selected: list[
        Mapping[str, Any]
    ],
    catalog: Mapping[
        str,
        Mapping[str, Any],
    ],
    *,
    cap: int,
) -> list[
    Mapping[str, Any]
]:
    output = list(
        selected
    )

    known = {
        trait_id(
            item
        )
        for item in output
    }

    changed = True

    while changed:
        changed = False

        for item in tuple(
            output
        ):
            requirements = (
                relation_terms(
                    item,
                    "requires",
                    "dependencies",
                )
            )

            for required in sorted(
                requirements
            ):
                if required in known:
                    continue

                dependency = catalog.get(
                    required
                )

                if dependency is None:
                    raise (
                        orobouros_enterprise_error(
                            "missing trait dependency: "
                            f"{trait_id(item)}"
                            " requires "
                            f"{required}"
                        )
                    )

                if len(
                    output
                ) >= cap:
                    raise (
                        orobouros_enterprise_error(
                            "trait dependency closure "
                            "would exceed crown cap"
                        )
                    )

                if any(
                    conflicts(
                        dependency,
                        existing,
                    )
                    for existing
                    in output
                ):
                    raise (
                        orobouros_enterprise_error(
                            "trait dependency conflicts "
                            "with selected composition"
                        )
                    )

                output.append(
                    dependency
                )

                known.add(
                    required
                )

                changed = True

    return output


def coverage(
    traits: Iterable[
        Mapping[str, Any]
    ],
) -> set[str]:
    result: set[str] = set()

    for trait in traits:
        result.update(
            trait_capabilities(
                trait
            )
        )

    return result


def resolve_cap(
    persona: Mapping[str, Any],
    requested: int | None,
) -> int:
    crown = persona.get(
        "living_trait_crown"
    )

    if not isinstance(
        crown,
        Mapping,
    ):
        return 0

    minimum = int(
        crown.get(
            "minimum_cap",
            0,
        )
        or 0
    )

    maximum = int(
        crown.get(
            "maximum_cap",
            absolute_trait_cap,
        )
        or absolute_trait_cap
    )

    maximum = min(
        absolute_trait_cap,
        max(
            minimum,
            maximum,
        ),
    )

    default = int(
        crown.get(
            "default_cap",
            default_trait_cap,
        )
        or default_trait_cap
    )

    selected = (
        default
        if requested is None
        else requested
    )

    return min(
        maximum,
        max(
            minimum,
            selected,
        ),
    )


def select_traits(
    *,
    persona: Mapping[str, Any],
    traits: Iterable[
        Mapping[str, Any]
    ],
    request: composition_request,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    catalog = trait_catalog(
        traits
    )

    cap = resolve_cap(
        persona,
        request.requested_cap,
    )

    if cap <= 0:
        required = set(
            request.required_capabilities
        )

        return (
            [],
            {
                "cap":
                    cap,
                "coverage":
                    [],
                "capability_gaps":
                    sorted(
                        required
                    ),
                "degraded":
                    bool(
                        required
                    ),
                "selection_reasons":
                    {},
            },
        )

    ranked: list[
        tuple[
            float,
            str,
            Mapping[str, Any],
            dict[str, Any],
        ]
    ] = []

    rejected: dict[
        str,
        str,
    ] = {}

    for identifier, trait in (
        catalog.items()
    ):
        status = str(
            trait.get(
                "status",
                "active",
            )
        ).strip().lower()

        if status not in {
            "active",
            "accepted",
            "champion",
        }:
            rejected[
                identifier
            ] = (
                "inactive"
            )
            continue

        if not provider_available(
            trait,
            request,
        ):
            rejected[
                identifier
            ] = (
                "provider_unavailable"
            )
            continue

        if not within_runtime_budgets(
            trait,
            request,
        ):
            rejected[
                identifier
            ] = (
                "runtime_budget"
            )
            continue

        score, reasons = trait_score(
            trait,
            request,
        )

        relevant = any(
            (
                reasons[
                    "required_hits"
                ],
                reasons[
                    "preferred_hits"
                ],
                reasons[
                    "domain_hits"
                ],
                reasons[
                    "signal_hits"
                ],
                identifier
                in request.previous_traits,
            )
        )

        if not relevant:
            rejected[
                identifier
            ] = (
                "not_required"
            )
            continue

        ranked.append(
            (
                score,
                identifier,
                trait,
                reasons,
            )
        )

    ranked.sort(
        key=lambda row: (
            -row[0],
            row[1],
        )
    )

    selected: list[
        Mapping[str, Any]
    ] = []

    reasons_by_trait: dict[
        str,
        Any,
    ] = {}

    for (
        score,
        identifier,
        candidate,
        reasons,
    ) in ranked:
        if len(
            selected
        ) >= cap:
            break

        conflict = next(
            (
                existing
                for existing
                in selected
                if conflicts(
                    candidate,
                    existing,
                )
            ),
            None,
        )

        if conflict is not None:
            rejected[
                identifier
            ] = (
                "conflict:"
                + trait_id(
                    conflict
                )
            )
            continue

        previous = (
            identifier
            in request.previous_traits
        )

        if (
            not previous
            and request.previous_traits
            and selected
        ):
            weakest_previous = [
                (
                    trait_score(
                        existing,
                        request,
                    )[0],
                    trait_id(
                        existing
                    ),
                )
                for existing
                in selected
                if trait_id(
                    existing
                )
                in request.previous_traits
            ]

            if weakest_previous:
                threshold = (
                    min(
                        score_value
                        for (
                            score_value,
                            _,
                        )
                        in weakest_previous
                    )
                    + default_switch_threshold
                )

                if score < threshold:
                    rejected[
                        identifier
                    ] = (
                        "hysteresis"
                    )
                    continue

        selected.append(
            candidate
        )

        reasons_by_trait[
            identifier
        ] = {
            **reasons,
            "score":
                score,
        }

    selected = dependency_closure(
        selected,
        catalog,
        cap=cap,
    )

    selected_ids = [
        trait_id(
            item
        )
        for item in selected
    ]

    covered = coverage(
        selected
    )

    required = set(
        request.required_capabilities
    )

    gaps = sorted(
        required
        - covered
    )

    output: list[
        dict[str, Any]
    ] = []

    for trait in selected:
        output.append(
            dict(
                trait
            )
        )

    return (
        output,
        {
            "cap":
                cap,
            "selected":
                selected_ids,
            "coverage":
                sorted(
                    covered
                ),
            "capability_gaps":
                gaps,
            "degraded":
                bool(
                    gaps
                ),
            "selection_reasons":
                reasons_by_trait,
            "rejected":
                dict(
                    sorted(
                        rejected.items()
                    )
                ),
        },
    )


def composition_semantics(
    *,
    persona: Mapping[str, Any],
    request: composition_request,
    selected: Sequence[
        Mapping[str, Any]
    ],
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    identity = persona.get(
        "identity"
    )

    if not isinstance(
        identity,
        Mapping,
    ):
        identity = {}

    baseline = list(
        persona.get(
            "baseline"
        )
        or ()
    )

    selected_traits = [
        {
            "id":
                trait_id(
                    trait
                ),
            "version":
                trait.get(
                    "version"
                ),
            "confidence":
                confidence(
                    trait
                ),
            "reliability":
                reliability(
                    trait
                ),
            "provenance":
                trait.get(
                    "provenance"
                ),
        }
        for trait in selected
    ]

    return {
        "persona_id":
            persona_id,
        "baseline_version":
            identity.get(
                "baseline_version",
                1,
            ),
        "baseline":
            baseline,
        "selected_traits":
            selected_traits,
        "policy_version":
            request.policy_version,
        "request":
            request.semantic_projection(),
        "capability_gaps":
            list(
                selection.get(
                    "capability_gaps"
                )
                or ()
            ),
        "degraded":
            bool(
                selection.get(
                    "degraded",
                    False,
                )
            ),
    }


def project(
    *,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    required_capabilities: Iterable[Any] = (),
    preferred_capabilities: Iterable[Any] = (),
    previous_traits: Iterable[Any] = (),
    unavailable_providers: Iterable[Any] = (),
    maximum_latency_ms: float | None = None,
    maximum_cost: float | None = None,
    cap: int | None = None,
    policy_version: str = default_policy_version,
) -> dict[str, Any]:
    persona = (
        persona_engine.load_persona(
            persona_id
        )
    )

    crown = persona.get(
        "living_trait_crown"
    )

    if not isinstance(
        crown,
        Mapping,
    ):
        raise (
            orobouros_enterprise_error(
                "orobouros crown unavailable"
            )
        )

    pool_id = str(
        crown.get(
            "trait_pool_ref"
        )
        or ""
    ).strip()

    if not pool_id:
        raise (
            orobouros_enterprise_error(
                "orobouros trait pool unavailable"
            )
        )

    pool = (
        persona_engine.load_trait_pool(
            pool_id
        )
    )

    traits = pool.get(
        "traits"
    )

    if not isinstance(
        traits,
        list,
    ):
        raise (
            orobouros_enterprise_error(
                "orobouros trait pool invalid"
            )
        )

    request = normalize_request(
        domains=domains,
        signals=signals,
        required_capabilities=
            required_capabilities,
        preferred_capabilities=
            preferred_capabilities,
        previous_traits=
            previous_traits,
        unavailable_providers=
            unavailable_providers,
        maximum_latency_ms=
            maximum_latency_ms,
        maximum_cost=
            maximum_cost,
        requested_cap=
            cap,
        policy_version=
            policy_version,
    )

    selected, selection = (
        select_traits(
            persona=persona,
            traits=traits,
            request=request,
        )
    )

    semantics = (
        composition_semantics(
            persona=persona,
            request=request,
            selected=selected,
            selection=selection,
        )
    )

    composition_digest = (
        digest(
            semantics
        )
    )

    legacy_projection = (
        persona_engine.compose_persona(
            persona_id=
                persona_id,
            domains=
                request.domains,
            signals=
                request.signals,
            cap=
                selection[
                    "cap"
                ],
        )
    )

    receipt = {
        "schema":
            receipt_schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "policy_version":
            request.policy_version,
        "composition_digest":
            composition_digest,
        "baseline_version":
            semantics[
                "baseline_version"
            ],
        "active_traits": [
            trait_id(
                trait
            )
            for trait in selected
        ],
        "selection":
            selection,
        "request_digest":
            digest(
                request
                .semantic_projection()
            ),
        "trait_pool_digest":
            digest(
                traits
            ),
        "legacy_projection_digest":
            legacy_projection.get(
                "composition_digest"
            ),
        "authority_effect":
            "none",
    }

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "display_name":
            persona.get(
                "display_name"
            ),
        "baseline_version":
            semantics[
                "baseline_version"
            ],
        "baseline":
            semantics[
                "baseline"
            ],
        "living_trait_crown": [
            trait_id(
                trait
            )
            for trait in selected
        ],
        "traits":
            selected,
        "selection":
            selection,
        "composition_digest":
            composition_digest,
        "composition_receipt":
            receipt,
        "voice_ref":
            persona.get(
                "voice_ref"
            ),
        "legacy_projection":
            legacy_projection,
        "compatibility_projection":
            True,
        "capability_gap":
            bool(
                selection[
                    "capability_gaps"
                ]
            ),
        "degraded_mode":
            bool(
                selection[
                    "degraded"
                ]
            ),
        "provider_credentials":
            False,
        "provider_execution":
            False,
        "conversation_ownership":
            False,
        "task_ownership":
            False,
        "context_ownership":
            False,
        "execution_owner":
            execution_owner,
        "conversation_owner":
            conversation_owner,
        "task_owner":
            task_owner,
        "context_owner":
            context_owner,
        "authority_effect":
            "none",
        "observed_at":
            time.time(),
    }


def replay(
    request: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    return project(
        domains=
            request.get(
                "domains"
            )
            or (),
        signals=
            request.get(
                "signals"
            )
            or (),
        required_capabilities=
            request.get(
                "required_capabilities"
            )
            or (),
        preferred_capabilities=
            request.get(
                "preferred_capabilities"
            )
            or (),
        previous_traits=
            request.get(
                "previous_traits"
            )
            or (),
        unavailable_providers=
            request.get(
                "unavailable_providers"
            )
            or (),
        maximum_latency_ms=
            request.get(
                "maximum_latency_ms"
            ),
        maximum_cost=
            request.get(
                "maximum_cost"
            ),
        cap=
            request.get(
                "requested_cap"
            ),
        policy_version=
            str(
                request.get(
                    "policy_version"
                )
                or default_policy_version
            ),
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            policy_schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "policy_version":
            default_policy_version,
        "enhancements": [
            "smallest_sufficient_trait_set",
            "deterministic_normalization",
            "required_capability_coverage",
            "preferred_capability_scoring",
            "dependency_closure",
            "bidirectional_conflict_rejection",
            "provider_availability_filtering",
            "latency_budget_filtering",
            "cost_budget_filtering",
            "confidence_calibration",
            "reliability_weighting",
            "trait_priority_weighting",
            "context_stickiness",
            "trait_hysteresis",
            "complement_awareness",
            "explicit_capability_gaps",
            "degraded_mode_projection",
            "bounded_crown_enforcement",
            "stable_tie_breaking",
            "semantic_composition_digest",
            "composition_receipts",
            "request_replay",
            "legacy_projection_comparison",
            "credential_isolation",
            "provider_neutrality",
            "volatile_telemetry_excluded_from_identity",
        ],
        "external_dependencies":
            [],
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    first = project(
        domains=(
            "engineering",
            "analysis",
        ),
        signals=(
            "implement",
            "verify",
            "architecture",
        ),
        required_capabilities=(
            "coding_precision",
            "uncertainty_calibration",
        ),
        preferred_capabilities=(
            "analytical_rigor",
        ),
    )

    second = replay(
        first[
            "composition_receipt"
        ]
        and normalize_request(
            domains=(
                "engineering",
                "analysis",
            ),
            signals=(
                "implement",
                "verify",
                "architecture",
            ),
            required_capabilities=(
                "coding_precision",
                "uncertainty_calibration",
            ),
            preferred_capabilities=(
                "analytical_rigor",
            ),
        ).semantic_projection()
    )

    if (
        first[
            "composition_digest"
        ]
        != second[
            "composition_digest"
        ]
    ):
        raise (
            orobouros_enterprise_error(
                "deterministic replay failed"
            )
        )

    if len(
        first[
            "living_trait_crown"
        ]
    ) > absolute_trait_cap:
        raise (
            orobouros_enterprise_error(
                "trait cap violated"
            )
        )

    if first[
        "owner"
    ] != owner:
        raise (
            orobouros_enterprise_error(
                "ownership violation"
            )
        )

    if (
        first[
            "provider_execution"
        ]
        is not False
    ):
        raise (
            orobouros_enterprise_error(
                "opus boundary violated"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "composition_digest":
            first[
                "composition_digest"
            ],
        "trait_count":
            len(
                first[
                    "living_trait_crown"
                ]
            ),
        "authority_effect":
            "none",
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
