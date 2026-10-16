#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path("/root/savant-runtime")
CANON_SYSTEM = ROOT / "canon-system"
CANON_AUTHORITY = CANON_SYSTEM / "authority"
ACCEPTED_DECISIONS = ROOT / "authority" / "accepted-decisions"
TASK_GRAPH = ROOT / "authority" / "task-graph" / "masterplan.json"

SCHEMA = "savant://canon/authority-reconciliation/1.0.0"

AUTHORITY_CLASS_RANK = {
    "project-owner-directed": 1000,
    "accepted-decision": 900,
    "constitutional": 800,
    "canonical": 700,
    "verified-implementation": 600,
    "admitted-evidence": 500,
    "deterministic-projection": 400,
    "historical-implementation": 300,
    "historical-document": 200,
    "inference": 100,
    "speculation": 0,
}

STATE_RANK = {
    "immutable": 900,
    "axiomatic": 800,
    "canonical": 700,
    "accepted": 600,
    "verified": 500,
    "proposed": 400,
    "candidate": 300,
    "claim": 200,
    "observation": 100,
    "provisional": 50,
    "unknown": 0,
}


class AuthorityReconciliationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AuthoritySource:
    source_id: str
    source_kind: str
    source_path: str
    authority_class: str
    authority_state: str
    tier: int | None
    confidence: float | None
    accepted_at: str | None
    accepted_by: str | None
    digest: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def precedence(self) -> tuple[int, int, int, float]:
        class_rank = AUTHORITY_CLASS_RANK.get(
            self.authority_class,
            -1,
        )
        state_rank = STATE_RANK.get(
            self.authority_state,
            -1,
        )
        tier_rank = (
            -self.tier
            if self.tier is not None
            else -1_000_000
        )
        confidence = (
            self.confidence
            if self.confidence is not None
            else -1.0
        )
        return (
            class_rank,
            state_rank,
            tier_rank,
            confidence,
        )


@dataclass(frozen=True, slots=True)
class AuthorityConflict:
    conflict_id: str
    subject: str
    source_ids: tuple[str, ...]
    highest_precedence: tuple[int, int, int, float]
    resolution: str
    requires_authority: bool


@dataclass(frozen=True, slots=True)
class ReconciliationProjection:
    sources: tuple[AuthoritySource, ...]
    ordered_source_ids: tuple[str, ...]
    conflicts: tuple[AuthorityConflict, ...]
    unresolved_conflicts: tuple[str, ...]
    task_id: str = "SAV-P0-001"
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = SCHEMA
        payload["generated_at"] = datetime.now(UTC).isoformat()

        semantic = {
            "schema": SCHEMA,
            "task_id": self.task_id,
            "authority_effect": self.authority_effect,
            "sources": [
                asdict(source)
                for source in self.sources
            ],
            "ordered_source_ids": list(
                self.ordered_source_ids
            ),
            "conflicts": [
                asdict(conflict)
                for conflict in self.conflicts
            ],
            "unresolved_conflicts": list(
                self.unresolved_conflicts
            ),
        }

        payload["semantic_digest"] = sha256_json(
            semantic
        )
        return payload


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(
        canonical_json(value).encode("utf-8")
    )


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="strict",
    )


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(
        read_text(path)
    )


def load_json(path: Path) -> Any:
    return json.loads(
        read_text(path)
    )


def normalize_state(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).strip().lower()


def normalize_class(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).strip().lower()


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def optional_float(
    value: Any,
) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def authority_from_mapping(
    value: Any,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}

    authority = value.get("authority")

    if isinstance(authority, Mapping):
        return authority

    return {}


