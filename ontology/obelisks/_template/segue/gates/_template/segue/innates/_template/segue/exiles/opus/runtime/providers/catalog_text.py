#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from .base import ProviderError
from . import native_text
from . import universal_text

try:
    from ..admission_projection import (
        load_projection,
    )
except ImportError:
    from admission_projection import (
        load_projection,
    )


OPUS_ROOT = Path(
    __file__
).resolve().parents[2]

CATALOG_PATH = (
    OPUS_ROOT
    / "registry"
    / "providers"
    / "universal_text_catalog.json"
)

EXPLICIT_PROFILE_ENV = (
    "OPUS_UNIVERSAL_PROVIDER"
)

SCHEMA = (
    "savant.opus.catalog-text.v5"
)

OWNER = "opus"

UNIVERSAL_PROTOCOLS = {
    "openai_responses",
    "openai_chat",
    "anthropic_messages",
    "gemini_generate_content",
    "generic_json",
}

NATIVE_PROTOCOLS = {
    "bedrock_converse",
    "cohere_chat",
    "ollama_chat",
    "replicate_prediction",
}


def _catalog() -> Dict[str, Any]:
    try:
        value = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError as exc:
        raise ProviderError(
            "opus universal provider catalog missing"
        ) from exc

    except json.JSONDecodeError as exc:
        raise ProviderError(
            "opus universal provider catalog invalid"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise ProviderError(
            "opus universal provider catalog "
            "must be an object"
        )

    profiles = value.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ProviderError(
            "opus universal provider catalog "
            "profiles missing"
        )

    return value


def _env(
    name: object,
) -> str:
    key = str(
        name
        or ""
    ).strip()

    if not key:
        return ""

    return str(
        os.getenv(
            key,
            "",
        )
        or ""
    ).strip()


def _base_configured(
    profile: Dict[str, Any],
) -> bool:
    direct = str(
        profile.get(
            "api_base"
        )
        or ""
    ).strip()

    if direct:
        return True

    return bool(
        _env(
            profile.get(
                "api_base_env"
            )
        )
    )


def _credential_configured(
    profile: Dict[str, Any],
) -> bool:
    header_env = profile.get(
        "header_env"
    )

    if isinstance(
        header_env,
        dict,
    ):
        if any(
            _env(
                value
            )
            for value
            in header_env.values()
        ):
            return True

    if _env(
        profile.get(
            "api_key_env"
        )
    ):
        return True

    if _env(
        profile.get(
            "api_key_env_fallback"
        )
    ):
        return True

    return bool(
        profile.get(
            "api_key_optional",
            False,
        )
    )


def _profile_configured(
    profile_id: str,
    profile: Dict[str, Any],
    *,
    automatic: bool,
) -> bool:
    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).strip().lower()

    if (
        automatic
        and profile_id
        == "custom"
    ):
        return False

    if (
        protocol
        == "bedrock_converse"
    ):
        return (
            native_text.profile_available(
                {
                    **profile,
                    "profile_id":
                        profile_id,
                }
            )
        )

    if (
        protocol
        == "ollama_chat"
    ):
        return _base_configured(
            profile
        )

    if protocol in {
        "cohere_chat",
        "replicate_prediction",
    }:
        return (
            _base_configured(
                profile
            )
            and _credential_configured(
                profile
            )
        )

    if protocol in UNIVERSAL_PROTOCOLS:
        return (
            _base_configured(
                profile
            )
            and _credential_configured(
                profile
            )
        )

    return False


def available_profiles() -> list[str]:
    profiles = _catalog()[
        "profiles"
    ]

    result: list[str] = []

    for (
        profile_id,
        profile,
    ) in profiles.items():
        if not isinstance(
            profile,
            dict,
        ):
            continue

        if _profile_configured(
            str(
                profile_id
            ),
            profile,
            automatic=True,
        ):
            result.append(
                str(
                    profile_id
                )
            )

    return sorted(
        result
    )


