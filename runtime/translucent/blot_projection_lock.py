#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_acceptance import (
    AcceptanceDecision,
)
from runtime.translucent.blot_replay import (
    ReplayBinding,
    ReplayResult,
)
from runtime.translucent.blot_verify import (
    VerificationReport,
)


name = "blot."
schema = "savant.translucent.blot.projection-lock.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True


class BlotProjectionLockError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BlotProjectionLockError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotProjectionLockError(
            f"{field_name} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = str(value or "").strip()

        if not token or token in seen:
            continue

        seen.add(token)
        result.append(token)

    return tuple(result)


def _normalized(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if hasattr(value, "normalized"):
        result = value.normalized()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise BlotProjectionLockError(
            f"{field_name} must provide normalized() "
            "or be a mapping"
        )

    if not isinstance(result, Mapping):
        raise BlotProjectionLockError(
            f"{field_name}.normalized() must return a mapping"
        )

    return dict(result)


@dataclass(frozen=True)
class ProjectionLock:
    source_digest: str
    construction_digest: str
    execution_digest: str
    projection_digest: str
    verification_digest: str
    acceptance_digest: str
    replay_binding_digest: str
    replay_result_digest: str
    profile_id: str
    locked: bool
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema": schema,
            "name": name,
            "source_digest": _text(
                self.source_digest,
                "source_digest",
            ),
            "construction_digest": _text(
                self.construction_digest,
                "construction_digest",
            ),
            "execution_digest": _text(
                self.execution_digest,
                "execution_digest",
            ),
            "projection_digest": _text(
                self.projection_digest,
                "projection_digest",
            ),
            "verification_digest": _text(
                self.verification_digest,
                "verification_digest",
            ),
            "acceptance_digest": _text(
                self.acceptance_digest,
                "acceptance_digest",
            ),
            "replay_binding_digest": _text(
                self.replay_binding_digest,
                "replay_binding_digest",
            ),
            "replay_result_digest": _text(
                self.replay_result_digest,
                "replay_result_digest",
            ),
            "profile_id": _text(
                self.profile_id,
                "profile_id",
            ),
            "locked": bool(self.locked),
            "lineage": list(
                _unique(self.lineage)
            ),
            "provenance": list(
                _unique(self.provenance)
            ),
            "authority_effect": authority_effect,
            "mutation_effect": mutation_effect,
            "projection_only": projection_only,
            "creates_authority": False,
            "projection_is_authority": False,
        }

        return {
            **body,
            "digest": _digest(body),
        }


def lock(
    *,
    verification: VerificationReport | Mapping[str, Any],
    acceptance: AcceptanceDecision | Mapping[str, Any],
    replay_binding: ReplayBinding | Mapping[str, Any],
    replay_result: ReplayResult | Mapping[str, Any],
    profile_id: str,
    lineage: Iterable[str] = (),
    provenance: Iterable[str] = (),
) -> ProjectionLock:
    verification_data = _normalized(
        verification,
        "verification",
    )
    acceptance_data = _normalized(
        acceptance,
        "acceptance",
    )
    binding_data = _normalized(
        replay_binding,
        "replay_binding",
    )
    replay_data = _normalized(
        replay_result,
        "replay_result",
    )

    verification_digest = str(
        verification_data.get("digest")
        or _digest(verification_data)
    )

    acceptance_digest = str(
        acceptance_data.get("digest")
        or _digest(acceptance_data)
    )

    binding_digest = str(
        binding_data.get("digest")
        or _digest(binding_data)
    )

    replay_result_digest = str(
        replay_data.get("digest")
        or _digest(replay_data)
    )

    source_digest = _text(
        verification_data.get("source_digest"),
        "source_digest",
    )

    construction_digest = _text(
        verification_data.get("construction_digest"),
        "construction_digest",
    )

    execution_digest = _text(
        verification_data.get("execution_digest"),
        "execution_digest",
    )

    projection_digest = _text(
        verification_data.get("projection_digest"),
        "projection_digest",
    )

    if (
        acceptance_data.get("verification_digest")
        != verification_digest
    ):
        raise BlotProjectionLockError(
            "acceptance is not bound to verification"
        )

    if (
        acceptance_data.get("source_digest")
        != source_digest
    ):
        raise BlotProjectionLockError(
            "acceptance source digest mismatch"
        )

    if (
        acceptance_data.get("construction_digest")
        != construction_digest
    ):
        raise BlotProjectionLockError(
            "acceptance construction digest mismatch"
        )

    if (
        acceptance_data.get("execution_digest")
        != execution_digest
    ):
        raise BlotProjectionLockError(
            "acceptance execution digest mismatch"
        )

    if (
        acceptance_data.get("projection_digest")
        != projection_digest
    ):
        raise BlotProjectionLockError(
            "acceptance projection digest mismatch"
        )

    if (
        binding_data.get("source_digest")
        != source_digest
    ):
        raise BlotProjectionLockError(
            "replay binding source digest mismatch"
        )

    if (
        binding_data.get("construction_digest")
        != construction_digest
    ):
        raise BlotProjectionLockError(
            "replay binding construction digest mismatch"
        )

    if (
        binding_data.get("execution_digest")
        != execution_digest
    ):
        raise BlotProjectionLockError(
            "replay binding execution digest mismatch"
        )

    if (
        binding_data.get("projection_digest")
        != projection_digest
    ):
        raise BlotProjectionLockError(
            "replay binding projection digest mismatch"
        )

    if (
        replay_data.get("binding_digest")
        != binding_digest
    ):
        raise BlotProjectionLockError(
            "replay result is not bound to replay binding"
        )

    if (
        replay_data.get("expected_projection_digest")
        != projection_digest
    ):
        raise BlotProjectionLockError(
            "replay expected projection digest mismatch"
        )

    if (
        replay_data.get("observed_projection_digest")
        != projection_digest
    ):
        raise BlotProjectionLockError(
            "replay observed projection digest mismatch"
        )

    requested_profile = _text(
        profile_id,
        "profile_id",
    )

    if (
        binding_data.get("profile_id")
        != requested_profile
    ):
        raise BlotProjectionLockError(
            "replay profile mismatch"
        )

    locked = (
        bool(verification_data.get("accepted"))
        and bool(acceptance_data.get("accepted"))
        and bool(replay_data.get("deterministic"))
    )

    if not locked:
        raise BlotProjectionLockError(
            "projection cannot be locked until verification, "
            "acceptance, and deterministic replay all pass"
        )

    result = ProjectionLock(
        source_digest=source_digest,
        construction_digest=construction_digest,
        execution_digest=execution_digest,
        projection_digest=projection_digest,
        verification_digest=verification_digest,
        acceptance_digest=acceptance_digest,
        replay_binding_digest=binding_digest,
        replay_result_digest=replay_result_digest,
        profile_id=requested_profile,
        locked=True,
        lineage=tuple(lineage),
        provenance=tuple(provenance),
    )

    result.normalized()

    return result


def manifest() -> dict[str, Any]:
    body = {
        "schema": schema,
        "name": name,
        "authority_effect": authority_effect,
        "mutation_effect": mutation_effect,
        "projection_only": projection_only,
        "requires": [
            "verification-accepted",
            "acceptance-accepted",
            "deterministic-replay",
            "digest-continuity",
            "profile-continuity",
        ],
        "creates_authority": False,
        "projection_is_authority": False,
        "mutates_construction": False,
        "mutates_projection": False,
        "lock_semantics": "derived-projection-acceptance-lock",
    }

    return {
        **body,
        "digest": _digest(body),
    }


__all__ = [
    "BlotProjectionLockError",
    "ProjectionLock",
    "authority_effect",
    "lock",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