def source_from_yaml(
    path: Path,
) -> AuthoritySource:
    raw = load_yaml(path)

    if not isinstance(raw, Mapping):
        raw = {}

    authority = authority_from_mapping(raw)

    source_id = str(
        raw.get("id")
        or relative(path)
    )

    state = normalize_state(
        authority.get(
            "state",
            raw.get("status"),
        )
    )

    authority_class = normalize_class(
        authority.get(
            "authority_class"
        )
    )

    return AuthoritySource(
        source_id=source_id,
        source_kind=str(
            raw.get("kind")
            or "canon-authority"
        ),
        source_path=relative(path),
        authority_class=authority_class,
        authority_state=state,
        tier=optional_int(
            authority.get("tier")
        ),
        confidence=optional_float(
            authority.get("confidence")
        ),
        accepted_at=(
            None
            if authority.get("accepted_at") is None
            else str(
                authority.get("accepted_at")
            )
        ),
        accepted_by=(
            None
            if authority.get("accepted_by") is None
            else str(
                authority.get("accepted_by")
            )
        ),
        digest=sha256_bytes(
            read_text(path).encode("utf-8")
        ),
        metadata={
            "title": raw.get("title"),
            "status": raw.get("status"),
        },
    )


def accepted_decision_source(
    path: Path,
) -> AuthoritySource:
    text = read_text(path)

    return AuthoritySource(
        source_id=path.stem,
        source_kind="accepted-decision",
        source_path=relative(path),
        authority_class="accepted-decision",
        authority_state="accepted",
        tier=1,
        confidence=1.0,
        accepted_at=None,
        accepted_by="project-owner",
        digest=sha256_bytes(
            text.encode("utf-8")
        ),
        metadata={
            "format": "markdown",
            "content_interpretation": (
                "opaque accepted authority; "
                "content is preserved and not "
                "semantically rewritten by reconciler"
            ),
        },
    )


def task_graph_source(
    path: Path,
) -> AuthoritySource:
    raw = load_json(path)

    if not isinstance(raw, Mapping):
        raise AuthorityReconciliationError(
            "masterplan root must be an object"
        )

    authority = authority_from_mapping(raw)

    return AuthoritySource(
        source_id=str(
            raw.get("graph_id")
            or "savant.masterplan"
        ),
        source_kind="authoritative-task-graph",
        source_path=relative(path),
        authority_class=normalize_class(
            authority.get(
                "authority_class",
                "project-owner-directed",
            )
        ),
        authority_state=normalize_state(
            authority.get(
                "state",
                "authoritative",
            )
        ),
        tier=optional_int(
            authority.get("tier")
        ),
        confidence=optional_float(
            authority.get("confidence")
        ),
        accepted_at=(
            None
            if authority.get("accepted_at") is None
            else str(
                authority.get("accepted_at")
            )
        ),
        accepted_by=(
            None
            if authority.get("accepted_by") is None
            else str(
                authority.get("accepted_by")
            )
        ),
        digest=sha256_bytes(
            read_text(path).encode("utf-8")
        ),
        metadata={
            "schema_version": raw.get(
                "schema_version"
            ),
        },
    )


def iter_canon_authority_files() -> Iterable[Path]:
    if not CANON_AUTHORITY.exists():
        return

    for path in sorted(
        CANON_AUTHORITY.rglob("*")
    ):
        if (
            path.is_file()
            and path.suffix.lower()
            in {".yaml", ".yml"}
        ):
            yield path


def iter_accepted_decisions() -> Iterable[Path]:
    if not ACCEPTED_DECISIONS.exists():
        return

    for path in sorted(
        ACCEPTED_DECISIONS.iterdir()
    ):
        if (
            path.is_file()
            and path.suffix.lower()
            in {".md", ".markdown"}
        ):
            yield path


def collect_sources() -> tuple[AuthoritySource, ...]:
    sources: list[AuthoritySource] = []

    if TASK_GRAPH.is_file():
        sources.append(
            task_graph_source(TASK_GRAPH)
        )

    for path in iter_accepted_decisions():
        sources.append(
            accepted_decision_source(path)
        )

    for path in iter_canon_authority_files():
        sources.append(
            source_from_yaml(path)
        )

    unique: dict[
        tuple[str, str],
        AuthoritySource,
    ] = {}

    for source in sources:
        key = (
            source.source_path,
            source.digest,
        )
        unique[key] = source

    return tuple(
        sorted(
            unique.values(),
            key=lambda source: (
                source.source_path,
                source.source_id,
            ),
        )
    )


