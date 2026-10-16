#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


owner = "exile:niche"
schema = "savant://runtime/niche/completion-engine/1.0.0"

root = Path("/root/savant-runtime")
niche_runtime = (
    root
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

living_task_path = niche_runtime / "living_task.py"
db_path = root / "runtime" / "niche" / "tasks.sqlite3"

projection_root = root / "runtime" / "niche" / "projections"
completion_json = projection_root / "completion.json"
masterplan_json = root / "masterplan.json"
masterplan_md = root / "MASTERPLAN.md"

scan_suffixes = {
    ".py",
    ".sh",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".md",
}

excluded_parts = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "repair_backups",
    "backups",
    "snapshots",
    "archive",
    "archives",
    "relics",
}

marker_pattern = re.compile(
    r"\b("
    r"TODO|FIXME|XXX|"
    r"NOT IMPLEMENTED|"
    r"NOT YET IMPLEMENTED|"
    r"UNIMPLEMENTED"
    r")\b"
    r"[\s:=-]*(.*)",
    re.IGNORECASE,
)

system_names = (
    "carbon",
    "cataxis",
    "coda",
    "envoy",
    "filament",
    "graffiti",
    "kindred",
    "lore",
    "mobius",
    "modus",
    "niche",
    "notary",
    "opus",
    "pact",
    "palaver",
    "shatter",
    "underscore",
    "urge",
    "zero",
    "scrybe",
    "scyon",
    "cypher",
    "spyral",
    "thryce",
    "dryve",
    "pryme",
)

masterplan_domains = {
    "authority",
    "canon",
    "ontology",
    "rubrics",
    "context",
    "runtime",
    "vault",
    "assurance",
    "evolution",
}


def utc_now() -> str:
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


def slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(
        r"[^a-z0-9:_./-]+",
        "-",
        value,
    )
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "task"


