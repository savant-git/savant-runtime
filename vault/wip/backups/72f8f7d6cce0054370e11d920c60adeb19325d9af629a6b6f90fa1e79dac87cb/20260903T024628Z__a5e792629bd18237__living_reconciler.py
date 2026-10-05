#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


OWNER = "exile:niche"
SCHEMA = "savant://runtime/niche/living-reconciler/1.0.0"

ROOT = Path("/root/savant-runtime")
NICHE_DB = ROOT / "runtime" / "niche" / "tasks.sqlite3"

REPORT_ROOT = ROOT / "runtime" / "niche" / "reconciliation"
STATE_FILE = REPORT_ROOT / "state.json"
REPORT_FILE = REPORT_ROOT / "latest.json"

MASTERPLAN_CANDIDATES = (
    ROOT / "MASTERPLAN.md",
    ROOT / "masterplan.json",
    ROOT / "authority" / "task-graph" / "masterplan.json",
    ROOT / "canon-system" / "projections" / "living" / "masterplan.json",
    ROOT / "canon-system" / "projections" / "living" / "masterplan.md",
)

SCAN_SUFFIXES = frozenset(
    {
        ".py",
        ".sh",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".md",
        ".json",
        ".yaml",
        ".yml",
    }
)

EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "repair_backups",
        "relics",
        "archives",
        "exports",
        "imports",
    }
)

TODO_PATTERN = re.compile(
    r"\b("
    r"todo|fixme|xxx|hack|pending|not implemented|"
    r"not yet implemented|unimplemented|remaining work|"
    r"requires implementation"
    r")\b"
    r"[\s:=-]*(.{0,500})",
    re.IGNORECASE,
)

STATUS_WORDS = {
    "blocked",
    "deferred",
    "paused",
    "pending",
    "proposed",
    "accepted",
    "ready",
    "active",
    "unverified",
    "incomplete",
}

PRIORITIES = {
    "critical",
    "high",
    "normal",
    "low",
    "deferred",
}

TERMINAL = {
    "completed",
    "rejected",
    "superseded",
}

SYSTEM_MAP = {
    "niche": "planning",
    "palaver": "conversation",
    "envoy": "persona",
    "opus": "orchestration",
    "coda": "mutation",
    "notary": "evidence",
    "pact": "contracts",
    "modus": "composition",
    "underscore": "structure",
    "shatter": "decomposition",
    "filament": "projection",
    "lore": "canon",
    "urge": "evolution",
    "vault": "custody",
    "kindred": "relationships",
    "carbon": "simulation",
    "oriel": "simulation",
    "scyon": "substantiation",
    "splyce": "interface",
    "scrybe": "memory",
    "pryme": "authority",
    "cypher": "translation",
    "spyral": "migration",
    "thryce": "assurance",
    "dryve": "execution",
}