def available() -> bool:
    requested = str(
        os.getenv(
            EXPLICIT_PROFILE_ENV,
            "",
        )
        or ""
    ).strip()

    if requested:
        profile = _catalog()[
            "profiles"
        ].get(
            requested
        )

        return (
            isinstance(
                profile,
                dict,
            )
            and _profile_configured(
                requested,
                profile,
                automatic=False,
            )
        )

    projection = (
        load_projection()
    )

    if not isinstance(
        projection,
        dict,
    ):
        return False

    admitted = projection.get(
        "admitted_profiles"
    )

    return bool(
        isinstance(
            admitted,
            list,
        )
        and admitted
    )


def _admitted_candidates(
    profiles: Dict[str, Any],
) -> tuple[
    list[str],
    dict[str, str],
    str | None,
]:
    projection = (
        load_projection()
    )

    if not isinstance(
        projection,
        dict,
    ):
        return (
            [],
            {},
            None,
        )

    admitted_profiles = (
        projection.get(
            "admitted_profiles"
        )
    )

    admitted_models = (
        projection.get(
            "admitted_models"
        )
    )

    if not isinstance(
        admitted_profiles,
        list,
    ):
        return (
            [],
            {},
            None,
        )

    if not isinstance(
        admitted_models,
        dict,
    ):
        admitted_models = {}

    candidates: list[str] = []

    models: dict[
        str,
        str,
    ] = {}

    for value in admitted_profiles:
        profile_id = str(
            value
            or ""
        ).strip()

        if not profile_id:
            continue

        profile = profiles.get(
            profile_id
        )

        if not isinstance(
            profile,
            dict,
        ):
            continue

        if not _profile_configured(
            profile_id,
            profile,
            automatic=True,
        ):
            continue

        candidates.append(
            profile_id
        )

        model = str(
            admitted_models.get(
                profile_id
            )
            or ""
        ).strip()

        if model:
            models[
                profile_id
            ] = model

    return (
        candidates,
        models,
        str(
            projection.get(
                "digest"
            )
            or ""
        ).strip()
        or None,
    )


def _bounded_score(
    value: Any,
    *,
    default: float = 0.5,
) -> float:
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        result = default

    return max(
        0.0,
        min(
            1.0,
            result,
        ),
    )


def _evidence_profile(
    item: Mapping[str, Any],
) -> str:
    return str(
        item.get(
            "provider_profile"
        )
        or item.get(
            "provider"
        )
        or ""
    ).strip()


def _evidence_model(
    item: Mapping[str, Any],
) -> str:
    return str(
        item.get(
            "model"
        )
        or ""
    ).strip()


def _evidence_trait(
    item: Mapping[str, Any],
) -> str:
    return str(
        item.get(
            "trait_id"
        )
        or ""
    ).strip()


def _evidence_value(
    item: Mapping[str, Any],
) -> float:
    score = _bounded_score(
        item.get(
            "score"
        )
    )

    confidence = _bounded_score(
        item.get(
            "confidence"
        )
    )

    reliability = _bounded_score(
        item.get(
            "reliability"
        )
    )

    return (
        score
        * confidence
        * reliability
    )


