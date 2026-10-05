#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/root/savant-runtime")
PLAN = ROOT / "audit/refactor_engine/rewrite_plan.json"

if not PLAN.exists():
    raise SystemExit("[ERROR] Missing rewrite_plan.json")

plan = json.loads(PLAN.read_text(encoding="utf-8"))

print("=== REFACTOR REWRITE PLAN ===")
print("moves:", len(plan.get("moves", [])))
print("affected_files:", len(plan.get("affected_files", [])))

print()
print("=== MOVES ===")
for move in plan.get("moves", []):
    print(f"{move['source']} -> {move['target']}")

print()
print("=== REQUIRED REWRITES ===")
for item in plan.get("affected_files", []):
    print()
    print(item["relpath"])
    for ch in item["changes"]:
        print(f"  {ch['count']}x {ch['old']} -> {ch['new']}")