def precedence_key(
    source: AuthoritySource,
) -> tuple[
    int,
    int,
    int,
    float,
    str,
]:
    return (
        *source.precedence,
        source.source_id,
    )


def ordered_sources(
    sources: Sequence[AuthoritySource],
) -> tuple[AuthoritySource, ...]:
    return tuple(
        sorted(
            sources,
            key=precedence_key,
            reverse=True,
        )
    )


def detect_metadata_conflicts(
    sources: Sequence[AuthoritySource],
) -> tuple[AuthorityConflict, ...]:
    grouped: dict[
        str,
        list[AuthoritySource],
    ] = {}

    for source in sources:
        grouped.setdefault(
            source.source_id,
            [],
        ).append(source)

    conflicts: list[
        AuthorityConflict
    ] = []

    for subject, group in sorted(
        grouped.items()
    ):
        if len(group) < 2:
            continue

        digests = {
            source.digest
            for source in group
        }

        if len(digests) == 1:
            continue

        ranked = ordered_sources(group)

        highest = ranked[0].precedence

        tied = tuple(
            source
            for source in ranked
            if source.precedence == highest
        )

        if len(tied) == 1:
            resolution = (
                "higher_precedence_source_controls"
            )
            requires_authority = False
        else:
            resolution = (
                "unresolved_equal_precedence_conflict"
            )
            requires_authority = True

        conflict_id = (
            "authority-conflict-"
            + sha256_json({
                "subject": subject,
                "sources": [
                    {
                        "source_id": source.source_id,
                        "source_path": source.source_path,
                        "digest": source.digest,
                        "precedence": source.precedence,
                    }
                    for source in ranked
                ],
            })[:24]
        )

        conflicts.append(
            AuthorityConflict(
                conflict_id=conflict_id,
                subject=subject,
                source_ids=tuple(
                    source.source_id
                    for source in ranked
                ),
                highest_precedence=highest,
                resolution=resolution,
                requires_authority=requires_authority,
            )
        )

    return tuple(conflicts)


def reconcile() -> ReconciliationProjection:
    sources = collect_sources()
    ordered = ordered_sources(sources)
    conflicts = detect_metadata_conflicts(
        sources
    )

    unresolved = tuple(
        conflict.conflict_id
        for conflict in conflicts
        if conflict.requires_authority
    )

    return ReconciliationProjection(
        sources=sources,
        ordered_source_ids=tuple(
            source.source_id
            for source in ordered
        ),
        conflicts=conflicts,
        unresolved_conflicts=unresolved,
    )


def summary(
    projection: ReconciliationProjection,
) -> dict[str, Any]:
    ordered = ordered_sources(
        projection.sources
    )

    return {
        "schema": SCHEMA,
        "task_id": projection.task_id,
        "source_count": len(
            projection.sources
        ),
        "conflict_count": len(
            projection.conflicts
        ),
        "unresolved_conflict_count": len(
            projection.unresolved_conflicts
        ),
        "highest_authority": (
            None
            if not ordered
            else {
                "source_id": ordered[0].source_id,
                "source_path": ordered[0].source_path,
                "authority_class": (
                    ordered[0].authority_class
                ),
                "authority_state": (
                    ordered[0].authority_state
                ),
                "tier": ordered[0].tier,
                "precedence": (
                    ordered[0].precedence
                ),
            }
        ),
        "accepted_decisions": sum(
            1
            for source in projection.sources
            if source.source_kind
            == "accepted-decision"
        ),
        "provisional_sources": sum(
            1
            for source in projection.sources
            if source.authority_state
            == "provisional"
        ),
        "authority_effect": "none",
        "safe_to_project": (
            not projection.unresolved_conflicts
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="authority_reconciliation",
        description=(
            "deterministically reconcile declared "
            "savant canon authority metadata"
        ),
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="emit complete reconciliation projection",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()
    projection = reconcile()

    payload = (
        projection.to_dict()
        if args.full
        else summary(projection)
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        2
        if projection.unresolved_conflicts
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
