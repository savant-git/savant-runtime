#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ENGINE="/root/savant-runtime/tools/refactor_engine"
mkdir -p "$ENGINE"

cat > "$ENGINE/simulate_refactor.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path("/root/savant-runtime")
PLAN = ROOT / "audit/refactor_engine/rewrite_plan.json"
OUT = ROOT / "audit/refactor_engine/simulation_report.json"

IGNORE = {".git", ".venv", "node_modules", "__pycache__", "site-packages", "exports"}

def ignore_dir(dirpath, names):
    return [n for n in names if n in IGNORE]

def apply_plan(work: Path, plan: dict) -> list[str]:
    log = []

    for item in plan.get("affected_files", []):
        rel = item["relpath"]
        path = work / rel

        if not path.exists():
            log.append(f"missing affected file: {rel}")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")

        for ch in item["changes"]:
            text = text.replace(ch["old"], ch["new"])

        path.write_text(text, encoding="utf-8")
        log.append(f"rewrote: {rel}")

    for move in plan.get("moves", []):
        src = Path(move["source"])
        dst = Path(move["target"])

        rel_src = src.relative_to(ROOT)
        rel_dst = dst.relative_to(ROOT)

        sim_src = work / rel_src
        sim_dst = work / rel_dst

        if not sim_src.exists():
            log.append(f"missing move source: {rel_src}")
            continue

        if sim_dst.exists():
            log.append(f"target exists: {rel_dst}")
            continue

        sim_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(sim_src), str(sim_dst))
        log.append(f"moved: {rel_src} -> {rel_dst}")

    return log

def validate(work: Path) -> list[dict]:
    failures = []

    for path in sorted(work.rglob("*.py")):
        if any(part in IGNORE for part in path.parts):
            continue
        proc = subprocess.run(
            ["python3", "-m", "py_compile", str(path)],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            failures.append({
                "kind": "python",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    for path in sorted(work.rglob("*.sh")):
        if any(part in IGNORE for part in path.parts):
            continue
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            failures.append({
                "kind": "shell",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    return failures

def main() -> int:
    if not PLAN.exists():
        raise SystemExit("[ERROR] Missing rewrite plan. Run dry run first.")

    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="savant_refactor_sim_") as td:
        work = Path(td) / "savant-runtime"
        shutil.copytree(ROOT, work, ignore=ignore_dir, symlinks=True)

        log = apply_plan(work, plan)
        failures = validate(work)

        report = {
            "moves": len(plan.get("moves", [])),
            "affected_files": len(plan.get("affected_files", [])),
            "simulation_log": log,
            "failures": failures,
            "status": "PASS" if not failures else "FAIL",
        }

        OUT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print("[OK] simulation complete")
    print("status:", report["status"])
    print("moves:", report["moves"])
    print("affected_files:", report["affected_files"])
    print("failures:", len(report["failures"]))
    print("report:", OUT)

    if failures:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ENGINE/simulate_refactor.py"

echo "[OK] simulator installed"