def atomic_write(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    temporary.write_text(
        text,
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def load_living_task():
    spec = importlib.util.spec_from_file_location(
        "savant_niche_living_task",
        living_task_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"unable to load {living_task_path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


living_task = load_living_task()
LivingTaskEngine = living_task.LivingTaskEngine


@dataclass(slots=True)
class Node:
    task_id: str
    title: str
    purpose: str
    system: str
    workstream: str
    domain: str
    priority: str
    status: str
    horizon: str
    depth: int
    parent_id: str | None
    dependencies: tuple[str, ...] = ()
    affected_instances: tuple[str, ...] = ()
    completion_condition: str = ""
    risk: str = "medium"
    effort: str = "unknown"
    authority_basis: tuple[str, ...] = ()
    source_kind: str = "accepted-plan"
    source_path: str = ""
    implementation_references: tuple[str, ...] = ()
    children: list[str] = field(
        default_factory=list
    )


def node(
    *,
    task_id: str,
    title: str,
    purpose: str,
    system: str,
    workstream: str,
    domain: str = "runtime",
    priority: str = "normal",
    status: str = "accepted",
    horizon: str = "next",
    depth: int = 1,
    parent_id: str | None = None,
    dependencies: Sequence[str] = (),
    affected_instances: Sequence[str] = (),
    completion_condition: str,
    risk: str = "medium",
    effort: str = "unknown",
    authority_basis: Sequence[str] = (
        "current user directive",
        "CHATGPT_MASTERPLAN_v3.24.0.md",
        "current verified implementation evidence",
    ),
    source_kind: str = "accepted-plan",
    source_path: str = (
        "CHATGPT_MASTERPLAN_v3.24.0.md"
    ),
    implementation_references: Sequence[str] = (),
) -> Node:
    if domain not in masterplan_domains:
        domain = "runtime"

    return Node(
        task_id=task_id,
        title=title,
        purpose=purpose,
        system=system,
        workstream=workstream,
        domain=domain,
        priority=priority,
        status=status,
        horizon=horizon,
        depth=depth,
        parent_id=parent_id,
        dependencies=tuple(dependencies),
        affected_instances=tuple(
            affected_instances
        ),
        completion_condition=(
            completion_condition
        ),
        risk=risk,
        effort=effort,
        authority_basis=tuple(
            authority_basis
        ),
        source_kind=source_kind,
        source_path=source_path,
        implementation_references=tuple(
            implementation_references
        ),
    )


def accepted_objectives() -> list[dict[str, Any]]:
    return [
        {
            "id": "niche-completion",
            "title": "Complete living Niche task intelligence",
            "system": "niche",
            "workstream": "completion-intelligence",
            "domain": "runtime",
            "priority": "critical",
            "horizon": "now",
            "risk": "high",
            "purpose": (
                "Make Niche the authoritative living task "
                "intelligence layer for completing Savant."
            ),
            "completion": (
                "Niche contains the accepted remaining Savant "
                "work, supports depth 1-4 decomposition, "
                "preserves immutable history and evidence, "
                "and deterministically projects Masterplan."
            ),
            "tranches": [
                (
                    "authoritative-task-reconciliation",
                    "Reconcile existing task authority",
                    [
                        "preserve existing task primitives",
                        "classify accepted versus proposed work",
                        "reconcile duplicate task identities",
                        "preserve task history and receipts",
                    ],
                ),
                (
                    "completion-discovery",
                    "Implement living completion discovery",
                    [
                        "ingest current implementation evidence",
                        "discover explicit unfinished markers",
                        "classify system and workstream",
                        "detect stale completion assumptions",
                    ],
                ),
                (
                    "decomposition",
                    "Implement depth-aware decomposition",
                    [
                        "project strategic objectives",
                        "project implementation tranches",
                        "project bounded engineering tasks",
                        "project executable actions",
                    ],
                ),
                (
                    "taskboard-integration",
                    "Complete Taskboard integration",
                    [
                        "expose decomposition depth control",
                        "expose system and workstream facets",
                        "expose dependency and evidence views",
                        "expose deterministic next-work selection",
                    ],
                ),
            ],
        },
        {
            "id": "living-projection-fabric",
            "title": "Complete living documentation projection fabric",
            "system": "savant",
            "workstream": "living-projections",
            "domain": "context",
            "priority": "critical",
            "horizon": "now",
            "risk": "medium",
            "purpose": (
                "Make Masterplan, Structure and hierarchical "
                "README surfaces deterministic living projections."
            ),
            "completion": (
                "Masterplan, Structure and README projections "
                "regenerate deterministically from authoritative "
                "primitives without becoming duplicate authority."
            ),
            "tranches": [
                (
                    "masterplan-projection",
                    "Generate living Masterplan",
                    [
                        "project Niche task graph",
                        "group tasks by Masterplan domain",
                        "project ready blocked and completed state",
                        "publish deterministic markdown and json",
                    ],
                ),
                (
                    "structure-projection",
                    "Generate living Structure",
                    [
                        "consume living structural state",
                        "preserve authority distinctions",
                        "project current system organization",
                        "publish deterministic current structure",
                    ],
                ),
                (
                    "readme-projection",
                    "Generate recursive README edifice",
                    [
                        "project local element substance",
                        "compose child-first recursive substance",
                        "apply Modus masks where authorized",
                        "publish machine and human twins",
                    ],
                ),
            ],
        },
        {
            "id": "kindred-reconciliation",
            "title": "Complete corrected Kindred methodology",
            "system": "kindred",
            "workstream": "family-relationship-methodology",
            "domain": "ontology",
            "priority": "critical",
            "horizon": "now",
            "risk": "high",
            "purpose": (
                "Restore Kindred to the accepted generalized "
                "family-relationship methodology and retire "
                "semantic drift safely."
            ),
            "completion": (
                "Direct family primitives, Kindred Algebra, "
                "policies, temporal history, projections and "
                "compatibility retirement are implemented with "
                "focused proof."
            ),
            "tranches": [
                (
                    "k0",
                    "K-0 reconciliation gate",
                    [
                        "classify eighteen-discipline expansion",
                        "classify legacy kindred surfaces",
                        "confirm direct Segue relationship authority",
                        "stop on stronger authority conflict",
                    ],
                ),
                (
                    "k1",
                    "K-1 direct family core",
                    [
                        "normalize parent-child primitives",
                        "normalize alliance and affinity primitives",
                        "normalize adoption step and guardian profiles",
                        "preserve lineage validity state and history",
                    ],
                ),
                (
                    "k2",
                    "K-2 Kindred Algebra",
                    [
                        "derive sibling and full-half qualification",
                        "derive grandparent and grandchild",
                        "derive aunt uncle niece nephew",
                        "derive cousins step and affinity relations",
                    ],
                ),
                (
                    "k3",
                    "K-3 policy and propagation",
                    [
                        "implement descent policies",
                        "separate descent from propagation",
                        "route authority through Pryme",
                        "implement temporal relationship replay",
                    ],
                ),
                (
                    "k4",
                    "K-4 projection and assurance",
                    [
                        "integrate NetworkX behind Kindred contracts",
                        "project semantic family topology",
                        "implement explain and derivation certificates",
                        "prove deterministic rebuild equivalence",
                    ],
                ),
                (
                    "k5",
                    "K-5 compatibility retirement",
                    [
                        "inventory disputed dependents",
                        "classify active compatibility historical dead",
                        "migrate consumers semantically",
                        "retire only after reverse-dependency proof",
                    ],
                ),
            ],
        },
        {
            "id": "living-governance-proof",
            "title": "Close second-generation Living Governance proof",
            "system": "savant",
            "workstream": "living-governance",
            "domain": "authority",
            "priority": "high",
            "horizon": "next",
            "risk": "high",
            "purpose": (
                "Convert September implementation presence into "
                "bounded operational evidence."
            ),
            "completion": (
                "Typed policy composition, temporal behavior, "
                "arbitration, lifecycle, packets and Coda receipt "
                "integration have focused operational proof."
            ),
            "tranches": [
                (
                    "operator-proof",
                    "Prove governance operators",
                    [
                        "compile current governance surfaces",
                        "run focused policy pipeline case",
                        "run temporal replay case",
                        "verify consumer packet and receipt",
                    ],
                ),
            ],
        },
        {
            "id": "palaver-ui-proof",
            "title": "Close Palaver next-generation UI proof",
            "system": "palaver",
            "workstream": "webui-nextgen",
            "domain": "runtime",
            "priority": "high",
            "horizon": "next",
            "risk": "medium",
            "purpose": (
                "Establish production build, startup and critical "
                "workflow evidence for the existing next-generation UI."
            ),
            "completion": (
                "The active App.tsx path builds, starts and completes "
                "one critical Palaver workflow."
            ),
            "tranches": [
                (
                    "production-proof",
                    "Prove production UI",
                    [
                        "build active webui-nextgen entry path",
                        "start Palaver with built frontend",
                        "exercise one critical workflow",
                        "record focused evidence",
                    ],
                ),
            ],
        },
        {
            "id": "carbon-oriel-proof",
            "title": "Close Carbon/Oriel operational proof",
            "system": "carbon",
            "workstream": "oriel",
            "domain": "runtime",
            "priority": "high",
            "horizon": "next",
            "risk": "medium",
            "purpose": (
                "Establish explicit live closure evidence for "
                "the implemented Carbon/Oriel subsystem."
            ),
            "completion": (
                "The final Carbon/Oriel closure operator succeeds "
                "with focused evidence while simulation remains "
                "non-canonical."
            ),
            "tranches": [
                (
                    "closure-proof",
                    "Prove Oriel closure",
                    [
                        "compile closure surfaces",
                        "run focused Oriel integration",
                        "run final closure operator",
                        "record closure evidence",
                    ],
                ),
            ],
        },
        {
            "id": "extr-closure",
            "title": "Reconcile and close extr enterprise",
            "system": "savant",
            "workstream": "extr",
            "domain": "runtime",
            "priority": "normal",
            "horizon": "next",
            "risk": "medium",
            "purpose": (
                "Re-evaluate the previously frozen incomplete extr "
                "workstream now that the September 3 sdump contains "
                "tools/extr-enterprise/runtime/boundary.py."
            ),
            "completion": (
                "The former blocker is reconciled and extr either "
                "passes its focused enterprise status path or retains "
                "an explicit current blocker."
            ),
            "tranches": [
                (
                    "reconciliation",
                    "Reconcile extr current state",
                    [
                        "confirm current boundary implementation",
                        "run focused extr status path",
                        "classify any remaining blocker",
                        "record completion or blocker evidence",
                    ],
                ),
            ],
        },
        {
            "id": "opus-provider-universal",
            "title": "Resume provider-universal Opus when actionable",
            "system": "opus",
            "workstream": "provider-universal",
            "domain": "runtime",
            "priority": "deferred",
            "horizon": "later",
            "risk": "low",
            "status": "deferred",
            "purpose": (
                "Resume provider-universal work only when valid "
                "external access exists or a concrete routing defect "
                "is demonstrated."
            ),
            "completion": (
                "An actionable provider prerequisite exists and the "
                "bounded provider continuation is proven."
            ),
            "tranches": [
                (
                    "external-prerequisite",
                    "Resolve actionable provider prerequisite",
                    [
                        "obtain valid provider access or defect evidence",
                        "classify external versus internal failure",
                        "resume only the affected integration",
                        "record provider integration evidence",
                    ],
                ),
            ],
        },
    ]


def build_edifice(
    selected_depth: int,
) -> list[Node]:
    nodes: list[Node] = []

    for objective in accepted_objectives():
        objective_id = (
            "completion:"
            + objective["id"]
        )

        tranche_ids = [
            f"{objective_id}:{slug(item[0])}"
            for item in objective["tranches"]
        ]

        objective_node = node(
            task_id=objective_id,
            title=objective["title"],
            purpose=objective["purpose"],
            system=objective["system"],
            workstream=objective["workstream"],
            domain=objective["domain"],
            priority=objective["priority"],
            status=objective.get(
                "status",
                "accepted",
            ),
            horizon=objective["horizon"],
            depth=1,
            parent_id=None,
            affected_instances=(
                objective["system"],
            ),
            completion_condition=(
                objective["completion"]
            ),
            risk=objective["risk"],
            effort="large",
        )

        if selected_depth >= 2:
            objective_node.children.extend(
                tranche_ids
            )

        nodes.append(objective_node)

        if selected_depth < 2:
            continue

        for tranche_key, tranche_title, actions in (
            objective["tranches"]
        ):
            tranche_id = (
                f"{objective_id}:"
                f"{slug(tranche_key)}"
            )

            task_ids = [
                f"{tranche_id}:task-{index + 1}"
                for index in range(len(actions))
            ]

            tranche_node = node(
                task_id=tranche_id,
                title=tranche_title,
                purpose=(
                    f"{tranche_title} for "
                    f"{objective['title']}."
                ),
                system=objective["system"],
                workstream=objective[
                    "workstream"
                ],
                domain=objective["domain"],
                priority=objective["priority"],
                status=objective.get(
                    "status",
                    "accepted",
                ),
                horizon=objective["horizon"],
                depth=2,
                parent_id=objective_id,
                completion_condition=(
                    f"{tranche_title} is complete "
                    "with required focused evidence."
                ),
                risk=objective["risk"],
                effort="medium",
            )

            if selected_depth >= 3:
                tranche_node.children.extend(
                    task_ids
                )

            nodes.append(tranche_node)

            if selected_depth < 3:
                continue

            previous_task_id: str | None = None

            for index, action in enumerate(
                actions,
                start=1,
            ):
                task_id = (
                    f"{tranche_id}:task-{index}"
                )

                action_ids = [
                    f"{task_id}:action-1",
                ]

                dependencies = (
                    (previous_task_id,)
                    if previous_task_id
                    else ()
                )

                task_node = node(
                    task_id=task_id,
                    title=action,
                    purpose=action,
                    system=objective["system"],
                    workstream=objective[
                        "workstream"
                    ],
                    domain=objective["domain"],
                    priority=objective[
                        "priority"
                    ],
                    status=objective.get(
                        "status",
                        "accepted",
                    ),
                    horizon=objective["horizon"],
                    depth=3,
                    parent_id=tranche_id,
                    dependencies=dependencies,
                    completion_condition=(
                        f"{action} is implemented "
                        "or explicitly resolved with "
                        "evidence."
                    ),
                    risk=objective["risk"],
                    effort="small",
                )

                if selected_depth >= 4:
                    task_node.children.extend(
                        action_ids
                    )

                nodes.append(task_node)

                if selected_depth >= 4:
                    nodes.append(
                        node(
                            task_id=action_ids[0],
                            title=(
                                "Execute: "
                                + action
                            ),
                            purpose=(
                                "Perform the bounded "
                                "implementation or "
                                "verification action: "
                                + action
                            ),
                            system=objective[
                                "system"
                            ],
                            workstream=objective[
                                "workstream"
                            ],
                            domain=objective[
                                "domain"
                            ],
                            priority=objective[
                                "priority"
                            ],
                            status=objective.get(
                                "status",
                                "accepted",
                            ),
                            horizon=objective[
                                "horizon"
                            ],
                            depth=4,
                            parent_id=task_id,
                            completion_condition=(
                                "The executable action "
                                "has an evidence receipt "
                                "or explicit blocker."
                            ),
                            risk=objective["risk"],
                            effort="small",
                        )
                    )

                previous_task_id = task_id

    return nodes


def infer_system(
    relative: Path,
) -> str:
    lowered = "/".join(
        part.lower()
        for part in relative.parts
    )

    for name in system_names:
        if (
            f"/{name}/" in f"/{lowered}/"
            or lowered.startswith(
                f"{name}/"
            )
        ):
            return name

    if lowered.startswith("vault/"):
        return "vault"

    if lowered.startswith("assurance/"):
        return "assurance"

    if lowered.startswith("canon"):
        return "canon"

    return "savant"


def iter_source_files() -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative = path.relative_to(
                root
            )
        except ValueError:
            continue

        if any(
            part in excluded_parts
            for part in relative.parts
        ):
            continue

        if (
            path.suffix.lower()
            not in scan_suffixes
        ):
            continue

        try:
            if path.stat().st_size > 4_000_000:
                continue
        except OSError:
            continue

        yield path


def discover_explicit_markers() -> list[Node]:
    result: list[Node] = []

    for path in iter_source_files():
        relative = path.relative_to(root)

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            continue

        system = infer_system(relative)

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            match = marker_pattern.search(
                line
            )

            if not match:
                continue

            marker = match.group(1).lower()
            detail = re.sub(
                r"\s+",
                " ",
                match.group(2),
            ).strip(" :#-*")

            if not detail:
                detail = (
                    f"{marker} marker in "
                    f"{relative}"
                )

            identity = {
                "path": str(relative),
                "line": line_number,
                "marker": marker,
                "detail": detail,
            }

            task_id = (
                "discovery:"
                + slug(system)
                + ":"
                + digest(identity)[:20]
            )

            result.append(
                node(
                    task_id=task_id,
                    title=detail[:140],
                    purpose=(
                        "Resolve explicit unfinished "
                        f"implementation marker at "
                        f"{relative}:{line_number}."
                    ),
                    system=system,
                    workstream=(
                        "implementation-discovery"
                    ),
                    domain="runtime",
                    priority="normal",
                    status="proposed",
                    horizon="backlog",
                    depth=3,
                    parent_id=None,
                    completion_condition=(
                        "The marker is implemented, "
                        "rejected, superseded, or "
                        "classified as non-task evidence."
                    ),
                    risk="low",
                    effort="unknown",
                    authority_basis=(
                        "current implementation evidence",
                    ),
                    source_kind=(
                        "implementation-marker"
                    ),
                    source_path=str(relative),
                    implementation_references=(
                        f"{relative}:{line_number}",
                    ),
                )
            )

    return result


def existing_tasks(
    engine: LivingTaskEngine,
) -> dict[str, Any]:
    return {
        task.task_id: task
        for task in engine.tasks()
    }


def task_extension(
    item: Node,
) -> dict[str, Any]:
    return {
        "masterplan_domain": item.domain,
        "niche.taskboard": {
            "title": item.title,
            "system": item.system,
            "workstream": item.workstream,
            "horizon": item.horizon,
            "risk": item.risk,
            "effort": item.effort,
            "depth": item.depth,
            "parent_id": item.parent_id,
            "source_kind": item.source_kind,
            "source_path": item.source_path,
            "labels": [
                item.system,
                item.workstream,
                item.domain,
                f"depth-{item.depth}",
                item.horizon,
                item.risk,
            ],
        },
        "completion": {
            "schema": schema,
            "depth": item.depth,
            "parent_id": item.parent_id,
        },
    }


def create_missing(
    engine: LivingTaskEngine,
    nodes: Sequence[Node],
) -> dict[str, Any]:
    known = existing_tasks(engine)

    created: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, str]] = []

    for item in sorted(
        nodes,
        key=lambda value: (
            value.depth,
            value.task_id,
        ),
    ):
        if item.task_id in known:
            skipped.append(item.task_id)
            continue

        try:
            task = engine.create(
                task_id=item.task_id,
                purpose=item.purpose,
                owner=owner,
                jurisdiction=item.system,
                authority_basis=(
                    item.authority_basis
                ),
                completion_condition=(
                    item.completion_condition
                ),
                status=item.status,
                priority=item.priority,
                provenance={
                    "schema": schema,
                    "source_kind": (
                        item.source_kind
                    ),
                    "source_path": (
                        item.source_path
                    ),
                    "generated_at": utc_now(),
                },
                created_from=(
                    "completion-engine",
                    item.source_kind,
                ),
                dependencies=(
                    item.dependencies
                ),
                affected_instances=(
                    item.affected_instances
                    or (item.system,)
                ),
                compatibility_obligations=(
                    "preserve accepted authority",
                    "preserve verified implementation",
                    "preserve lineage and provenance",
                    "preserve immutable task history",
                    "do not create duplicate authority",
                ),
                validation_budget={
                    "syntax_or_compile": True,
                    "focused_functional": 1,
                    "integration_or_startup": (
                        1
                        if item.risk
                        in {"high", "medium"}
                        else 0
                    ),
                },
                decomposition_children=(
                    item.children
                ),
                implementation_references=(
                    item.implementation_references
                ),
                extension_slots=(
                    task_extension(item)
                ),
            )

            known[task.task_id] = task
            created.append(task.task_id)

        except Exception as exc:
            failed.append(
                {
                    "task_id": item.task_id,
                    "error": str(exc),
                }
            )

    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "created": created,
        "skipped": skipped,
        "failed": failed,
    }


