#!/usr/bin/env python3
"""Savant transactional dry-run simulator.

Reconstructs an sdump projection into an isolated staging tree, verifies every
source digest, simulates proposed relocations without touching the live tree,
runs structural and language validation, evaluates dependency and compatibility
impact, and emits a conservative SAFE / UNSAFE / INDETERMINATE verdict.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

VERSION = "1.0.0"
SAFE = "safe"
UNSAFE = "unsafe"
INDETERMINATE = "indeterminate"
VERDICTS = {SAFE, UNSAFE, INDETERMINATE}
TEXT_ENCODINGS = {"utf-8", "utf8", "ascii"}
CRITICAL_EXTENSIONS = {".py", ".sh", ".json", ".jsonl", ".yaml", ".yml", ".toml"}
PUBLIC_PATH_PATTERNS = (
    re.compile(r"(^|/)bin/"),
    re.compile(r"(^|/)commands?/"),
    re.compile(r"(^|/)contracts?/"),
    re.compile(r"(^|/)schemas?/"),
    re.compile(r"(^|/)authority/"),
    re.compile(r"(^|/)canon/"),
)


class DryRunError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class Entry:
    path: str
    content_id: str
    source_sha256: str
    rendered_sha256: str
    language: str
    category: str
    content: str
    mode: str = "unknown"


@dataclasses.dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: str
    severity: str
    message: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(slots=True)
class Simulation:
    dump_path: Path
    proposal_path: Path
    output_dir: Path
    entries: list[Entry]
    manifest: dict[str, Any]
    proposal: list[dict[str, Any]]
    gates: list[GateResult]
    actions: list[dict[str, Any]]
    baseline_digest: str
    staged_digest: str
    verdict: str
    verdict_reasons: list[str]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def tree_digest(records: Iterable[tuple[str, str]]) -> str:
    payload = "\n".join(f"{path}\0{digest}" for path, digest in sorted(records))
    return sha256_bytes(payload.encode("utf-8"))


def parse_dump(path: Path) -> tuple[dict[str, Any], list[Entry]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "manifest\n----------------------------------------------------------------------------\n"
    start = text.find(marker)
    if start < 0:
        raise DryRunError("sdump manifest marker not found")
    start += len(marker)
    end = text.find("\n\n============================================================================", start)
    if end < 0:
        raise DryRunError("sdump manifest terminator not found")
    manifest = json.loads(text[start:end])

    header = re.compile(
        r"={76}\ncontent instance\n={76}\n"
        r"path: (?P<path>[^\n]+)\n"
        r"category: (?P<category>[^\n]+)\n"
        r"language: (?P<language>[^\n]+)\n"
        r"source_size: (?P<size>[^\n]+)\n"
        r"source_sha256: (?P<source_sha256>[^\n]+)\n"
        r"rendered_sha256: (?P<rendered_sha256>[^\n]+)\n"
        r"content_id: (?P<content_id>[^\n]+)\n"
        r"encoding: (?P<encoding>[^\n]+)\n"
        r"redactions: (?P<redactions>[^\n]+)\n"
        r"-{76}\ncontent\n-{76}\n",
        re.MULTILINE,
    )
    end_marker = "\n\n============================================================================\nend content instance"
    parsed: list[Entry] = []
    contents: dict[str, str] = {}
    for match in header.finditer(text, end):
        body_start = match.end()
        body_end = text.find(end_marker, body_start)
        if body_end < 0:
            body_end = len(text)
        content = text[body_start:body_end]
        if content.startswith("\n"):
            content = content[1:]
        if content and not content.endswith("\n"):
            content += "\n"
        item = Entry(
            path=match.group("path"),
            content_id=match.group("content_id"),
            source_sha256=match.group("source_sha256"),
            rendered_sha256=match.group("rendered_sha256"),
            language=match.group("language"),
            category=match.group("category"),
            content=content,
        )
        parsed.append(item)
        contents[item.content_id] = content

    present = {item.path for item in parsed}
    for record in manifest.get("files", []):
        if not record.get("included") or record.get("path") in present:
            continue
        content_id = record.get("content_id", "")
        parsed.append(
            Entry(
                path=record["path"],
                content_id=content_id,
                source_sha256=record.get("source_sha256", ""),
                rendered_sha256=record.get("rendered_sha256", record.get("source_sha256", "")),
                language=record.get("language", "unknown"),
                category=record.get("category", "unknown"),
                content=contents.get(content_id, ""),
                mode=record.get("mode", "unknown"),
            )
        )
    parsed.sort(key=lambda item: item.path)
    return manifest, parsed


def safe_relative(path: str) -> PurePosixPath:
    value = PurePosixPath(path)
    if value.is_absolute() or ".." in value.parts or not value.parts:
        raise DryRunError(f"unsafe relative path: {path!r}")
    return value


def load_proposal(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise DryRunError("migration proposal root must be a JSON list")
    return [item for item in value if isinstance(item, dict)]


def reconstruct(entries: list[Entry], root: Path) -> list[GateResult]:
    gates: list[GateResult] = []
    mismatches: list[str] = []
    missing_content: list[str] = []
    for entry in entries:
        rel = safe_relative(entry.path)
        target = root.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = entry.content.encode("utf-8")
        actual = sha256_bytes(raw)
        expected_rendered = entry.rendered_sha256 or entry.source_sha256
        if expected_rendered and actual != expected_rendered:
            mismatches.append(f"{entry.path}: expected_rendered={expected_rendered} actual={actual}")
        if not entry.content and entry.source_sha256 not in {"", sha256_bytes(b"")}:
            missing_content.append(entry.path)
        target.write_bytes(raw)
        if entry.mode and entry.mode not in {"unknown", ""}:
            try:
                os.chmod(target, int(entry.mode, 8))
            except (ValueError, OSError):
                pass
    if mismatches:
        gates.append(GateResult("source-integrity", "indeterminate", "high", f"{len(mismatches)} rendered entries could not be byte-reconstructed exactly from the textual dump", tuple(mismatches[:50])))
    else:
        gates.append(GateResult("source-integrity", "pass", "critical", "all reconstructed file hashes match the dump"))
    if missing_content:
        gates.append(GateResult("content-completeness", "indeterminate", "high", f"{len(missing_content)} included manifest entries lack embedded content", tuple(missing_content[:50])))
    else:
        gates.append(GateResult("content-completeness", "pass", "high", "all included entries have reconstructable content"))
    return gates


def inventory(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(root).as_posix()
            result[rel] = sha256_bytes(path.read_bytes())
    return result


def is_public_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in PUBLIC_PATH_PATTERNS)


def simulate_moves(root: Path, proposal: list[dict[str, Any]], entries_by_path: dict[str, Entry]) -> tuple[list[dict[str, Any]], list[GateResult]]:
    actions: list[dict[str, Any]] = []
    gates: list[GateResult] = []
    source_seen: set[str] = set()
    destination_seen: dict[str, str] = {}
    failures: list[str] = []
    uncertain: list[str] = []
    compatibility_missing: list[str] = []

    for index, item in enumerate(proposal):
        source = str(item.get("source", "")).strip()
        destination = str(item.get("proposed_destination", "")).strip()
        confidence = float(item.get("confidence", 0.0) or 0.0)
        dependents = [str(v) for v in item.get("dependents", []) if isinstance(v, str)]
        compatibility_required = bool(item.get("compatibility_required")) or bool(dependents) or is_public_path(source)
        record = {
            "index": index,
            "source": source,
            "destination": destination,
            "confidence": confidence,
            "dependents": dependents,
            "compatibility_required": compatibility_required,
            "status": "pending",
            "reasons": [],
        }
        actions.append(record)
        try:
            src_rel = safe_relative(source)
            dst_rel = safe_relative(destination)
        except DryRunError as error:
            record["status"] = "blocked"
            record["reasons"].append(str(error))
            failures.append(f"proposal[{index}]: {error}")
            continue
        src = root.joinpath(*src_rel.parts)
        dst = root.joinpath(*dst_rel.parts)
        if source in source_seen:
            record["status"] = "blocked"
            record["reasons"].append("duplicate source action")
            failures.append(f"duplicate source action: {source}")
            continue
        source_seen.add(source)
        if not src.is_file():
            record["status"] = "blocked"
            record["reasons"].append("source missing from reconstructed baseline")
            failures.append(f"missing source: {source}")
            continue
        actual = sha256_bytes(src.read_bytes())
        expected = str(item.get("precondition_sha256", ""))
        authoritative_source_hash = entries_by_path.get(source).source_sha256 if source in entries_by_path else ""
        if expected and authoritative_source_hash and authoritative_source_hash != expected:
            record["status"] = "blocked"
            record["reasons"].append("precondition hash mismatch")
            failures.append(f"hash mismatch: {source}")
            continue
        prior = destination_seen.get(destination)
        if prior and prior != source:
            record["status"] = "blocked"
            record["reasons"].append(f"destination collision with {prior}")
            failures.append(f"destination collision: {destination}")
            continue
        destination_seen[destination] = source
        if dst.exists() and sha256_bytes(dst.read_bytes()) != actual:
            record["status"] = "blocked"
            record["reasons"].append("destination already exists with different content")
            failures.append(f"occupied destination: {destination}")
            continue
        if confidence < 0.90:
            record["reasons"].append("classification confidence below 0.90")
            uncertain.append(f"{source}: confidence={confidence:.2f}")
        if compatibility_required and not item.get("compatibility_path"):
            compatibility_missing.append(source)
            record["reasons"].append("compatibility path required but not specified")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        # Keep the source in staging. This models a compatibility-preserving copy,
        # never a destructive move. Retirement requires a later, separately gated run.
        record["status"] = "simulated"

    if failures:
        gates.append(GateResult("proposal-applicability", "fail", "critical", f"{len(failures)} proposal actions cannot be simulated", tuple(failures[:100])))
    else:
        gates.append(GateResult("proposal-applicability", "pass", "critical", "all proposal actions can be simulated as non-destructive copies"))
    if uncertain:
        gates.append(GateResult("ownership-confidence", "indeterminate", "high", f"{len(uncertain)} actions have confidence below 0.90", tuple(uncertain[:100])))
    else:
        gates.append(GateResult("ownership-confidence", "pass", "high", "all actions meet the 0.90 ownership-confidence threshold"))
    if compatibility_missing:
        gates.append(GateResult("compatibility-contracts", "indeterminate", "critical", f"{len(compatibility_missing)} actions require explicit compatibility paths", tuple(compatibility_missing[:100])))
    else:
        gates.append(GateResult("compatibility-contracts", "pass", "critical", "all affected public/dependent paths have explicit compatibility disposition"))
    return actions, gates


def validate_python(root: Path) -> GateResult:
    failures: list[str] = []
    for path in root.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except SyntaxError as error:
            failures.append(f"{path.relative_to(root)}:{error.lineno}:{error.offset}: {error.msg}")
    return GateResult("python-syntax", "fail" if failures else "pass", "critical", f"{len(failures)} Python syntax failures" if failures else "all Python files parse", tuple(failures[:100]))


def validate_json(root: Path) -> GateResult:
    failures: list[str] = []
    for pattern in ("*.json", "*.jsonl"):
        for path in root.rglob(pattern):
            try:
                if path.suffix == ".jsonl":
                    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if line.strip():
                            json.loads(line)
                else:
                    json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception as error:
                failures.append(f"{path.relative_to(root)}: {error}")
    return GateResult("json-validity", "fail" if failures else "pass", "critical", f"{len(failures)} JSON/JSONL failures" if failures else "all JSON and JSONL files parse", tuple(failures[:100]))


def validate_shell(root: Path) -> GateResult:
    failures: list[str] = []
    shell = shutil.which("bash")
    if not shell:
        return GateResult("shell-syntax", "indeterminate", "high", "bash is unavailable")
    for path in root.rglob("*.sh"):
        result = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True, check=False)
        if result.returncode:
            failures.append(f"{path.relative_to(root)}: {(result.stderr or result.stdout).strip()}")
    return GateResult("shell-syntax", "fail" if failures else "pass", "critical", f"{len(failures)} shell syntax failures" if failures else "all shell files pass bash -n", tuple(failures[:100]))


def validate_references(root: Path, proposal: list[dict[str, Any]]) -> GateResult:
    missing: list[str] = []
    for item in proposal:
        source = str(item.get("source", ""))
        for dependent in item.get("dependents", []):
            if not isinstance(dependent, str):
                continue
            dep_path = root.joinpath(*safe_relative(dependent).parts)
            if not dep_path.exists():
                missing.append(f"dependent absent: {dependent} (for {source})")
    return GateResult("dependent-presence", "indeterminate" if missing else "pass", "high", f"{len(missing)} declared dependents are absent from the snapshot" if missing else "all declared dependents are present", tuple(missing[:100]))


def evaluate(gates: list[GateResult], manifest: dict[str, Any], proposal: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    failed = [gate for gate in gates if gate.status == "fail"]
    unknown = [gate for gate in gates if gate.status == "indeterminate"]
    excluded = int(manifest.get("summary", {}).get("excluded", manifest.get("excluded_count", 0)) or 0)
    oversized = int(manifest.get("summary", {}).get("oversized", manifest.get("oversized_count", 0)) or 0)
    if failed:
        reasons.extend(f"failed gate: {gate.gate} — {gate.message}" for gate in failed)
        return UNSAFE, reasons
    if not proposal:
        reasons.append("migration proposal is empty; no change set was evaluated")
        return INDETERMINATE, reasons
    if unknown:
        reasons.extend(f"indeterminate gate: {gate.gate} — {gate.message}" for gate in unknown)
    if excluded or oversized:
        reasons.append(f"snapshot is incomplete: excluded={excluded}, oversized={oversized}")
    if unknown or excluded or oversized:
        return INDETERMINATE, reasons
    reasons.append("every required dry-run gate passed against a complete snapshot")
    return SAFE, reasons


def write_outputs(sim: Simulation) -> None:
    sim.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "$schema": "savant://dry-run/result/1.0.0",
        "version": VERSION,
        "generated_at": now(),
        "dump": str(sim.dump_path),
        "proposal": str(sim.proposal_path),
        "mutation_performed": False,
        "baseline_digest": sim.baseline_digest,
        "staged_digest": sim.staged_digest,
        "entry_count": len(sim.entries),
        "proposal_count": len(sim.proposal),
        "verdict": sim.verdict,
        "verdict_reasons": sim.verdict_reasons,
        "gates": [gate.as_dict() for gate in sim.gates],
        "actions": sim.actions,
    }
    payload["result_digest"] = sha256_bytes(stable_json(payload).encode("utf-8"))
    (sim.output_dir / "dry-run-result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Savant Dry-Run Safety Evaluation",
        "",
        f"- Verdict: **{sim.verdict.upper()}**",
        f"- Entries: {len(sim.entries)}",
        f"- Proposed actions: {len(sim.proposal)}",
        "- Mutation performed: **no**",
        f"- Baseline digest: `{sim.baseline_digest}`",
        f"- Staged digest: `{sim.staged_digest}`",
        "",
        "## Verdict reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in sim.verdict_reasons)
    lines.extend(["", "## Gates", "", "| Gate | Status | Severity | Result |", "|---|---:|---:|---|"])
    for gate in sim.gates:
        lines.append(f"| `{gate.gate}` | {gate.status} | {gate.severity} | {gate.message.replace('|', '/')} |")
    lines.extend(["", "## Interpretation", ""])
    if sim.verdict == SAFE:
        lines.append("The proposed changes passed every modeled gate. This authorizes only a separately approved transactional execution against a hash-identical live baseline.")
    elif sim.verdict == UNSAFE:
        lines.append("The proposed changes must not be applied. One or more modeled gates prove breakage or invalid preconditions.")
    else:
        lines.append("The proposed changes are not proven safe. Additional live evidence, authority resolution, compatibility contracts, or missing source content is required.")
    (sim.output_dir / "DRY_RUN_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(dump_path: Path, proposal_path: Path, output_dir: Path, keep_staging: bool = False) -> Simulation:
    manifest, entries = parse_dump(dump_path)
    proposal = load_proposal(proposal_path)
    staging_parent = output_dir / "staging" if keep_staging else None
    temp_ctx = tempfile.TemporaryDirectory(prefix="savant-dry-run-") if not keep_staging else None
    root = staging_parent if staging_parent is not None else Path(temp_ctx.name)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    gates = reconstruct(entries, root)
    baseline_inventory = inventory(root)
    baseline_digest = tree_digest(baseline_inventory.items())
    actions, move_gates = simulate_moves(root, proposal, {entry.path: entry for entry in entries})
    gates.extend(move_gates)
    gates.extend((validate_python(root), validate_json(root), validate_shell(root), validate_references(root, proposal)))
    staged_inventory = inventory(root)
    staged_digest = tree_digest(staged_inventory.items())
    verdict, reasons = evaluate(gates, manifest, proposal)
    sim = Simulation(dump_path, proposal_path, output_dir, entries, manifest, proposal, gates, actions, baseline_digest, staged_digest, verdict, reasons)
    write_outputs(sim)
    if temp_ctx is not None:
        temp_ctx.cleanup()
    return sim


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", required=True, type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keep-staging", action="store_true")
    args = parser.parse_args(argv)
    sim = run(args.dump, args.proposal, args.output, args.keep_staging)
    print(json.dumps({"status": "completed", "verdict": sim.verdict, "output": str(sim.output_dir), "mutation_performed": False}, indent=2, sort_keys=True))
    return {SAFE: 0, INDETERMINATE: 2, UNSAFE: 3}[sim.verdict]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DryRunError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "error", "error": str(error), "mutation_performed": False}, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(4)
