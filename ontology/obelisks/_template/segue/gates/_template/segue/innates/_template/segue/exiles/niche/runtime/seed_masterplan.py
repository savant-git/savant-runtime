#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


BASE_URL = "http://127.0.0.1:1999"

AUTHORITY_BASIS = [
    "CHATGPT_MASTERPLAN_v3.23.0.md",
    "SAVANT_STRUCTURE_CURRENT_v3.23.0.md",
]

CREATED_FROM = [
    "masterplan:current-recommended-bounded-sequence",
]

VALIDATION_BUDGET = {
    "syntax_compile": True,
    "focused_functional_check": True,
    "integration_check": True,
}

COMMON_COMPATIBILITY = [
    "preserve existing verified implementation",
    "preserve authority ownership",
    "preserve lineage and provenance",
    "do not create duplicate authority",
    "do not resurrect superseded historical architecture",
]


TASKS: list[dict[str, Any]] = [
    {
        "task_id": "masterplan:lore-fluid-canon-scrybe-integration",
        "title": "Complete Lore / fluid canon / Scrybe integration",
        "priority": "critical",
        "purpose": (
            "Complete Lore, fluid-canon, and Scrybe integration without "
            "creating duplicate canonical or memory storage."
        ),
        "dependencies": [],
        "affected_instances": [
            "exile:lore",
            "living:scrybe",
            "fluid-canon",
        ],
        "completion_condition": (
            "Lore/fluid-canon/Scrybe integration is operational using singular "
            "authority-preserving storage, focused verification passes, and "
            "completion evidence is attached."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si1-si2",
        "title": "Implement Source Intelligence SI-1 and SI-2",
        "priority": "critical",
        "purpose": (
            "Implement source custody and identity plus bounded-memory "
            "streaming ingestion."
        ),
        "dependencies": [
            "masterplan:lore-fluid-canon-scrybe-integration",
        ],
        "affected_instances": [
            "source-intelligence",
            "vault",
        ],
        "completion_condition": (
            "Sources retain custody and stable identity and large inputs can "
            "be ingested with bounded memory without destructive normalization."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si3",
        "title": "Implement Source Intelligence SI-3",
        "priority": "high",
        "purpose": (
            "Implement deterministic semantic segmentation with exact "
            "source-boundary provenance."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si1-si2",
        ],
        "affected_instances": [
            "source-intelligence",
        ],
        "completion_condition": (
            "Segmentation is deterministic and every segment retains exact "
            "source-boundary provenance sufficient to recover its source."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si4-si5",
        "title": "Bind Scrybe and Pryme to SI-4 and SI-5",
        "priority": "high",
        "purpose": (
            "Bind Scrybe relevance/recall mechanics and Pryme authority "
            "interpretation to Source Intelligence."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si3",
        ],
        "affected_instances": [
            "living:scrybe",
            "living:pryme",
            "source-intelligence",
        ],
        "completion_condition": (
            "Source Intelligence relevance can feed Scrybe retrieval while "
            "authority interpretation remains Pryme-governed and cannot "
            "manufacture authority."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si6",
        "title": "Bind Thryce and Notary to SI-6",
        "priority": "high",
        "purpose": (
            "Bind Source Intelligence evidence assurance to Thryce and "
            "evidence admission to Notary."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si4-si5",
        ],
        "affected_instances": [
            "living:thryce",
            "exile:notary",
            "source-intelligence",
        ],
        "completion_condition": (
            "Evidence assurance and admission operate through their accepted "
            "owners without Source Intelligence becoming an evidence authority."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si7",
        "title": "Bind admitted SI records to Lore",
        "priority": "high",
        "purpose": (
            "Bind admitted Source Intelligence records into Lore/fluid canon "
            "without creating a competing canonical store."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si6",
        ],
        "affected_instances": [
            "exile:lore",
            "fluid-canon",
            "source-intelligence",
        ],
        "completion_condition": (
            "Admitted Source Intelligence records are consumable by Lore/fluid "
            "canon with authority, provenance, and admission lineage preserved."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si8",
        "title": "Implement SI-8 projections",
        "priority": "high",
        "purpose": (
            "Implement human, machine, and AI Source Intelligence projections "
            "through the accepted projection architecture."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si7",
        ],
        "affected_instances": [
            "exile:filament",
            "living:lythe",
            "source-intelligence",
        ],
        "completion_condition": (
            "Human, machine, and bounded AI views are reproducible projections "
            "of the same Source Intelligence primitives."
        ),
    },
    {
        "task_id": "masterplan:source-intelligence-si9",
        "title": "Implement SI-9 replay and recovery",
        "priority": "high",
        "purpose": (
            "Implement one deterministic replay/recovery path for the Source "
            "Intelligence pipeline."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si8",
        ],
        "affected_instances": [
            "source-intelligence",
            "vault",
        ],
        "completion_condition": (
            "At least one focused replay/recovery path reconstructs the "
            "required derived state from retained primitives and provenance."
        ),
    },
    {
        "task_id": "masterplan:urge-generalization",
        "title": "Generalize Urge iteration protocol",
        "priority": "normal",
        "purpose": (
            "Generalize Urge iteration only after Source Intelligence has a "
            "stable evidence and projection contract."
        ),
        "dependencies": [
            "masterplan:source-intelligence-si9",
        ],
        "affected_instances": [
            "exile:urge",
            "source-intelligence",
        ],
        "completion_condition": (
            "Urge can perform generalized candidate refinement while "
            "preserving immutable lineage, explicit deltas, and prohibition "
            "against automatic authority promotion."
        ),
    },
    {
        "task_id": "masterplan:cypher-integration",
        "title": "Continue Cypher integration",
        "priority": "normal",
        "purpose": (
            "Continue Cypher translation, normalization, serialization, "
            "adapter, and compatibility integration as a bounded task."
        ),
        "dependencies": [
            "masterplan:urge-generalization",
        ],
        "affected_instances": [
            "living:cypher",
        ],
        "completion_condition": (
            "Required Cypher integration works without transferring semantic "
            "ownership or authority through translation."
        ),
    },
    {
        "task_id": "masterplan:spyral-integration",
        "title": "Continue Spyral integration",
        "priority": "normal",
        "purpose": (
            "Continue Spyral migration and version-transition integration as "
            "a separate bounded task."
        ),
        "dependencies": [
            "masterplan:urge-generalization",
        ],
        "affected_instances": [
            "living:spyral",
        ],
        "completion_condition": (
            "Required migration/version transitions are modeled while durable "
            "mutation authorization remains outside Spyral."
        ),
    },
    {
        "task_id": "masterplan:splyce-integration",
        "title": "Continue Splyce integration",
        "priority": "normal",
        "purpose": (
            "Continue Splyce interface and interaction integration as a "
            "separate bounded task."
        ),
        "dependencies": [
            "masterplan:urge-generalization",
        ],
        "affected_instances": [
            "living:splyce",
        ],
        "completion_condition": (
            "Required interface projections operate without displayed state "
            "becoming independent authority."
        ),
    },
    {
        "task_id": "masterplan:dryve-integration",
        "title": "Continue Dryve integration",
        "priority": "normal",
        "purpose": (
            "Continue Dryve reusable execution-lifecycle integration without "
            "transferring task governance from Niche."
        ),
        "dependencies": [
            "masterplan:urge-generalization",
        ],
        "affected_instances": [
            "living:dryve",
            "exile:niche",
        ],
        "completion_condition": (
            "Required Dryve execution mechanics are reusable while Niche "
            "retains task identity, priority, dependencies, transitions, "
            "scheduling, and completion authority."
        ),
    },
    {
        "task_id": "masterplan:enterprise-completion",
        "title": "Reach current enterprise completion milestone",
        "priority": "normal",
        "purpose": (
            "Verify the current Masterplan enterprise completion conditions "
            "after the bounded implementation sequence is complete."
        ),
        "dependencies": [
            "masterplan:cypher-integration",
            "masterplan:spyral-integration",
            "masterplan:splyce-integration",
            "masterplan:dryve-integration",
        ],
        "affected_instances": [
            "savant",
        ],
        "completion_condition": (
            "Authority is explicit and queryable; canon remains singular and "
            "history-preserving; memory has no duplicate authority; source "
            "evidence preserves provenance; projections are reproducible; "
            "Vault supports custody/replay/recovery; durable mutations remain "
            "Coda-owned; and Masterplan remains Niche-owned."
        ),
    },
]


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            if not raw:
                return response.status, None
            return response.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"error": raw}
        return exc.code, data


def existing_ids() -> set[str]:
    status, data = request("GET", "/api/tasks")

    if status != 200:
        raise RuntimeError(
            f"unable to read existing tasks: http={status} response={data!r}"
        )

    if isinstance(data, dict):
        rows = data.get("tasks", data.get("items", []))
    else:
        rows = data

    if not isinstance(rows, list):
        raise RuntimeError("task API returned an unexpected task collection")

    result: set[str] = set()

    for row in rows:
        if isinstance(row, dict):
            task_id = row.get("task_id") or row.get("id")
            if task_id:
                result.add(str(task_id))

    return result


def payload_for(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "owner": "exile:niche",
        "jurisdiction": "masterplan",
        "purpose": task["purpose"],
        "status": "accepted",
        "priority": task["priority"],
        "authority_basis": AUTHORITY_BASIS,
        "provenance": {
            "source": "current-masterplan",
            "classification": "source-derived",
        },
        "created_from": CREATED_FROM,
        "dependencies": task["dependencies"],
        "affected_instances": task["affected_instances"],
        "compatibility_obligations": COMMON_COMPATIBILITY,
        "completion_condition": task["completion_condition"],
        "validation_budget": VALIDATION_BUDGET,
        "blockers": [],
        "evidence_receipts": [],
        "supersedes": [],
        "decomposition_children": [],
        "implementation_references": [],
        "extension_slots": {
            "niche.taskboard": {
                "title": task["title"],
                "labels": [
                    "masterplan",
                    "savant",
                ],
                "notes": (
                    "Seeded from the current bounded Masterplan sequence. "
                    "Do not mark complete without implementation evidence."
                ),
            }
        },
    }


def main() -> int:
    status, health = request("GET", "/api/health")

    if status != 200:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "niche taskboard is not reachable",
                    "http_status": status,
                    "response": health,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    known = existing_ids()

    created: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, Any]] = []

    pending = list(TASKS)

    while pending:
        progress = False

        for task in pending[:]:
            task_id = task["task_id"]

            if task_id in known:
                skipped.append(task_id)
                pending.remove(task)
                progress = True
                continue

            missing_dependencies = [
                dependency
                for dependency in task["dependencies"]
                if dependency not in known
            ]

            if missing_dependencies:
                continue

            status, response = request(
                "POST",
                "/api/tasks",
                payload_for(task),
            )

            if status in {200, 201}:
                created.append(task_id)
                known.add(task_id)
            else:
                failed.append(
                    {
                        "task_id": task_id,
                        "http_status": status,
                        "response": response,
                    }
                )

            pending.remove(task)
            progress = True

        if not progress:
            for task in pending:
                failed.append(
                    {
                        "task_id": task["task_id"],
                        "error": "unresolved dependency during seed",
                        "dependencies": task["dependencies"],
                    }
                )
            break

    result = {
        "ok": not failed,
        "created_count": len(created),
        "skipped_existing_count": len(skipped),
        "failed_count": len(failed),
        "created": created,
        "skipped_existing": skipped,
        "failed": failed,
    }

    print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