def taskboard_metadata(
    task: Any,
) -> Mapping[str, Any]:
    slots = task.extension_slots or {}
    value = slots.get(
        "niche.taskboard",
        {},
    )

    if isinstance(value, Mapping):
        return value

    return {}


def completion_projection(
    engine: LivingTaskEngine,
    selected_depth: int,
) -> dict[str, Any]:
    tasks = list(engine.tasks())

    by_system: Counter[str] = Counter()
    by_priority: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_horizon: Counter[str] = Counter()
    by_depth: Counter[str] = Counter()
    by_workstream: Counter[str] = Counter()

    projected: list[dict[str, Any]] = []

    for task in tasks:
        meta = taskboard_metadata(task)

        depth = int(
            meta.get("depth", 1)
        )

        if depth > selected_depth:
            continue

        system = str(
            meta.get(
                "system",
                task.jurisdiction,
            )
        )

        workstream = str(
            meta.get(
                "workstream",
                system,
            )
        )

        horizon = str(
            meta.get(
                "horizon",
                "backlog",
            )
        )

        by_system[system] += 1
        by_priority[task.priority] += 1
        by_status[task.status] += 1
        by_horizon[horizon] += 1
        by_depth[str(depth)] += 1
        by_workstream[workstream] += 1

        projected.append(
            {
                "task_id": task.task_id,
                "title": meta.get(
                    "title",
                    task.purpose,
                ),
                "system": system,
                "workstream": workstream,
                "status": task.status,
                "priority": task.priority,
                "horizon": horizon,
                "depth": depth,
                "parent_id": meta.get(
                    "parent_id"
                ),
                "dependencies": list(
                    task.dependencies
                ),
                "children": list(
                    task.decomposition_children
                ),
                "blockers": list(
                    task.blockers
                ),
                "completion_condition": (
                    task.completion_condition
                ),
                "evidence_receipts": list(
                    task.evidence_receipts
                ),
            }
        )

    projected.sort(
        key=lambda item: (
            {
                "critical": 0,
                "high": 1,
                "normal": 2,
                "low": 3,
                "deferred": 4,
            }.get(
                item["priority"],
                9,
            ),
            item["depth"],
            item["system"],
            item["task_id"],
        )
    )

    graph = engine.project()

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect": "none",
        "generated_at": utc_now(),
        "selected_depth": selected_depth,
        "task_count": len(projected),
        "by_system": dict(
            sorted(by_system.items())
        ),
        "by_workstream": dict(
            sorted(by_workstream.items())
        ),
        "by_priority": dict(
            sorted(by_priority.items())
        ),
        "by_status": dict(
            sorted(by_status.items())
        ),
        "by_horizon": dict(
            sorted(by_horizon.items())
        ),
        "by_depth": dict(
            sorted(by_depth.items())
        ),
        "graph_digest": graph["digest"],
        "tasks": projected,
        "rebuildable": True,
    }


