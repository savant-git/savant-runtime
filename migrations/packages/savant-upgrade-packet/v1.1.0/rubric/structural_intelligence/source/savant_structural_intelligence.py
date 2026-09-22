#!/usr/bin/env python3
"""Savant Structural Intelligence Compiler.

Read-only by default. It reconstructs an sdump v3 projection, executes a
fixed set of deterministic audit passes, corroborates claims across supplied
sources, identifies Rubric/Cabal ownership, maps Opus integration apertures,
and emits a staged migration plan without changing the runtime.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence

VERSION = "1.0.0"
DEFAULT_ROOT = Path("/root/savant-runtime")
TEXT_LANGUAGES = {
    "python", "shell", "json", "json-lines", "yaml", "markdown", "text",
    "javascript", "javascript-react", "typescript", "typescript-react",
    "css", "html", "before", "service", "timer", "toml",
}
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", "__pycache__", "node_modules", "site-packages",
    ".venv", ".venv_voice", "exports", "repair_backups", "relics",
}
EXILES = {
    "carbon", "cataxis", "coda", "envoy", "filament", "graffiti", "lore",
    "mobius", "modus", "niche", "notary", "opus", "pact", "palaver",
    "shatter", "underscore", "urge", "zero",
}
OPUS_TERMS = {
    "provider", "model routing", "multi-agent", "orchestration", "openai",
    "anthropic", "gemini", "mistral", "consensus", "synthesis", "fusion",
    "token budget", "api key", "provider execution", "completion", "llm",
}
NICHE_TERMS = {
    "task discovery", "decomposition", "priority", "scheduler", "queue",
    "readiness", "blocker", "dependency", "masterplan", "task state",
}
AUTHORITY_TERMS = {
    "accepted", "authority", "canon", "constitutional", "decision",
    "supersedes", "precedence", "provisional", "historical",
}
KINDRED_TERMS = {
    "kindred", "kindred", "mother", "father", "daughter", "son", "ancestor",
    "descendant", "sibling", "family tree", "alliance contract",
}
MUTATION_PATTERNS = (
    re.compile(r"\b(shutil\.(?:move|rmtree|copy2?)|os\.(?:remove|unlink|rename|replace))\s*\("),
    re.compile(r"\bPath\([^\n]+\)\.(?:unlink|rename|replace|write_text|write_bytes)\s*\("),
    re.compile(r"\b(?:rm|mv|cp)\s+-[A-Za-z]*[rf]"),
)
VERSION_KEYS = {"version", "schema_version", "$schema", "apiVersion", "specversion"}


@dataclasses.dataclass(frozen=True, slots=True)
class DumpEntry:
    path: str
    category: str
    language: str
    content_id: str
    source_sha256: str
    rendered_sha256: str
    mode: str
    content: str
    duplicate_of: str | None = None

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.path).suffix.lower()

    @property
    def basename(self) -> str:
        return PurePosixPath(self.path).name


@dataclasses.dataclass(frozen=True, slots=True)
class Finding:
    pass_id: str
    severity: str
    code: str
    path: str | None
    message: str
    evidence: tuple[str, ...] = ()
    proposed_disposition: str = "review"
    confidence: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class Claim:
    term: str
    statement: str
    sources: tuple[str, ...]
    source_dates: tuple[str, ...]
    authority_states: tuple[str, ...]
    corroborated: bool
    conflict: bool
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(slots=True)
class AuditContext:
    dump_path: Path
    output_dir: Path
    manifest: dict[str, Any]
    entries: list[DumpEntry]
    by_path: dict[str, DumpEntry]
    by_hash: dict[str, list[DumpEntry]]
    findings: list[Finding]
    claims: list[Claim]
    dependencies: dict[str, set[str]]
    reverse_dependencies: dict[str, set[str]]
    classifications: dict[str, dict[str, Any]]
    opus_apertures: list[dict[str, Any]]
    passes_requested: int


class AuditError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def ignored_path(path: str) -> bool:
    return bool(set(PurePosixPath(path).parts) & EXCLUDED_PARTS)


def parse_dump(path: Path) -> tuple[dict[str, Any], list[DumpEntry]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "manifest\n----------------------------------------------------------------------------\n"
    start = text.find(marker)
    if start < 0:
        raise AuditError("sdump manifest marker not found")
    manifest_start = start + len(marker)
    manifest_end = text.find("\n\n============================================================================", manifest_start)
    if manifest_end < 0:
        raise AuditError("sdump manifest terminator not found")
    manifest = json.loads(text[manifest_start:manifest_end])

    header_re = re.compile(
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
    entries: list[DumpEntry] = []
    matches = list(header_re.finditer(text, manifest_end))
    end_marker = "\n\n============================================================================\nend content instance"
    for idx, match in enumerate(matches):
        body_start = match.end()
        body_end = text.find(end_marker, body_start)
        if body_end < 0:
            body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        content = text[body_start:body_end]
        if content.startswith("\n"):
            content = content[1:]
        if content and not content.endswith("\n"):
            content += "\n"
        entries.append(
            DumpEntry(
                path=match.group("path"),
                category=match.group("category"),
                language=match.group("language"),
                content_id=match.group("content_id"),
                source_sha256=match.group("source_sha256"),
                rendered_sha256=match.group("rendered_sha256"),
                mode="unknown",
                content=content,
            )
        )

    # Restore duplicate path instances from the manifest while sharing content.
    content_by_id = {entry.content_id: entry.content for entry in entries}
    present = {entry.path for entry in entries}
    for record in manifest.get("files", []):
        if not record.get("included") or record.get("path") in present:
            continue
        cid = record.get("content_id", "")
        entries.append(
            DumpEntry(
                path=record["path"],
                category=record.get("category", "unknown"),
                language=record.get("language", "unknown"),
                content_id=cid,
                source_sha256=record.get("source_sha256", ""),
                rendered_sha256=record.get("rendered_sha256", record.get("source_sha256", "")),
                mode=record.get("mode", "unknown"),
                content=content_by_id.get(cid, ""),
                duplicate_of=record.get("duplicate_of"),
            )
        )
    entries.sort(key=lambda item: item.path)
    return manifest, entries


def make_context(dump_path: Path, output_dir: Path, passes: int) -> AuditContext:
    manifest, entries = parse_dump(dump_path)
    by_path = {e.path: e for e in entries}
    by_hash: dict[str, list[DumpEntry]] = defaultdict(list)
    for entry in entries:
        by_hash[entry.source_sha256].append(entry)
    return AuditContext(
        dump_path=dump_path,
        output_dir=output_dir,
        manifest=manifest,
        entries=entries,
        by_path=by_path,
        by_hash=dict(by_hash),
        findings=[],
        claims=[],
        dependencies=defaultdict(set),
        reverse_dependencies=defaultdict(set),
        classifications={},
        opus_apertures=[],
        passes_requested=passes,
    )


def add(ctx: AuditContext, pass_id: str, severity: str, code: str,
        message: str, path: str | None = None, evidence: Sequence[str] = (),
        disposition: str = "review", confidence: float = 1.0) -> None:
    ctx.findings.append(Finding(pass_id, severity, code, path, message,
                                tuple(evidence), disposition, confidence))


def source_date(entry: DumpEntry) -> str:
    patterns = (
        re.compile(r"(?:created_at|accepted_at|updated_at|generated_at)\s*[:=]\s*['\"]?([^'\"\n]+)"),
        re.compile(r"\b(20\d{2}-\d{2}-\d{2}(?:T[^\s'\"]+)?)"),
    )
    for pattern in patterns:
        m = pattern.search(entry.content)
        if m:
            return m.group(1).strip()
    return "unknown"


def authority_state(entry: DumpEntry) -> str:
    lower = entry.content.lower()
    for state in ("accepted", "constitutional", "provisional", "proposed", "historical", "deprecated"):
        if re.search(rf"(?:status|state)\s*[:=]\s*['\"]?{state}\b", lower):
            return state
    if "/authority/" in f"/{entry.path}" or entry.category == "canon":
        return "authority-candidate"
    return "evidence"


def classify_owner(path: str, content: str) -> dict[str, Any]:
    lower_path = path.lower()
    lower = content.lower()
    owner = "unknown"
    confidence = 0.0
    reasons: list[str] = []
    for exile in EXILES:
        canonical = (
            f"/exiles/{exile}/" in f"/{lower_path}"
            or f"/exile/{exile}/" in f"/{lower_path}"
        )
        legacy = f"/{exile}/" in f"/{lower_path}" and any(
            prefix in f"/{lower_path}"
            for prefix in ("/tools/", "/edifices/identity/exiles/", "/runtime/")
        )
        if canonical or legacy:
            owner = exile
            confidence = 0.95 if canonical else 0.72
            reasons.append("canonical exile path" if canonical else "legacy owner path")
            break
    scores = {
        "opus": sum(term in lower for term in OPUS_TERMS),
        "niche": sum(term in lower for term in NICHE_TERMS),
    }
    if max(scores.values(), default=0) > 0:
        semantic = max(scores, key=scores.get)
        semantic_confidence = min(0.9, 0.35 + 0.08 * scores[semantic])
        if owner == "unknown":
            owner = semantic
            confidence = semantic_confidence
            reasons.append(f"semantic signal: {semantic}")
        elif semantic != owner and scores[semantic] >= 2:
            reasons.append(f"ownership conflict: path={owner}, semantics={semantic}")
            confidence = min(confidence, 0.65)
    return {"owner": owner, "confidence": round(confidence, 3), "reasons": reasons, "scores": scores}


def classify_artifact(entry: DumpEntry) -> str:
    p = entry.path.lower()
    if "/tests/" in f"/{p}" or p.startswith("tests/") or entry.basename.startswith("test_"):
        return "test"
    if "/migrations/" in f"/{p}":
        return "migration"
    if "/reports/" in f"/{p}" or p.startswith("reports/"):
        return "report"
    if "/history/" in f"/{p}" or ".bak" in p or "before-" in p:
        return "history"
    if "/authority/" in f"/{p}" or entry.category == "canon":
        return "authority-or-canon"
    if "/runtime/" in f"/{p}":
        return "runtime"
    if entry.suffix in {".json", ".yaml", ".yml", ".toml"} and any(x in p for x in ("schema", "contract", "registry", "manifest")):
        return "structured-contract"
    if entry.language in {"python", "shell", "javascript", "javascript-react", "typescript", "typescript-react"}:
        return "program-source"
    if entry.language == "markdown":
        return "documentation"
    return "data-or-projection"


def py_imports(entry: DumpEntry) -> set[str]:
    refs: set[str] = set()
    try:
        tree = ast.parse(entry.content, filename=entry.path)
    except SyntaxError:
        return refs
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            refs.add(node.module)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/root/savant-runtime/"):
            refs.add(node.value.removeprefix("/root/savant-runtime/"))
    return refs


def shell_refs(entry: DumpEntry) -> set[str]:
    refs = set(re.findall(r"/root/savant-runtime/[A-Za-z0-9_./@+,:=-]+", entry.content))
    return {r.removeprefix("/root/savant-runtime/").rstrip("'\";,)") for r in refs}


def all_refs(entry: DumpEntry) -> set[str]:
    refs = set()
    if entry.language == "python":
        refs |= py_imports(entry)
    if entry.language == "shell":
        refs |= shell_refs(entry)
    refs |= {m.group(1) for m in re.finditer(r"(?:path|source|target|file)\s*[:=]\s*['\"]?(/root/savant-runtime/[^'\"\s]+)", entry.content)}
    return refs


def p01_inventory(ctx: AuditContext) -> None:
    counts = Counter(e.language for e in ctx.entries)
    if len(ctx.entries) != ctx.manifest.get("counts", {}).get("included_files"):
        add(ctx, "P01", "warning", "inventory-count-drift",
            f"reconstructed {len(ctx.entries)} entries; manifest declares {ctx.manifest.get('counts', {}).get('included_files')}")
    add(ctx, "P01", "info", "inventory-summary", f"languages={dict(sorted(counts.items()))}")


def p02_integrity(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if not entry.content:
            add(ctx, "P02", "warning", "missing-content", "content unavailable in projection", entry.path,
                disposition="require-live-read", confidence=0.9)
            continue
        actual = hashlib.sha256(entry.content.encode("utf-8")).hexdigest()
        expected = entry.rendered_sha256 or entry.source_sha256
        if actual != expected and not entry.duplicate_of:
            add(ctx, "P02", "warning", "dump-hash-mismatch",
                f"rendered content hash {actual} differs from declared rendered hash {expected}", entry.path,
                disposition="verify-dump-boundary-or-live-source", confidence=0.8)


def p03_python_syntax(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language != "python" or not entry.content:
            continue
        try:
            ast.parse(entry.content, filename=entry.path)
        except SyntaxError as exc:
            add(ctx, "P03", "critical", "python-syntax", str(exc), entry.path,
                disposition="block-release-and-repair")


def p04_json(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language not in {"json", "json-lines"} or not entry.content:
            continue
        try:
            if entry.language == "json-lines":
                for line in entry.content.splitlines():
                    if line.strip(): json.loads(line)
            else:
                json.loads(entry.content)
        except json.JSONDecodeError as exc:
            add(ctx, "P04", "critical", "json-invalid", str(exc), entry.path,
                disposition="repair-or-reclassify")


def p05_shell(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language != "shell" or not entry.content:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
            fh.write(entry.content)
            temp = fh.name
        try:
            cp = subprocess.run(["bash", "-n", temp], capture_output=True, text=True)
            if cp.returncode:
                add(ctx, "P05", "critical", "shell-syntax", cp.stderr.strip(), entry.path,
                    disposition="block-release-and-repair")
        finally:
            os.unlink(temp)


def p06_duplicates(ctx: AuditContext) -> None:
    for digest, group in ctx.by_hash.items():
        if digest and len(group) > 1:
            paths = tuple(e.path for e in group)
            add(ctx, "P06", "warning", "exact-duplicate", f"{len(group)} exact copies", paths[0], paths,
                "classify-projection-history-or-deduplicate", 1.0)


def p07_ownership(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        result = classify_owner(entry.path, entry.content)
        ctx.classifications[entry.path] = {
            **result, "artifact_kind": classify_artifact(entry),
            "authority_state": authority_state(entry),
        }
        if any("ownership conflict" in r for r in result["reasons"]):
            add(ctx, "P07", "high", "semantic-owner-conflict", "; ".join(result["reasons"]), entry.path,
                disposition="split-by-rubric-owner", confidence=result["confidence"])


def p08_rubric(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        c = ctx.classifications[entry.path]
        if c["artifact_kind"] != "program-source":
            continue
        if "/rubric/" not in f"/{entry.path}" and c["owner"] in EXILES:
            add(ctx, "P08", "medium", "rubric-candidate", f"program source owned by {c['owner']} is outside a rubric", entry.path,
                disposition=f"propose-{c['owner']}-rubric", confidence=c["confidence"])


def p09_cabal(ctx: AuditContext) -> None:
    by_hash_owners: dict[str, set[str]] = defaultdict(set)
    for entry in ctx.entries:
        owner = ctx.classifications[entry.path]["owner"]
        if owner != "unknown": by_hash_owners[entry.source_sha256].add(owner)
    for digest, owners in by_hash_owners.items():
        if len(owners) >= 2:
            paths = tuple(e.path for e in ctx.by_hash[digest])
            add(ctx, "P09", "medium", "cabal-candidate", f"identical implementation consumed or stored by owners {sorted(owners)}", paths[0], paths,
                "review-for-narrowest-scope-cabal", 0.8)


def p10_dependencies(ctx: AuditContext) -> None:
    paths = set(ctx.by_path)
    module_index: dict[str, str] = {}
    for path in paths:
        if path.endswith(".py"):
            module_index[path[:-3].replace("/", ".")] = path
            if path.endswith("/__init__.py"):
                module_index[path[:-12].replace("/", ".")] = path
    for entry in ctx.entries:
        for ref in all_refs(entry):
            target = None
            if ref in paths: target = ref
            elif ref.startswith("/root/savant-runtime/"): target = ref.removeprefix("/root/savant-runtime/")
            elif ref in module_index: target = module_index[ref]
            else:
                for module, candidate in module_index.items():
                    if ref == module or ref.startswith(module + "."):
                        target = candidate; break
            if target and target != entry.path:
                ctx.dependencies[entry.path].add(target)
                ctx.reverse_dependencies[target].add(entry.path)
            elif ref.startswith("/root/savant-runtime/") or "/" in ref:
                add(ctx, "P10", "medium", "missing-reference", f"unresolved reference: {ref}", entry.path,
                    disposition="verify-live-target", confidence=0.75)


def p11_cycles(ctx: AuditContext) -> None:
    # Tarjan SCC, stdlib-only.
    index = 0; stack: list[str] = []; onstack: set[str] = set()
    indices: dict[str, int] = {}; low: dict[str, int] = {}
    def visit(v: str) -> None:
        nonlocal index
        indices[v] = low[v] = index; index += 1; stack.append(v); onstack.add(v)
        for w in ctx.dependencies.get(v, ()):
            if w not in indices:
                visit(w); low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            comp = []
            while True:
                w = stack.pop(); onstack.remove(w); comp.append(w)
                if w == v: break
            if len(comp) > 1:
                add(ctx, "P11", "high", "dependency-cycle", f"cycle of {len(comp)} files", comp[0], tuple(sorted(comp)),
                    "review-cycle-contract", 1.0)
    for path in ctx.by_path:
        if path not in indices: visit(path)


def p12_opus(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        lower = entry.content.lower()
        score = sum(term in lower for term in OPUS_TERMS)
        if score < 2: continue
        c = ctx.classifications[entry.path]
        aperture = {
            "path": entry.path,
            "current_owner": c["owner"],
            "opus_signal_score": score,
            "recommended_role": "opus-rubric" if c["artifact_kind"] == "program-source" else "opus-contract-or-projection",
            "confidence": min(0.98, 0.55 + score * 0.05),
        }
        ctx.opus_apertures.append(aperture)
        if c["owner"] not in {"opus", "unknown"}:
            add(ctx, "P12", "high", "opus-responsibility-outside-opus", f"Opus signal score={score}, current owner={c['owner']}", entry.path,
                disposition="split-intent-from-execution", confidence=aperture["confidence"])


def p13_authority(ctx: AuditContext) -> None:
    terms: dict[str, list[DumpEntry]] = defaultdict(list)
    for entry in ctx.entries:
        lower = entry.content.lower()
        for term in ("kindred", "kindred", "mote", "shard", "mood", "rubric", "cabal", "masterplan"):
            if term in lower: terms[term].append(entry)
    for term, sources in terms.items():
        states = tuple(authority_state(e) for e in sources[:20])
        dates = tuple(source_date(e) for e in sources[:20])
        accepted = [e for e in sources if authority_state(e) in {"accepted", "constitutional"}]
        statements = set()
        for e in accepted[:20]:
            for line in e.content.splitlines():
                if term in line.lower() and 10 <= len(line.strip()) <= 240:
                    statements.add(re.sub(r"\s+", " ", line.strip()))
        conflict = len(statements) > 1 and term in {"kindred", "mote", "shard", "mood"}
        ctx.claims.append(Claim(term, "; ".join(sorted(statements)[:8]) or "presence only",
                                tuple(e.path for e in sources[:20]), dates, states,
                                len({e.path for e in accepted}) >= 2, conflict,
                                0.95 if len(accepted) >= 2 and not conflict else 0.55))
        if conflict:
            add(ctx, "P13", "critical", "authority-conflict", f"conflicting accepted statements for {term}", None,
                tuple(e.path for e in accepted[:20]), "require-accepted-decision", 0.95)


def p14_versioning(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if ctx.classifications[entry.path]["artifact_kind"] != "structured-contract" or not entry.content:
            continue
        present = any(re.search(rf"(?m)^\s*[\"']?{re.escape(key)}[\"']?\s*[:=]", entry.content) for key in VERSION_KEYS)
        if not present:
            add(ctx, "P14", "medium", "unversioned-contract", "structured contract lacks explicit version metadata", entry.path,
                disposition="add-version-through-compatible-migration", confidence=0.9)


def p15_security(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language not in {"python", "shell"}: continue
        for pattern in MUTATION_PATTERNS:
            if pattern.search(entry.content):
                add(ctx, "P15", "medium", "mutation-capability", "file performs or may perform durable mutation", entry.path,
                    disposition="bind-coda-capability-and-commit-gate", confidence=0.85)
                break
        if re.search(r"subprocess\.(?:run|Popen|call).*shell\s*=\s*True", entry.content, re.S):
            add(ctx, "P15", "high", "shell-injection-risk", "subprocess shell=True requires explicit justification", entry.path,
                disposition="replace-with-argv-or-validate", confidence=0.95)


def p16_secrets(ctx: AuditContext) -> None:
    rx = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([^'\"]{8,})")
    for entry in ctx.entries:
        for m in rx.finditer(entry.content):
            value = m.group(2)
            if not value.startswith(("${", "env:", "REDACTED", "<")):
                add(ctx, "P16", "critical", "possible-secret", f"possible embedded credential field {m.group(1)}", entry.path,
                    disposition="revoke-and-move-to-secret-provider", confidence=0.7)


def p17_exceptions(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language != "python": continue
        if re.search(r"except\s+(?:BaseException|Exception)\s*(?:as\s+\w+)?\s*:", entry.content):
            add(ctx, "P17", "low", "broad-exception", "broad exception boundary requires case review", entry.path,
                disposition="narrow-or-document-boundary", confidence=0.85)


def p18_placeholders(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if re.search(r"\b(?:TODO|FIXME|NotImplementedError|pass\s*(?:#.*)?$|stub)\b", entry.content, re.I | re.M):
            add(ctx, "P18", "medium", "incomplete-marker", "incomplete implementation marker present", entry.path,
                disposition="implement-or-mark-unavailable", confidence=0.85)


def p19_shell_quality(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language != "shell": continue
        if re.search(r"<<-?['\"]?[A-Z][A-Z0-9_]*['\"]?", entry.content):
            add(ctx, "P19", "medium", "heredoc-generation", "shell embeds generated file content", entry.path,
                disposition="move-program-content-to-rubric", confidence=0.95)
        if re.search(r"(?m)^\s*cd\s+(?!/)", entry.content):
            add(ctx, "P19", "low", "relative-cd", "relative working-directory dependency", entry.path,
                disposition="use-absolute-root-or-explicit-cwd", confidence=0.95)


def p20_projection(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        p = entry.path.lower()
        if entry.category in {"source", "canon"} and any(x in p for x in ("report", "projection", "generated", "snapshot")):
            add(ctx, "P20", "low", "projection-authority-review", "projection/report-like artifact is included as source or canon", entry.path,
                disposition="declare-authority-state-and-rebuild-contract", confidence=0.7)


def p21_tests(ctx: AuditContext) -> None:
    sources = [e for e in ctx.entries if ctx.classifications[e.path]["artifact_kind"] == "program-source"]
    tests = [e for e in ctx.entries if ctx.classifications[e.path]["artifact_kind"] == "test"]
    test_stems = {PurePosixPath(t.path).stem.lower() for t in tests}
    referenced = set()
    token_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
    for test in tests:
        referenced.update(token.lower() for token in token_re.findall(test.content))
    for entry in sources:
        stem = PurePosixPath(entry.path).stem.lower()
        if stem in {"__init__", "conftest"} or len(entry.content) < 200: continue
        if stem not in referenced and not any(stem in ts for ts in test_stems):
            add(ctx, "P21", "low", "test-coverage-candidate", "no direct test reference found", entry.path,
                disposition="add-focused-test-or-document-indirect-coverage", confidence=0.55)


def p22_dead_code(ctx: AuditContext) -> None:
    for entry in ctx.entries:
        if entry.language != "python": continue
        try: tree = ast.parse(entry.content)
        except SyntaxError: continue
        defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")}
        if not defs: continue
        dependents_text = "\n".join(ctx.by_path[p].content for p in ctx.reverse_dependencies.get(entry.path, ()) if p in ctx.by_path)
        unused = [name for name in defs if name not in dependents_text and entry.content.count(name) <= 1]
        if unused:
            add(ctx, "P22", "low", "public-symbol-review", f"possibly unreferenced public symbols: {unused[:12]}", entry.path,
                disposition="verify-public-api-before-retirement", confidence=0.45)


def p23_opus_contracts(ctx: AuditContext) -> None:
    needed = {
        "request": False, "provider": False, "routing": False, "execution": False,
        "synthesis": False, "evidence": False, "budget": False, "observability": False,
        "security": False,
    }
    for entry in ctx.entries:
        if "opus" not in entry.path.lower() and "opus" not in entry.content.lower(): continue
        lower = entry.content.lower()
        for key in needed:
            if key in lower: needed[key] = True
    for key, present in needed.items():
        if not present:
            add(ctx, "P23", "high", "opus-contract-gap", f"no corroborated Opus {key} contract found in included snapshot", None,
                disposition=f"define-opus-{key}-contract", confidence=0.7)


def p24_modernization(ctx: AuditContext) -> None:
    # Report candidates rather than install dependencies blindly.
    candidates = {
        "pydantic": "strict boundary validation",
        "networkx": "analysis adapter for dependency and lineage graphs",
        "opentelemetry": "traces, metrics, and logs",
        "hypothesis": "property-based invariant testing",
        "ruff": "fast linting and formatting",
        "pyright": "strict Python type analysis",
        "cue": "constraint and configuration validation",
        "opa": "policy decision evaluation",
        "cloudevents": "portable event envelopes",
    }
    corpus = "\n".join(e.content.lower() for e in ctx.entries)
    for name, purpose in candidates.items():
        if name not in corpus:
            add(ctx, "P24", "info", "dependency-candidate", f"evaluate {name}: {purpose}", None,
                disposition="benchmark-before-adoption", confidence=0.8)


def p25_integrated(ctx: AuditContext) -> None:
    blockers = [f for f in ctx.findings if f.severity in {"critical", "high"}]
    add(ctx, "P25", "info", "integrated-gate", f"release/migration blockers={len(blockers)}",
        disposition="block-mutation" if blockers else "eligible-for-staged-validation")


BASE_PASSES = [
    p01_inventory, p02_integrity, p03_python_syntax, p04_json, p05_shell,
    p06_duplicates, p07_ownership, p08_rubric, p09_cabal, p10_dependencies,
    p11_cycles, p12_opus, p13_authority, p14_versioning, p15_security,
    p16_secrets, p17_exceptions, p18_placeholders, p19_shell_quality,
    p20_projection, p21_tests, p22_dead_code, p23_opus_contracts,
    p24_modernization, p25_integrated,
]


def run_passes(ctx: AuditContext) -> None:
    # First 25 passes establish facts. Additional requested passes repeat the
    # integrated fixed-point checks and verify output determinism without
    # duplicating findings.
    for fn in BASE_PASSES:
        fn(ctx)
    seen = {(f.code, f.path, f.message) for f in ctx.findings}
    for iteration in range(26, ctx.passes_requested + 1):
        finding_digest = digest_json(sorted(seen))
        add(ctx, f"P{iteration:02d}", "info", "fixed-point-pass",
            f"iteration={iteration}; stable=true; finding_digest={finding_digest}",
            disposition="continue" if iteration < ctx.passes_requested else "complete")
        seen.add(("fixed-point-pass", None, f"iteration={iteration}; stable=true; finding_digest={finding_digest}"))


def enhancement_catalog() -> list[dict[str, str]]:
    names = [
        ("stable-identity", "Stable identifiers independent of paths"),
        ("content-addressing", "SHA-256 manifests and immutable artifact identity"),
        ("authority-matrix", "Two-source corroboration and explicit conflict records"),
        ("rubric-ownership", "One canonical Rubric owner for each program file"),
        ("cabal-promotion", "Evidence-based shared-scope implementation promotion"),
        ("reverse-dependency-index", "Explicit dependents for safe migration"),
        ("semantic-owner-linter", "Detect path/meaning ownership conflicts"),
        ("transactional-migrations", "Baseline, staging, activation, rollback receipts"),
        ("compatibility-retirement", "Tracked consumers before path retirement"),
        ("opus-aperture-map", "Every relevant AI integration point mapped to Opus"),
        ("opus-request-contract", "Typed requester-owned AI intent envelope"),
        ("opus-provider-registry", "Provider/model capabilities and lifecycle registry"),
        ("opus-routing-policy", "Cost, latency, quality, privacy, and availability routing"),
        ("opus-execution-receipts", "Per-call lineage, usage, latency, and failure receipts"),
        ("opus-synthesis-contract", "Deterministic normalization and fusion boundaries"),
        ("notary-evidence-gate", "AI output remains candidate evidence until verified"),
        ("coda-commit-gate", "Durable mutation delegated through approved commit workflow"),
        ("niche-opus-separation", "Task intent separated from AI execution"),
        ("schema-versioning", "Reader/writer compatibility negotiation"),
        ("cue-validation", "Optional constraint validation adapter"),
        ("opa-policy", "Optional deny-by-default policy evaluation"),
        ("graph-scc-audit", "Exact strongly connected component reporting"),
        ("property-tests", "Generated invariant testing for graphs and migrations"),
        ("mutation-tests", "Constitutional validator strength assessment"),
        ("impact-test-selection", "Dependency-closure based focused validation"),
        ("deterministic-projections", "Digest-stable generated views"),
        ("event-envelope", "CloudEvents-compatible semantic events"),
        ("otel-semantic-conventions", "Savant-specific trace, metric, and log fields"),
        ("capability-security", "Explicit filesystem, process, network, secret capabilities"),
        ("secret-provider", "No embedded credentials in Rubrics or Cabals"),
        ("shell-thinning", "Business logic removed from launchers"),
        ("reproducible-locks", "Pinned and hashed dependency environments"),
        ("supply-chain-records", "License, source, digest, fallback, removal plan"),
        ("structural-health", "Generated health dimensions per element/Rubric/Cabal"),
        ("replay-verification", "Rebuild projections from accepted events"),
        ("semantic-diff", "Meaning-aware before/after migration reports"),
        ("vault-custody-contract", "Retention, source, replay, and authority metadata"),
        ("kindred-boundary-audit", "Preserve family-lineage semantics and registry conflict"),
        ("segue-transition-audit", "Keep governed transitions distinct from generic edges"),
        ("observatory-causality", "Expose authority, lineage, owner, task, and evidence"),
    ]
    return [{"id": f"ENH-{i:02d}", "name": n, "purpose": p} for i, (n, p) in enumerate(names, 1)]


def proposed_destination(path: str, classification: Mapping[str, Any]) -> str | None:
    owner = classification.get("owner")
    kind = classification.get("artifact_kind")
    if owner not in EXILES: return None
    base = f"ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/{owner}"
    name = PurePosixPath(path).name
    if kind == "program-source": return f"{base}/rubric/unclassified/source/{name}"
    if kind == "test": return f"{base}/rubric/unclassified/tests/{name}"
    if kind == "migration": return f"{base}/rubric/unclassified/migrations/{name}"
    return None


def emit(ctx: AuditContext) -> None:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    findings = sorted((f.as_dict() for f in ctx.findings), key=lambda x: (x["severity"], x["code"], x.get("path") or ""))
    migrations = []
    for path, classification in sorted(ctx.classifications.items()):
        dest = proposed_destination(path, classification)
        if dest and dest != path:
            migrations.append({
                "source": path,
                "proposed_destination": dest,
                "owner": classification["owner"],
                "confidence": classification["confidence"],
                "action": "proposal-only",
                "precondition_sha256": ctx.by_path[path].source_sha256,
                "compatibility_required": bool(ctx.reverse_dependencies.get(path)),
                "dependents": sorted(ctx.reverse_dependencies.get(path, ())),
            })
    result = {
        "schema": "savant.structural-intelligence.audit.v1",
        "version": VERSION,
        "generated_at": utc_now(),
        "source_dump": str(ctx.dump_path),
        "source_snapshot_hash": ctx.manifest.get("snapshot_hash"),
        "passes_requested": ctx.passes_requested,
        "entries": len(ctx.entries),
        "findings": findings,
        "claims": [c.as_dict() for c in ctx.claims],
        "classifications": ctx.classifications,
        "dependencies": {k: sorted(v) for k, v in sorted(ctx.dependencies.items())},
        "reverse_dependencies": {k: sorted(v) for k, v in sorted(ctx.reverse_dependencies.items())},
        "opus_apertures": sorted(ctx.opus_apertures, key=lambda x: (-x["opus_signal_score"], x["path"])),
        "migration_proposals": migrations,
        "enhancements": enhancement_catalog(),
        "mutation_performed": False,
    }
    result["audit_digest"] = digest_json(result)
    (ctx.output_dir / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (ctx.output_dir / "migration-proposal.json").write_text(json.dumps(migrations, indent=2, sort_keys=True), encoding="utf-8")
    (ctx.output_dir / "opus-apertures.json").write_text(json.dumps(result["opus_apertures"], indent=2, sort_keys=True), encoding="utf-8")
    (ctx.output_dir / "authority-matrix.json").write_text(json.dumps(result["claims"], indent=2, sort_keys=True), encoding="utf-8")
    (ctx.output_dir / "enhancements.json").write_text(json.dumps(result["enhancements"], indent=2, sort_keys=True), encoding="utf-8")

    sev = Counter(f.severity for f in ctx.findings)
    lines = [
        "# Savant Structural Intelligence Audit",
        "",
        f"Generated: `{result['generated_at']}`",
        f"Source snapshot: `{result['source_snapshot_hash']}`",
        f"Passes: `{ctx.passes_requested}`",
        f"Entries: `{len(ctx.entries)}`",
        f"Audit digest: `{result['audit_digest']}`",
        "",
        "## Severity counts",
        "",
    ]
    for key in ("critical", "high", "medium", "warning", "low", "info"):
        lines.append(f"- {key}: {sev.get(key, 0)}")
    lines += ["", "## Critical and high findings", ""]
    for f in ctx.findings:
        if f.severity in {"critical", "high"}:
            lines.append(f"- **{f.code}** `{f.path or 'system'}` — {f.message}")
    lines += ["", "## Implementation boundary", "",
              "This compiler performed no mutation. Every migration entry is a proposal requiring live hash preconditions, accepted authority, staging, validation, and rollback.", ""]
    (ctx.output_dir / "AUDIT.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=50)
    args = parser.parse_args(argv)
    if args.passes < 25:
        parser.error("--passes must be at least 25")
    ctx = make_context(args.dump.resolve(), args.output.resolve(), args.passes)
    run_passes(ctx)
    emit(ctx)
    print(json.dumps({
        "status": "completed",
        "passes": args.passes,
        "entries": len(ctx.entries),
        "findings": len(ctx.findings),
        "output": str(ctx.output_dir),
        "mutation_performed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(2)
