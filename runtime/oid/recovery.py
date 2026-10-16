from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.oid.store import OidStore, StoredArtifact


SCHEMA = "savant://oid/recovery/1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class RecoveryIssue:
    artifact_ref: str
    issue: str
    recoverable: bool

    def projection(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "artifact_ref": self.artifact_ref,
            "issue": self.issue,
            "recoverable": self.recoverable,
            "automatic_mutation": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    frame_ref: str
    frame_refs: tuple[str, ...]
    issues: tuple[RecoveryIssue, ...]
    latest_valid_ref: str | None
    latest_valid_generation: int | None
    lineage_valid: bool

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "frame_ref": self.frame_ref,
            "frame_refs": list(
                self.frame_refs
            ),
            "issues": [
                issue.projection()
                for issue in self.issues
            ],
            "latest_valid_ref": (
                self.latest_valid_ref
            ),
            "latest_valid_generation": (
                self.latest_valid_generation
            ),
            "lineage_valid": self.lineage_valid,
            "issue_count": len(self.issues),
            "destructive_repair": False,
            "historical_state_preserved": True,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def _valid_frame_artifact(
    artifact: StoredArtifact,
) -> bool:
    if artifact.artifact_type != "frame":
        return False

    payload = artifact.payload

    digest = payload.get("digest")

    if not isinstance(digest, str):
        return False

    body = dict(payload)
    body.pop("digest", None)

    return digest == _digest(body)


def inspect_recovery(
    store: OidStore,
    frame_ref: str,
) -> RecoveryReport:
    history = store.frame_history(
        frame_ref
    )

    issues: list[RecoveryIssue] = []
    valid: list[StoredArtifact] = []

    expected_generation = 0

    for artifact in history:
        if artifact.generation != expected_generation:
            issues.append(
                RecoveryIssue(
                    artifact_ref=artifact.artifact_id,
                    issue=(
                        "non_contiguous_generation"
                    ),
                    recoverable=True,
                )
            )

        expected_generation += 1

        if not _valid_frame_artifact(
            artifact
        ):
            issues.append(
                RecoveryIssue(
                    artifact_ref=artifact.artifact_id,
                    issue="digest_mismatch",
                    recoverable=False,
                )
            )
            continue

        valid.append(artifact)

    lineage_valid = store.validate_lineage(
        frame_ref
    )

    if not lineage_valid:
        issues.append(
            RecoveryIssue(
                artifact_ref=frame_ref,
                issue="lineage_invalid",
                recoverable=True,
            )
        )

    latest = (
        valid[-1]
        if valid
        else None
    )

    return RecoveryReport(
        frame_ref=frame_ref,
        frame_refs=tuple(
            artifact.artifact_id
            for artifact in history
        ),
        issues=tuple(issues),
        latest_valid_ref=(
            latest.artifact_id
            if latest is not None
            else None
        ),
        latest_valid_generation=(
            latest.generation
            if latest is not None
            else None
        ),
        lineage_valid=lineage_valid,
    )


def recovery_projection(
    store: OidStore,
    frame_ref: str,
) -> Mapping[str, Any]:
    return inspect_recovery(
        store,
        frame_ref,
    ).projection()