def render_masterplan(
    engine: LivingTaskEngine,
    completion: Mapping[str, Any],
) -> str:
    masterplan = engine.masterplan()

    lines = [
        "# savant living masterplan",
        "",
        f"generated: {completion['generated_at']}",
        "",
        "status: deterministic projection from "
        "niche-owned task primitives",
        "",
        "authority effect: none",
        "",
        "task owner: exile:niche",
        "",
        f"selected decomposition depth: "
        f"{completion['selected_depth']}",
        "",
        f"task graph digest: "
        f"`{masterplan['task_graph_digest']}`",
        "",
        "## completion summary",
        "",
    ]

    for status, count in sorted(
        completion["by_status"].items()
    ):
        lines.append(
            f"- {status}: {count}"
        )

    lines.extend(
        [
            "",
            "## systems",
            "",
        ]
    )

    for system, count in sorted(
        completion["by_system"].items()
    ):
        lines.append(
            f"- {system}: {count}"
        )

    lines.extend(
        [
            "",
            "## masterplan domains",
            "",
        ]
    )

    for domain, task_ids in (
        masterplan["domains"].items()
    ):
        lines.append(
            f"### {domain}"
        )
        lines.append("")

        visible = {
            task["task_id"]: task
            for task in completion["tasks"]
        }

        found = False

        for task_id in task_ids:
            task = visible.get(task_id)

            if task is None:
                continue

            found = True

            lines.append(
                "- "
                f"[{task['status']}] "
                f"[{task['priority']}] "
                f"{task['title']} "
                f"(`{task_id}`)"
            )

        if not found:
            lines.append("- none")

        lines.append("")

    lines.extend(
        [
            "## ready",
            "",
        ]
    )

    if masterplan["ready"]:
        for task_id in masterplan["ready"]:
            lines.append(
                f"- `{task_id}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## blocked",
            "",
        ]
    )

    if masterplan["blocked"]:
        for task_id in masterplan["blocked"]:
            lines.append(
                f"- `{task_id}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## projection law",
            "",
            "This file is rebuildable.",
            "",
            "Task substance exists in Niche.",
            "",
            "This Masterplan does not create "
            "independent task authority.",
            "",
        ]
    )

    return "\n".join(lines)