def _rank_candidates(
    request: Dict[str, Any],
    candidates: list[
        tuple[
            str,
            Dict[str, Any],
            str | None,
        ]
    ],
) -> tuple[
    list[
        tuple[
            str,
            Dict[str, Any],
            str | None,
        ]
    ],
    list[Dict[str, Any]],
    bool,
]:
    trait_id = str(
        request.get(
            "trait_id"
        )
        or ""
    ).strip()

    raw_evidence = request.get(
        "provider_model_evidence"
    )

    if (
        not trait_id
        or not isinstance(
            raw_evidence,
            Sequence,
        )
        or isinstance(
            raw_evidence,
            (
                str,
                bytes,
                bytearray,
            ),
        )
    ):
        return (
            candidates,
            [],
            False,
        )

    candidate_ids = {
        profile_id
        for (
            profile_id,
            _,
            _,
        ) in candidates
    }

    candidate_models = {
        profile_id: str(
            admitted_model
            or ""
        ).strip()
        for (
            profile_id,
            _,
            admitted_model,
        ) in candidates
    }

    evidence_rows: list[
        Dict[str, Any]
    ] = []

    profile_scores: dict[
        str,
        list[float],
    ] = {}

    for raw_item in raw_evidence:
        if not isinstance(
            raw_item,
            Mapping,
        ):
            continue

        evidence_trait = (
            _evidence_trait(
                raw_item
            )
        )

        if (
            evidence_trait
            and evidence_trait
            != trait_id
        ):
            continue

        evidence_profile = (
            _evidence_profile(
                raw_item
            )
        )

        evidence_model = (
            _evidence_model(
                raw_item
            )
        )

        matched_profile = ""

        if (
            evidence_profile
            in candidate_ids
        ):
            matched_profile = (
                evidence_profile
            )

        elif evidence_model:
            for (
                profile_id,
                admitted_model,
            ) in candidate_models.items():
                if (
                    admitted_model
                    and admitted_model
                    == evidence_model
                ):
                    matched_profile = (
                        profile_id
                    )
                    break

        if not matched_profile:
            continue

        value = _evidence_value(
            raw_item
        )

        profile_scores.setdefault(
            matched_profile,
            [],
        ).append(
            value
        )

        evidence_rows.append(
            {
                "trait_id": trait_id,
                "provider_profile": (
                    matched_profile
                ),
                "model": (
                    evidence_model
                    or candidate_models.get(
                        matched_profile,
                        "",
                    )
                ),
                "score": _bounded_score(
                    raw_item.get(
                        "score"
                    )
                ),
                "confidence": (
                    _bounded_score(
                        raw_item.get(
                            "confidence"
                        )
                    )
                ),
                "reliability": (
                    _bounded_score(
                        raw_item.get(
                            "reliability"
                        )
                    )
                ),
                "selection_value": (
                    value
                ),
                "provenance": (
                    raw_item.get(
                        "provenance"
                    )
                ),
            }
        )

    if not profile_scores:
        return (
            candidates,
            evidence_rows,
            False,
        )

    aggregate_scores = {
        profile_id: (
            sum(values)
            / len(values)
        )
        for (
            profile_id,
            values,
        ) in profile_scores.items()
        if values
    }

    original_order = {
        profile_id: index
        for (
            index,
            (
                profile_id,
                _,
                _,
            ),
        ) in enumerate(
            candidates
        )
    }

    ranked = sorted(
        candidates,
        key=lambda candidate: (
            0
            if candidate[0]
            in aggregate_scores
            else 1,
            -aggregate_scores.get(
                candidate[0],
                0.0,
            ),
            original_order[
                candidate[0]
            ],
        ),
    )

    for row in evidence_rows:
        row[
            "aggregate_profile_score"
        ] = aggregate_scores.get(
            row[
                "provider_profile"
            ]
        )

    return (
        ranked,
        evidence_rows,
        True,
    )


def _selection_candidates(
    request: Dict[str, Any],
) -> tuple[
    list[
        tuple[
            str,
            Dict[str, Any],
            str | None,
        ]
    ],
    str | None,
    bool,
    list[Dict[str, Any]],
    bool,
]:
    requested = str(
        request.get(
            "provider_profile"
        )
        or os.getenv(
            EXPLICIT_PROFILE_ENV,
            "",
        )
        or ""
    ).strip()

    profiles = _catalog()[
        "profiles"
    ]

    if requested:
        profile = profiles.get(
            requested
        )

        if not isinstance(
            profile,
            dict,
        ):
            raise ProviderError(
                "unknown opus provider profile: "
                f"{requested}"
            )

        if not _profile_configured(
            requested,
            profile,
            automatic=False,
        ):
            raise ProviderError(
                "opus provider profile unavailable: "
                f"{requested}"
            )

        return (
            [
                (
                    requested,
                    dict(
                        profile
                    ),
                    None,
                )
            ],
            None,
            True,
            [],
            False,
        )

    (
        admitted,
        admitted_models,
        admission_digest,
    ) = _admitted_candidates(
        profiles
    )

    if not admitted:
        raise ProviderError(
            "no admitted opus catalog "
            "provider projection available"
        )

    candidates = [
        (
            profile_id,
            dict(
                profiles[
                    profile_id
                ]
            ),
            admitted_models.get(
                profile_id
            ),
        )
        for profile_id
        in admitted
    ]

    (
        ranked_candidates,
        selection_evidence,
        evidence_ranked,
    ) = _rank_candidates(
        request,
        candidates,
    )

    return (
        ranked_candidates,
        admission_digest,
        False,
        selection_evidence,
        evidence_ranked,
    )


