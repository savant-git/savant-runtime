
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any


schema = "savant://modus/capability-dependency-projection/1.0.0"


class projection_error(ValueError):
    pass


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise projection_error(
            "projection data is not serializable"
        ) from exc

    return hashlib.sha256(encoded).hexdigest()


def _require_mapping(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise projection_error(
            f"{name} must be a mapping"
        )

    result = copy.deepcopy(dict(value))
    _digest(result)
    return result


def project(
    *,
    dependency_projection: Mapping[str, Any],
    capability: Mapping[str, Any],
    mask: Mapping[str, Any] | None,
    verify_dependencies: Callable[..., Any],
    apply_mask: Callable[..., Any],
) -> dict[str, Any]:
    """
    Combine existing projections without acquiring authority.

    Dependency integrity is delegated to Modus's established
    dependency projection verifier.

    Capability-mask interpretation is delegated to the
    existing capability fabric.

    This function never resolves imports, creates capabilities,
    interprets masks, or modifies authoritative records.
    """
    if not callable(verify_dependencies):
        raise projection_error(
            "dependency verifier is required"
        )

    if not callable(apply_mask):
        raise projection_error(
            "capability mask evaluator is required"
        )

    dependencies = _require_mapping(
        dependency_projection,
        "dependency_projection",
    )

    source_capability = _require_mapping(
        capability,
        "capability",
    )

    source_mask = (
        None
        if mask is None
        else _require_mapping(mask, "mask")
    )

    verified = verify_dependencies(
        copy.deepcopy(dependencies)
    )

    if not isinstance(verified, Mapping):
        raise projection_error(
            "dependency verification returned no record"
        )

    if dict(verified) != dependencies:
        raise projection_error(
            "dependency verification changed the record"
        )

    dependency_digest = dependencies.get("digest")

    if (
        not isinstance(dependency_digest, str)
        or not dependency_digest
    ):
        raise projection_error(
            "verified dependency digest is missing"
        )

    evaluation = apply_mask(
        copy.deepcopy(source_capability),
        copy.deepcopy(source_mask),
    )

    evaluation = _require_mapping(
        evaluation,
        "mask evaluation",
    )

    if not isinstance(
        evaluation.get("valid"),
        bool,
    ):
        raise projection_error(
            "mask evaluation validity is missing"
        )

    effective = _require_mapping(
        evaluation.get("effective_capability"),
        "effective_capability",
    )

    violations = evaluation.get("violations")

    if (
        not isinstance(violations, list)
        or not all(
            isinstance(item, str)
            for item in violations
        )
    ):
        raise projection_error(
            "mask violations are invalid"
        )

    if evaluation["valid"] and violations:
        raise projection_error(
            "valid evaluation contains violations"
        )

    if not evaluation["valid"] and not violations:
        raise projection_error(
            "invalid evaluation lacks violations"
        )

    normalized_mask = evaluation.get("mask")

    if normalized_mask is not None:
        normalized_mask = _require_mapping(
            normalized_mask,
            "normalized mask",
        )

        if normalized_mask.get("owner") != "modus":
            raise projection_error(
                "mask ownership mismatch"
            )

    source_digest = source_capability.get(
        "capability_digest"
    )

    effective_digest = effective.get(
        "effective_capability_digest"
    )

    if evaluation["valid"] and normalized_mask is not None:
        if effective.get("source_capability_digest") != source_digest:
            raise projection_error(
                "capability source lineage mismatch"
            )

        if not isinstance(effective_digest, str):
            raise projection_error(
                "effective capability digest is missing"
            )

    result = {
        "schema": schema,
        "modu": dependencies.get("modu"),
        "dependency_projection_digest": dependency_digest,
        "capability_digest": source_digest,
        "effective_capability_digest": effective_digest,
        "valid": evaluation["valid"],
        "mask": normalized_mask,
        "violations": copy.deepcopy(violations),
        "effective_capability": effective,
    }

    result["digest"] = _digest(result)
    return result


def verify(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    current = _require_mapping(
        value,
        "projection",
    )

    signature = current.pop("digest", None)

    if current.get("schema") != schema:
        raise projection_error(
            "unsupported projection schema"
        )

    if not isinstance(signature, str):
        raise projection_error(
            "projection digest is missing"
        )

    if _digest(current) != signature:
        raise projection_error(
            "projection digest mismatch"
        )

    current["digest"] = signature
    return current