V324_TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "masterplan:v3.24:kindred:k0",
        "title": "Kindred K-0 reconciliation gate",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "critical",
        "status": "accepted",
        "horizon": "now",
        "purpose": (
            "Reconcile the September 2 broad Kindred expansion against "
            "the controlling family-relationship semantics before mutation."
        ),
        "dependencies": (),
        "completion_condition": (
            "Current direct relationship authority is confirmed; broad "
            "discipline expansion and separate kinship claims are classified "
            "without destroying evidence; stronger authority conflicts stop "
            "the tranche."
        ),
        "affected_instances": (
            "exile:kindred",
            "segue",
            "pryme",
        ),
        "risk": "high",
        "effort": "medium",
    },
    {
        "task_id": "masterplan:v3.24:kindred:k1",
        "title": "Kindred K-1 direct family core",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "critical",
        "status": "accepted",
        "horizon": "now",
        "purpose": (
            "Normalize direct parent-child, adoption, step, guardian, "
            "alliance and affinity semantics by reference to existing "
            "relationship authority."
        ),
        "dependencies": ("masterplan:v3.24:kindred:k0",),
        "completion_condition": (
            "Direct family primitives, reusable profiles, qualifiers, "
            "lineage, provenance, validity, state, history and boundary "
            "schemas are owner-correct and non-duplicative."
        ),
        "affected_instances": (
            "exile:kindred",
            "segue",
        ),
        "risk": "high",
        "effort": "medium",
    },
    {
        "task_id": "masterplan:v3.24:kindred:k2",
        "title": "Kindred K-2 algebra",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "critical",
        "status": "accepted",
        "horizon": "now",
        "purpose": (
            "Implement deterministic family-relationship derivation from "
            "direct admitted primitives."
        ),
        "dependencies": ("masterplan:v3.24:kindred:k1",),
        "completion_condition": (
            "Sibling, full/half sibling, grandparent/grandchild, "
            "aunt/uncle, niece/nephew, cousin, step and affinity/in-law "
            "derivations emit deterministic certificates and preserve "
            "unresolved qualification."
        ),
        "affected_instances": (
            "exile:kindred",
            "segue",
        ),
        "risk": "high",
        "effort": "large",
    },
    {
        "task_id": "masterplan:v3.24:kindred:k3",
        "title": "Kindred K-3 policy and propagation",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "high",
        "status": "accepted",
        "horizon": "next",
        "purpose": (
            "Implement purpose-specific descent, propagation, impeti, "
            "state/history and temporal replay without transferring authority."
        ),
        "dependencies": ("masterplan:v3.24:kindred:k2",),
        "completion_condition": (
            "Descent selection is separate from payload propagation; "
            "authority propagation routes through accepted authority/Pryme; "
            "temporal replay is deterministic."
        ),
        "affected_instances": (
            "exile:kindred",
            "living:pryme",
        ),
        "risk": "high",
        "effort": "large",
    },
    {
        "task_id": "masterplan:v3.24:kindred:k4",
        "title": "Kindred K-4 projection and assurance",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "high",
        "status": "accepted",
        "horizon": "next",
        "purpose": (
            "Add topology, semantic family-tree, historical, descent and "
            "alliance projections with focused assurance."
        ),
        "dependencies": ("masterplan:v3.24:kindred:k3",),
        "completion_condition": (
            "NetworkX-backed projections remain behind Kindred contracts; "
            "Graphviz is optional; deterministic explanation, derivation, "
            "temporal and rebuild-equivalence checks pass."
        ),
        "affected_instances": (
            "exile:kindred",
            "living:thryce",
        ),
        "risk": "medium",
        "effort": "medium",
    },
    {
        "task_id": "masterplan:v3.24:kindred:k5",
        "title": "Kindred K-5 compatibility retirement",
        "system": "kindred",
        "workstream": "kindred-reconciliation",
        "priority": "high",
        "status": "accepted",
        "horizon": "next",
        "purpose": (
            "Retire semantically incorrect Kindred/kinship compatibility "
            "surfaces only after dependent classification and migration."
        ),
        "dependencies": ("masterplan:v3.24:kindred:k4",),
        "completion_condition": (
            "Dependents are classified and migrated semantically; receipts "
            "and rollback exist where required; retirement occurs only after "
            "reverse-dependency proof."
        ),
        "affected_instances": (
            "exile:kindred",
            "living:spyral",
            "living:thryce",
        ),
        "risk": "high",
        "effort": "medium",
    },
    {
        "task_id": "masterplan:v3.24:palaver:ui-proof",
        "title": "Prove Palaver next-generation UI",
        "system": "palaver",
        "workstream": "palaver-ui",
        "priority": "high",
        "status": "proposed",
        "horizon": "next",
        "purpose": (
            "Establish explicit production build, startup and critical "
            "workflow evidence for the current next-generation Palaver UI."
        ),
        "dependencies": (),
        "completion_condition": (
            "Production build/startup and one critical workflow have explicit "
            "execution evidence without reopening the completed Palaver "
            "ownership migration."
        ),
        "affected_instances": (
            "exile:palaver",
            "living:splyce",
        ),
        "risk": "medium",
        "effort": "small",
    },
    {
        "task_id": "masterplan:v3.24:carbon:oriel-closure-proof",
        "title": "Prove Carbon/Oriel final closure",
        "system": "carbon",
        "workstream": "oriel",
        "priority": "high",
        "status": "proposed",
        "horizon": "next",
        "purpose": (
            "Establish explicit execution evidence for the Carbon/Oriel "
            "final closure operator."
        ),
        "dependencies": (),
        "completion_condition": (
            "The final closure operator produces explicit successful "
            "execution evidence while Carbon retains simulation ownership."
        ),
        "affected_instances": (
            "exile:carbon",
            "oriel",
        ),
        "risk": "medium",
        "effort": "small",
    },
    {
        "task_id": "masterplan:v3.24:opus:provider-universal",
        "title": "Resume provider-universal Opus integration",
        "system": "opus",
        "workstream": "provider-universal",
        "priority": "deferred",
        "status": "deferred",
        "horizon": "later",
        "purpose": (
            "Resume provider-universal Opus work only when valid external "
            "provider access exists or a concrete routing defect is proven."
        ),
        "dependencies": (),
        "completion_condition": (
            "A valid external-access prerequisite or concrete routing defect "
            "exists and the bounded provider integration is proven."
        ),
        "affected_instances": (
            "exile:opus",
        ),
        "risk": "low",
        "effort": "unknown",
    },
)