def write_projections(
    engine: LivingTaskEngine,
    selected_depth: int,
) -> dict[str, str]:
    completion = completion_projection(
        engine,
        selected_depth,
    )

    atomic_write(
        completion_json,
        json.dumps(
            completion,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    )

    masterplan = engine.masterplan()

    atomic_write(
        masterplan_json,
        json.dumps(
            masterplan,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    )

    atomic_write(
        masterplan_md,
        render_masterplan(
            engine,
            completion,
        ),
    )

    return {
        "completion": str(
            completion_json
        ),
        "masterplan_json": str(
            masterplan_json
        ),
        "masterplan_md": str(
            masterplan_md
        ),
    }


def health(
    engine: LivingTaskEngine,
) -> dict[str, Any]:
    result = engine.health()

    return {
        "schema": schema,
        "owner": owner,
        "niche": result,
        "database": str(db_path),
        "healthy": bool(
            result.get(
                "healthy",
                result.get("valid", True),
            )
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Living Savant completion intelligence "
            "owned by Niche."
        )
    )

    parser.add_argument(
        "command",
        choices=(
            "preview",
            "apply",
            "project",
            "health",
        ),
    )

    parser.add_argument(
        "--depth",
        type=int,
        choices=(1, 2, 3, 4),
        default=3,
    )

    parser.add_argument(
        "--discover",
        action="store_true",
        help=(
            "include explicit TODO/FIXME/"
            "unimplemented markers as proposed tasks"
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    engine = LivingTaskEngine(
        db_path
    )

    if args.command == "health":
        print(
            json.dumps(
                health(engine),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    nodes = build_edifice(
        args.depth
    )

    if args.discover:
        nodes.extend(
            discover_explicit_markers()
        )

    if args.command == "preview":
        counts = Counter(
            item.status
            for item in nodes
        )

        systems = Counter(
            item.system
            for item in nodes
        )

        print(
            json.dumps(
                {
                    "schema": schema,
                    "owner": owner,
                    "authority_effect": "none",
                    "depth": args.depth,
                    "candidate_count": len(
                        nodes
                    ),
                    "status_counts": dict(
                        counts
                    ),
                    "system_counts": dict(
                        systems
                    ),
                    "discovery_enabled": (
                        args.discover
                    ),
                    "existing_task_count": len(
                        engine.tasks()
                    ),
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "apply":
        result = create_missing(
            engine,
            nodes,
        )

        projections = write_projections(
            engine,
            args.depth,
        )

        output = {
            "schema": schema,
            "owner": owner,
            "depth": args.depth,
            "apply": result,
            "projections": projections,
            "health": health(engine),
        }

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
            if result["failed_count"]
            else 0
        )

    if args.command == "project":
        projections = write_projections(
            engine,
            args.depth,
        )

        print(
            json.dumps(
                {
                    "schema": schema,
                    "owner": owner,
                    "depth": args.depth,
                    "projections": projections,
                    "health": health(engine),
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )

        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