def _infer_profile(
    request: Dict[str, Any],
    provider: Dict[str, Any],
    *,
    profile_id: str,
    profile: Dict[str, Any],
    admitted_model: str | None,
) -> Dict[str, Any]:
    protocol = str(
        profile.get(
            "protocol"
        )
        or ""
    ).strip().lower()

    profile[
        "profile_id"
    ] = profile_id

    delegated = dict(
        request
    )

    delegated[
        "provider_profile"
    ] = profile_id

    if (
        not str(
            delegated.get(
                "model"
            )
            or delegated.get(
                "requested_model"
            )
            or ""
        ).strip()
        and admitted_model
    ):
        delegated[
            "model"
        ] = admitted_model

    if protocol in NATIVE_PROTOCOLS:
        return native_text.infer(
            delegated,
            provider,
            profile,
        )

    if protocol in UNIVERSAL_PROTOCOLS:
        return universal_text.infer(
            delegated,
            provider,
        )

    raise ProviderError(
        "unsupported catalog protocol: "
        f"{protocol}"
    )


def infer(
    request: Dict[str, Any],
    provider: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(
        request,
        dict,
    ):
        raise ProviderError(
            "request must be an object"
        )

    (
        candidates,
        admission_digest,
        explicit_selection,
        selection_evidence,
        evidence_ranked,
    ) = _selection_candidates(
        request
    )

    attempts: list[
        dict[str, Any]
    ] = []

    last_error: (
        Exception
        | None
    ) = None

    for (
        profile_id,
        profile,
        admitted_model,
    ) in candidates:
        try:
            result = _infer_profile(
                request,
                provider,
                profile_id=(
                    profile_id
                ),
                profile=profile,
                admitted_model=(
                    admitted_model
                ),
            )

        except Exception as exc:
            last_error = exc

            attempts.append(
                {
                    "profile_id":
                        profile_id,
                    "state":
                        "failed",
                    "error_type":
                        type(
                            exc
                        ).__name__,
                }
            )

            if explicit_selection:
                raise

            continue

        if not isinstance(
            result,
            dict,
        ):
            last_error = ProviderError(
                "catalog provider returned "
                "non-object result"
            )

            attempts.append(
                {
                    "profile_id":
                        profile_id,
                    "state":
                        "failed",
                    "error_type":
                        "ProviderError",
                }
            )

            if explicit_selection:
                raise last_error

            continue

        attempts.append(
            {
                "profile_id":
                    profile_id,
                "state":
                    "succeeded",
                "model":
                    (
                        result.get(
                            "model"
                        )
                        or admitted_model
                    ),
            }
        )

        result[
            "provider"
        ] = "catalog_text"

        result[
            "provider_profile"
        ] = profile_id

        result[
            "catalog_schema"
        ] = SCHEMA

        result[
            "owner"
        ] = OWNER

        result[
            "authority_effect"
        ] = "none"

        result[
            "catalog_attempts"
        ] = attempts

        result[
            "admission_selected"
        ] = bool(
            admission_digest
        )

        result[
            "trait_evidence_ranked"
        ] = evidence_ranked

        result[
            "trait_selection_evidence"
        ] = selection_evidence

        result[
            "selection_trait_id"
        ] = str(
            request.get(
                "trait_id"
            )
            or ""
        ).strip()

        result[
            "selection_candidates"
        ] = [
            candidate_profile
            for (
                candidate_profile,
                _,
                _,
            ) in candidates
        ]

        result[
            "selection_authority_effect"
        ] = "none"

        if admission_digest:
            result[
                "admission_projection_digest"
            ] = admission_digest

        return result

    if last_error is not None:
        raise ProviderError(
            "all admitted opus catalog "
            "provider profiles failed"
        ) from last_error

    raise ProviderError(
        "no admitted opus catalog "
        "provider could be executed"
    )