@dataclass(slots=True)
class Candidate:
    task_id: str
    title: str
    purpose: str
    system: str
    workstream: str
    priority: str = "normal"
    status: str = "proposed"
    horizon: str = "backlog"
    dependencies: tuple[str, ...] = ()
    affected_instances: tuple[str, ...] = ()
    completion_condition: str = ""
    risk: str = "unknown"
    effort: str = "unknown"
    confidence: float = 1.0
    source_kind: str = "discovery"
    source_path: str = ""
    source_line: int | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def projection(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "purpose": self.purpose,
            "system": self.system,
            "workstream": self.workstream,
            "priority": self.priority,
            "status": self.status,
            "horizon": self.horizon,
            "dependencies": list(self.dependencies),
            "affected_instances": list(self.affected_instances),
            "completion_condition": self.completion_condition,
            "risk": self.risk,
            "effort": self.effort,
            "confidence": self.confidence,
            "source_kind": self.source_kind,
            "source_path": self.source_path,
            "source_line": self.source_line,
            "evidence": self.evidence,
        }


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )
    temporary.write_text(data, encoding="utf-8")
    os.replace(temporary, path)


def slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9:_./-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "task"


def infer_system(path: Path | str) -> str:
    text = str(path).lower()

    for name in SYSTEM_MAP:
        if f"/{name}/" in f"/{text}/":
            return name

    if text.startswith("canon") or "/canon/" in text:
        return "canon"

    if text.startswith("authority") or "/authority/" in text:
        return "authority"

    if text.startswith("assurance") or "/assurance/" in text:
        return "assurance"

    if text.startswith("vault") or "/vault/" in text:
        return "vault"

    if text.startswith("runtime") or "/runtime/" in text:
        return "runtime"

    return "savant"


def infer_workstream(path: Path | str, system: str) -> str:
    text = str(path).lower()

    if system != "savant":
        return system

    if "/ui" in text or "/web" in text or "frontend" in text:
        return "interface"

    if "test" in text or "assurance" in text:
        return "assurance"

    if "migration" in text:
        return "migration"

    return "general"


def infer_priority(text: str) -> str:
    lower = text.lower()

    if any(
        token in lower
        for token in (
            "security",
            "corrupt",
            "data loss",
            "authority violation",
            "critical",
            "broken",
            "regression",
        )
    ):
        return "critical"

    if any(
        token in lower
        for token in (
            "blocker",
            "blocked",
            "required",
            "must",
            "failure",
            "unimplemented",
        )
    ):
        return "high"

    return "normal"


def infer_risk(text: str) -> str:
    lower = text.lower()

    if any(
        token in lower
        for token in (
            "authority",
            "persistent",
            "migration",
            "database",
            "schema",
            "security",
            "delete",
            "rollback",
        )
    ):
        return "high"

    if any(
        token in lower
        for token in (
            "integration",
            "compatibility",
            "shared",
            "interface",
        )
    ):
        return "medium"

    return "low"


def clean_title(text: str, fallback: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n:;#*-")

    if not text:
        return fallback

    if len(text) > 120:
        text = text[:117].rstrip() + "..."

    return text


def iter_source_files() -> Iterator[Path]:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            continue

        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue

        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue

        try:
            if path.stat().st_size > 4 * 1024 * 1024:
                continue
        except OSError:
            continue

        yield path


def discover_markers() -> list[Candidate]:
    candidates: list[Candidate] = []

    for path in iter_source_files():
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        relative = path.relative_to(ROOT)
        system = infer_system(relative)
        workstream = infer_workstream(relative, system)

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            match = TODO_PATTERN.search(line)

            if not match:
                continue

            marker = match.group(1).lower()
            remainder = clean_title(
                match.group(2),
                f"{marker} in {relative}",
            )

            identity = {
                "source_path": str(relative),
                "source_line": line_number,
                "marker": marker,
                "text": remainder,
            }

            task_id = (
                "discovery:"
                + slug(system)
                + ":"
                + digest(identity)[:20]
            )

            purpose = (
                f"Resolve explicit {marker.upper()} implementation evidence "
                f"in {relative}:{line_number}: {remainder}"
            )

            candidates.append(
                Candidate(
                    task_id=task_id,
                    title=remainder,
                    purpose=purpose,
                    system=system,
                    workstream=workstream,
                    priority=infer_priority(line),
                    status="proposed",
                    horizon="backlog",
                    completion_condition=(
                        "The referenced implementation marker is resolved "
                        "or explicitly rejected/superseded with evidence."
                    ),
                    risk=infer_risk(line),
                    effort="unknown",
                    confidence=0.55,
                    source_kind="implementation-marker",
                    source_path=str(relative),
                    source_line=line_number,
                    evidence=[
                        {
                            "marker": marker,
                            "line": line.strip()[:1000],
                        }
                    ],
                )
            )

    return candidates


def masterplan_candidates() -> list[Candidate]:
    result: list[Candidate] = []

    for record in V324_TASKS:
        result.append(
            Candidate(
                task_id=record["task_id"],
                title=record["title"],
                purpose=record["purpose"],
                system=record["system"],
                workstream=record["workstream"],
                priority=record["priority"],
                status=record["status"],
                horizon=record["horizon"],
                dependencies=tuple(
                    record["dependencies"]
                ),
                affected_instances=tuple(
                    record["affected_instances"]
                ),
                completion_condition=record[
                    "completion_condition"
                ],
                risk=record["risk"],
                effort=record["effort"],
                confidence=1.0,
                source_kind="masterplan-v3.24",
                source_path="CHATGPT_MASTERPLAN_v3.24.0.md",
                evidence=[
                    {
                        "authority_class": (
                            "strategic/reference projection"
                        ),
                        "version": "3.24.0",
                    }
                ],
            )
        )

    return result


def read_existing_tasks() -> dict[str, dict[str, Any]]:
    if not NICHE_DB.exists():
        return {}

    connection = sqlite3.connect(str(NICHE_DB))
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            "SELECT task_id, payload FROM tasks"
        ).fetchall()
    finally:
        connection.close()

    tasks: dict[str, dict[str, Any]] = {}

    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except Exception:
            continue

        tasks[str(row["task_id"])] = payload

    return tasks


def candidate_signature(candidate: Candidate) -> str:
    normalized = {
        "system": candidate.system,
        "workstream": candidate.workstream,
        "title": candidate.title.lower(),
        "purpose": candidate.purpose.lower(),
        "source_path": candidate.source_path,
    }
    return digest(normalized)


def deduplicate(
    candidates: Iterable[Candidate],
) -> list[Candidate]:
    chosen: dict[str, Candidate] = {}

    source_rank = {
        "masterplan-v3.24": 100,
        "authoritative-task-graph": 90,
        "living-masterplan": 80,
        "implementation-marker": 20,
        "discovery": 10,
    }

    for candidate in candidates:
        signature = candidate_signature(candidate)
        current = chosen.get(signature)

        if current is None:
            chosen[signature] = candidate
            continue

        if source_rank.get(
            candidate.source_kind,
            0,
        ) > source_rank.get(
            current.source_kind,
            0,
        ):
            candidate.evidence.extend(current.evidence)
            chosen[signature] = candidate
        else:
            current.evidence.extend(candidate.evidence)

    return sorted(
        chosen.values(),
        key=lambda item: (
            item.system,
            item.workstream,
            item.priority,
            item.task_id,
        ),
    )


def calculate_focus_score(
    candidate: Candidate,
    reverse_dependents: int,
) -> float:
    priority = {
        "critical": 100.0,
        "high": 70.0,
        "normal": 40.0,
        "low": 20.0,
        "deferred": 0.0,
    }.get(candidate.priority, 40.0)

    horizon = {
        "now": 25.0,
        "next": 15.0,
        "backlog": 5.0,
        "later": 0.0,
    }.get(candidate.horizon, 5.0)

    risk = {
        "high": 15.0,
        "medium": 8.0,
        "low": 2.0,
        "unknown": 0.0,
    }.get(candidate.risk, 0.0)

    return round(
        priority
        + horizon
        + risk
        + min(reverse_dependents * 5.0, 30.0)
        + candidate.confidence * 5.0,
        2,
    )


def build_projection(
    candidates: Sequence[Candidate],
    existing: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = {
        candidate.task_id: candidate
        for candidate in candidates
    }

    reverse: dict[str, set[str]] = defaultdict(set)

    for candidate in candidates:
        for dependency in candidate.dependencies:
            reverse[dependency].add(candidate.task_id)

    systems: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        system = systems.setdefault(
            candidate.system,
            {
                "total": 0,
                "by_priority": Counter(),
                "by_status": Counter(),
                "by_horizon": Counter(),
                "by_workstream": Counter(),
            },
        )

        system["total"] += 1
        system["by_priority"][candidate.priority] += 1
        system["by_status"][candidate.status] += 1
        system["by_horizon"][candidate.horizon] += 1
        system["by_workstream"][candidate.workstream] += 1

    tasks: list[dict[str, Any]] = []

    for candidate in candidates:
        projection = candidate.projection()
        projection["already_present"] = (
            candidate.task_id in existing
        )
        projection["reverse_dependents"] = sorted(
            reverse.get(candidate.task_id, set())
        )
        projection["focus_score"] = calculate_focus_score(
            candidate,
            len(projection["reverse_dependents"]),
        )
        tasks.append(projection)

    tasks.sort(
        key=lambda item: (
            item["status"] == "deferred",
            -item["focus_score"],
            item["system"],
            item["task_id"],
        )
    )

    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "authority_effect": "none",
        "generated_at": now(),
        "source_version": "3.24.0",
        "existing_task_count": len(existing),
        "candidate_count": len(tasks),
        "new_candidate_count": sum(
            not task["already_present"]
            for task in tasks
        ),
        "systems": {
            name: {
                "total": value["total"],
                "by_priority": dict(
                    value["by_priority"]
                ),
                "by_status": dict(
                    value["by_status"]
                ),
                "by_horizon": dict(
                    value["by_horizon"]
                ),
                "by_workstream": dict(
                    value["by_workstream"]
                ),
            }
            for name, value in sorted(systems.items())
        },
        "tasks": tasks,
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {}


def save_projection(projection: Mapping[str, Any]) -> None:
    atomic_write(
        REPORT_FILE,
        json.dumps(
            projection,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    )

    state = {
        "schema": SCHEMA,
        "generated_at": projection["generated_at"],
        "source_version": projection["source_version"],
        "projection_digest": digest(projection),
        "candidate_count": projection["candidate_count"],
        "new_candidate_count": projection[
            "new_candidate_count"
        ],
    }

    atomic_write(
        STATE_FILE,
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    )


def task_payload(candidate: Candidate) -> dict[str, Any]:
    status = candidate.status

    if status not in {
        "proposed",
        "accepted",
        "blocked",
        "deferred",
    }:
        status = "proposed"

    return {
        "task_id": candidate.task_id,
        "owner": OWNER,
        "jurisdiction": candidate.system,
        "purpose": candidate.purpose,
        "status": status,
        "priority": candidate.priority,
        "authority_basis": [
            "current user directive",
            (
                "CHATGPT_MASTERPLAN_v3.24.0.md"
                if candidate.source_kind == "masterplan-v3.24"
                else "implementation evidence"
            ),
        ],
        "provenance": {
            "source_kind": candidate.source_kind,
            "source_path": candidate.source_path,
            "source_line": candidate.source_line,
            "confidence": candidate.confidence,
            "reconciler_schema": SCHEMA,
        },
        "created_from": [
            candidate.source_kind,
            candidate.source_path,
        ],
        "dependencies": list(candidate.dependencies),
        "affected_instances": list(
            candidate.affected_instances
        ),
        "compatibility_obligations": [
            "preserve accepted authority",
            "preserve existing verified implementation",
            "preserve lineage and provenance",
            "preserve immutable history",
            "do not create duplicate authority",
        ],
        "completion_condition": (
            candidate.completion_condition
            or (
                "The bounded task is implemented or explicitly "
                "rejected/superseded with evidence."
            )
        ),
        "validation_budget": {
            "syntax_compile": True,
            "focused_functional_check": True,
            "integration_check": (
                candidate.risk in {"high", "medium"}
            ),
        },
        "blockers": [],
        "evidence_receipts": [],
        "supersedes": [],
        "decomposition_children": [],
        "implementation_references": (
            [candidate.source_path]
            if candidate.source_path
            else []
        ),
        "extension_slots": {
            "niche.taskboard": {
                "title": candidate.title,
                "system": candidate.system,
                "workstream": candidate.workstream,
                "horizon": candidate.horizon,
                "risk": candidate.risk,
                "effort": candidate.effort,
                "confidence": candidate.confidence,
                "labels": [
                    candidate.system,
                    candidate.workstream,
                    candidate.source_kind,
                ],
                "source_kind": candidate.source_kind,
                "source_path": candidate.source_path,
                "source_line": candidate.source_line,
                "discovery_evidence": candidate.evidence,
            }
        },
    }


def import_living_task():
    runtime_path = (
        ROOT
        / "ontology"
        / "obelisks"
        / "_template"
        / "segue"
        / "gates"
        / "_template"
        / "segue"
        / "innates"
        / "_template"
        / "segue"
        / "exiles"
        / "niche"
        / "runtime"
    )

    sys.path.insert(0, str(runtime_path))

    try:
        import living_task
    except Exception as exc:
        raise RuntimeError(
            f"unable to import living_task: {exc}"
        ) from exc

    return living_task


def instantiate_store(module: Any):
    candidates = (
        "LivingTaskStore",
        "TaskStore",
        "NicheTaskStore",
        "LivingTaskEngine",
    )

    for name in candidates:
        cls = getattr(module, name, None)

        if cls is None:
            continue

        for args in (
            (),
            (NICHE_DB,),
        ):
            try:
                return cls(*args)
            except TypeError:
                continue

    raise RuntimeError(
        "unable to identify living_task store class"
    )


def create_task(
    store: Any,
    payload: Mapping[str, Any],
) -> Any:
    method = getattr(store, "create", None)

    if method is None:
        raise RuntimeError(
            "living_task store has no create method"
        )

    try:
        return method(payload)
    except TypeError:
        return method(**payload)


def apply_candidates(
    candidates: Sequence[Candidate],
    existing: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    module = import_living_task()
    store = instantiate_store(module)

    created: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, Any]] = []

    known = set(existing)
    pending = list(candidates)

    while pending:
        progress = False

        for candidate in pending[:]:
            if candidate.task_id in known:
                skipped.append(candidate.task_id)
                pending.remove(candidate)
                progress = True
                continue

            unresolved = [
                dependency
                for dependency in candidate.dependencies
                if dependency not in known
            ]

            if unresolved:
                continue

            try:
                create_task(
                    store,
                    task_payload(candidate),
                )
            except Exception as exc:
                failed.append(
                    {
                        "task_id": candidate.task_id,
                        "error": str(exc),
                    }
                )
            else:
                created.append(candidate.task_id)
                known.add(candidate.task_id)

            pending.remove(candidate)
            progress = True

        if progress:
            continue

        for candidate in pending:
            failed.append(
                {
                    "task_id": candidate.task_id,
                    "error": "unresolved dependencies",
                    "dependencies": [
                        dependency
                        for dependency in candidate.dependencies
                        if dependency not in known
                    ],
                }
            )

        break

    return {
        "created": created,
        "created_count": len(created),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "failed": failed,
        "failed_count": len(failed),
    }


def reconcile(
    *,
    scan_markers: bool,
    apply: bool,
) -> dict[str, Any]:
    existing = read_existing_tasks()

    candidates: list[Candidate] = []
    candidates.extend(masterplan_candidates())

    if scan_markers:
        candidates.extend(discover_markers())

    candidates = deduplicate(candidates)

    projection = build_projection(
        candidates,
        existing,
    )

    previous = load_state()

    projection["previous_projection_digest"] = (
        previous.get("projection_digest")
    )

    projection["changed"] = (
        previous.get("projection_digest")
        != digest(projection)
    )

    if apply:
        projection["apply"] = apply_candidates(
            candidates,
            existing,
        )
    else:
        projection["apply"] = {
            "mode": "dry-run",
        }

    save_projection(projection)

    return projection


def summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": projection["schema"],
        "owner": projection["owner"],
        "authority_effect": projection[
            "authority_effect"
        ],
        "generated_at": projection["generated_at"],
        "source_version": projection[
            "source_version"
        ],
        "candidate_count": projection[
            "candidate_count"
        ],
        "new_candidate_count": projection[
            "new_candidate_count"
        ],
        "systems": projection["systems"],
        "apply": projection["apply"],
        "report": str(REPORT_FILE),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile living Savant work into Niche without "
            "manufacturing task authority."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="create missing tasks",
    )

    parser.add_argument(
        "--no-source-markers",
        action="store_true",
        help="skip TODO/FIXME implementation evidence discovery",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="print the complete projection",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    projection = reconcile(
        scan_markers=not args.no_source_markers,
        apply=args.apply,
    )

    output = (
        projection
        if args.full
        else summary(projection)
    )

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return (
        1
        if projection.get("apply", {}).get(
            "failed_count",
            0,
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
