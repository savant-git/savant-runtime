from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping

from .model import Projection
from .util import atomic_write_json, atomic_write_text, canonical_json_bytes, now_iso, sha256_file, stable_hash

AUDIT_SCHEMA = "savant.sdump.audit.v4"
MAX_CAPTURE_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT = 8.0
SECRET_NAME = re.compile(r"(?i)(secret|token|password|passwd|api[_-]?key|private[_-]?key|credential|cookie|session|authorization)")
ENV_ALLOW_PREFIXES = ("SAVANT_", "SDUMP_", "PYTHON", "NODE_", "NPM_", "JAVA_", "PATH", "LANG", "LC_", "HOME", "SHELL", "VIRTUAL_ENV")
LOCKFILE_NAMES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb",
    "cargo.lock", "poetry.lock", "pdm.lock", "uv.lock", "pipfile.lock", "composer.lock", "gemfile.lock",
    "go.sum", "gradle.lockfile", "packages.lock.json",
}
MANIFEST_NAMES = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.py", "setup.cfg", "package.json",
    "cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "gemfile",
}
TOOL_PROBES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("python", (sys.executable, "--version")), ("git", ("git", "--version")), ("node", ("node", "--version")),
    ("npm", ("npm", "--version")), ("pnpm", ("pnpm", "--version")), ("yarn", ("yarn", "--version")),
    ("bun", ("bun", "--version")), ("java", ("java", "-version")), ("go", ("go", "version")),
    ("rustc", ("rustc", "--version")), ("cargo", ("cargo", "--version")), ("docker", ("docker", "--version")),
    ("podman", ("podman", "--version")), ("sqlite3", ("sqlite3", "--version")), ("adb", ("adb", "version")),
)

@dataclass(frozen=True)
class CommandEvidence:
    argv: tuple[str, ...]
    available: bool
    returncode: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv), "available": self.available, "returncode": self.returncode,
            "timed_out": self.timed_out, "duration_ms": self.duration_ms, "stdout": self.stdout, "stderr": self.stderr,
        }


def _bounded(value: str, limit: int = MAX_CAPTURE_BYTES) -> str:
    data = value.encode("utf-8", errors="replace")
    if len(data) <= limit:
        return value
    clipped = data[:limit].decode("utf-8", errors="replace")
    return clipped + f"\n<sdump-truncated original_bytes={len(data)} limit={limit}>\n"


def run_readonly(argv: Iterable[str], cwd: Path | None = None, timeout: float = DEFAULT_TIMEOUT) -> CommandEvidence:
    command = tuple(str(part) for part in argv)
    executable = command[0] if command else ""
    if not executable or (os.sep not in executable and shutil.which(executable) is None):
        return CommandEvidence(command, False, None, False, 0, "", "")
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=str(cwd) if cwd else None, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
                                   timeout=timeout, check=False, env=os.environ.copy())
        return CommandEvidence(command, True, completed.returncode, False,
                               int((time.monotonic() - started) * 1000), _bounded(completed.stdout), _bounded(completed.stderr))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandEvidence(command, True, None, True, int((time.monotonic() - started) * 1000), _bounded(stdout), _bounded(stderr))
    except OSError as exc:
        return CommandEvidence(command, False, None, False, int((time.monotonic() - started) * 1000), "", str(exc))


def _git_root(target: Path) -> Path | None:
    probe = target if target.is_dir() else target.parent
    result = run_readonly(("git", "-C", str(probe), "rev-parse", "--show-toplevel"), timeout=3)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve(strict=False)


def collect_git(targets: list[Path]) -> list[dict[str, Any]]:
    roots: list[Path] = []
    for target in targets:
        root = _git_root(target)
        if root and root not in roots:
            roots.append(root)
    records: list[dict[str, Any]] = []
    for root in roots:
        def g(*args: str, timeout: float = 5) -> CommandEvidence:
            return run_readonly(("git", "-C", str(root), *args), timeout=timeout)
        head = g("rev-parse", "HEAD")
        branch = g("branch", "--show-current")
        status = g("status", "--porcelain=v1", "--untracked-files=all", timeout=12)
        remotes = g("remote", "-v")
        recent = g("log", "-n", "20", "--date=iso-strict", "--pretty=format:%H%x09%aI%x09%an%x09%s")
        submodules = g("submodule", "status", "--recursive", timeout=12)
        records.append({
            "root": str(root), "head": head.stdout.strip() or None, "branch": branch.stdout.strip() or None,
            "status_porcelain": status.stdout.splitlines(), "dirty": bool(status.stdout.strip()),
            "remotes": sorted(set(remotes.stdout.splitlines())), "recent_commits": recent.stdout.splitlines(),
            "submodules": submodules.stdout.splitlines(), "evidence_errors": [
                x.to_dict() for x in (head, branch, status, remotes, recent, submodules)
                if x.available and x.returncode not in (0, None)
            ],
        })
    return records


def collect_host() -> dict[str, Any]:
    uname = platform.uname()
    load = None
    try:
        load = list(os.getloadavg())
    except (AttributeError, OSError):
        pass
    disk = shutil.disk_usage("/")
    return {
        "hostname": socket.gethostname(), "platform": platform.platform(), "system": uname.system,
        "release": uname.release, "machine": uname.machine, "python": platform.python_version(),
        "python_implementation": platform.python_implementation(), "cpu_count": os.cpu_count(), "loadavg": load,
        "disk_root": {"total": disk.total, "used": disk.used, "free": disk.free},
        "uid": os.getuid() if hasattr(os, "getuid") else None, "gid": os.getgid() if hasattr(os, "getgid") else None,
    }


def collect_environment() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for key in sorted(os.environ):
        upper = key.upper()
        sensitive = bool(SECRET_NAME.search(key))
        relevant = sensitive or any(upper == prefix or upper.startswith(prefix) for prefix in ENV_ALLOW_PREFIXES)
        if not relevant:
            continue
        value = os.environ.get(key, "")
        rows.append({"name": key, "set": key in os.environ, "nonempty": bool(value), "sensitive": sensitive,
                     "value": None if sensitive else value[:4096]})
    return {"variables": rows, "policy": "secret-like values are never captured"}


def collect_tools() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, argv in TOOL_PROBES:
        evidence = run_readonly(argv, timeout=4)
        result[name] = evidence.to_dict()
    return result


def _safe_hash(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "mode": oct(stat.st_mode & 0o7777),
                "sha256": sha256_file(path), "error": None}
    except Exception as exc:
        return {"path": str(path), "size": None, "mtime_ns": None, "mode": None, "sha256": None,
                "error": f"{type(exc).__name__}: {exc}"}


def collect_dependency_files(targets: list[Path], maximum: int = 10000) -> dict[str, Any]:
    found: dict[str, dict[str, Any]] = {}
    for target in targets:
        root = target if target.is_dir() else target.parent
        count = 0
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "target"})
            for name in sorted(files):
                folded = name.casefold()
                if folded in LOCKFILE_NAMES or folded in MANIFEST_NAMES or folded.startswith("requirements") and folded.endswith(".txt"):
                    path = Path(current) / name
                    key = str(path.resolve(strict=False))
                    found.setdefault(key, _safe_hash(path))
                    count += 1
                    if len(found) >= maximum:
                        return {"files": list(found.values()), "truncated": True, "maximum": maximum}
            if count >= maximum:
                break
    return {"files": list(found.values()), "truncated": False, "maximum": maximum}


def collect_oversize_fingerprints(projection: Projection, targets: list[Path]) -> list[dict[str, Any]]:
    target_map = {target.name: target for target in targets if target.is_dir()}
    rows: list[dict[str, Any]] = []
    for item in projection.skipped:
        if item.reason != "max_file_bytes_exceeded":
            continue
        resolved: Path | None = None
        for root in targets:
            base = root if root.is_dir() else root.parent
            candidate = base / item.path
            if candidate.is_file():
                resolved = candidate
                break
        row = _safe_hash(resolved) if resolved else {"path": item.path, "size": item.size, "mtime_ns": None, "mode": None, "sha256": None, "error": "unresolved"}
        row["projection_path"] = item.path
        rows.append(row)
    return rows


def collect_processes() -> dict[str, Any]:
    ps = run_readonly(("ps", "-eo", "pid=,ppid=,uid=,etimes=,stat=,comm=,args="), timeout=5)
    return ps.to_dict()


def collect_listeners() -> dict[str, Any]:
    for argv in (("ss", "-lntup"), ("ss", "-lntp"), ("netstat", "-lntp")):
        result = run_readonly(argv, timeout=5)
        if result.available:
            return result.to_dict()
    return CommandEvidence(tuple(), False, None, False, 0, "", "no supported listener tool found").to_dict()


def collect_python_packages() -> dict[str, Any]:
    result = run_readonly((sys.executable, "-m", "pip", "list", "--format=json", "--disable-pip-version-check"), timeout=15)
    payload: Any = None
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = None
    return {"command": result.to_dict(), "packages": payload}


def collect_validation(targets: list[Path], enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "checks": []}
    checks: list[dict[str, Any]] = []
    for target in targets:
        root = target if target.is_dir() else target.parent
        script = (
            "import ast,pathlib,sys; root=pathlib.Path(sys.argv[1]); bad=[]; n=0; "
            "\nfor p in root.rglob('*.py'):\n"
            "  if any(x in p.parts for x in ('.git','.venv','venv','node_modules','vendor','build','dist')): continue\n"
            "  n+=1\n"
            "  try: ast.parse(p.read_text(encoding='utf-8',errors='strict'), filename=str(p))\n"
            "  except Exception as e: bad.append(f'{p}: {type(e).__name__}: {e}')\n"
            "print(f'python_files={n} failures={len(bad)}'); print('\\n'.join(bad[:100])); sys.exit(1 if bad else 0)"
        )
        check = run_readonly((sys.executable, "-c", script, str(root)), timeout=30)
        checks.append({"kind": "python-ast-parse", "root": str(root), **check.to_dict()})
        package = root / "package.json"
        if package.is_file():
            try:
                payload = json.loads(package.read_text(encoding="utf-8"))
                scripts = payload.get("scripts", {}) if isinstance(payload, dict) else {}
                checks.append({"kind": "package-script-inventory", "root": str(root), "available": True,
                               "returncode": 0, "timed_out": False, "duration_ms": 0,
                               "stdout": json.dumps(sorted(scripts) if isinstance(scripts, dict) else []), "stderr": ""})
            except Exception as exc:
                checks.append({"kind": "package-script-inventory", "root": str(root), "available": True,
                               "returncode": 1, "timed_out": False, "duration_ms": 0, "stdout": "",
                               "stderr": f"{type(exc).__name__}: {exc}"})
    return {"enabled": True, "checks": checks}


def _projection_inventory(projection: Projection) -> dict[str, Any]:
    return {
        "snapshot_hash": projection.snapshot_hash,
        "stats": projection.stats.to_dict(),
        "included": [r.to_dict() for r in projection.records],
        "skipped": [r.to_dict() for r in projection.skipped],
        "failures": [r.to_dict() for r in projection.failures],
        "symlinks": projection.symlinks,
    }


def _coverage(
    projection: Projection,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Return explicit audit coverage and accounting semantics.

    Important accounting rule:

    ``files_seen`` belongs to filesystem discovery.

    ``projection.records`` belongs to the authoritative candidate
    projection.

    ``projection.skipped`` is a diagnostic/event ledger and may contain
    discovery-stage exclusions as well as projection-stage dispositions.
    It therefore MUST NOT be added to included files and compared against
    files_seen as though all three represented one population.

    The legacy ``score`` and ``dimensions`` fields remain available for
    compatibility with v4 consumers.
    """
    from collections import Counter

    stats = projection.stats.to_dict()

    files_seen = max(
        0,
        int(stats.get("files_seen", 0)),
    )

    included_files = max(
        0,
        int(stats.get("included_files", 0)),
    )

    hard_failures = max(
        0,
        int(stats.get("failures", 0)),
    )

    records = list(projection.records)

    projected_included = sum(
        1
        for record in records
        if record.included
    )

    projected_excluded = sum(
        1
        for record in records
        if not record.included
    )

    projected_total = len(records)

    record_reason_counts = Counter(
        record.reason or "included"
        for record in records
        if not record.included
    )

    skip_reason_counts = Counter(
        record.reason
        for record in projection.skipped
    )

    failure_reason_counts = Counter(
        record.reason
        for record in projection.failures
    )

    discovery_exclusion_reasons = {
        "excluded_absolute_root",
        "excluded_directory_name",
        "excluded_extension",
        "excluded_pattern",
        "hidden_path",
        "max_file_bytes_exceeded",
        "non_authoritative_extension",
        "not_regular_file",
    }

    projection_exclusion_reasons = {
        "binary_content",
        "undecodable_text",
        "volatile_runtime_unstable",
        "max_total_content_bytes_exceeded",
    }

    known_policy_reasons = (
        discovery_exclusion_reasons
        | projection_exclusion_reasons
    )

    known_policy_events = sum(
        count
        for reason, count in skip_reason_counts.items()
        if reason in known_policy_reasons
    )

    unknown_skip_events = sum(
        count
        for reason, count in skip_reason_counts.items()
        if reason not in known_policy_reasons
    )

    projection_denominator = max(
        1,
        included_files + projected_excluded,
    )

    projection_score = (
        included_files / projection_denominator
    )

    discovery_integrity_score = max(
        0.0,
        1.0 - hard_failures / max(1, files_seen),
    )

    projection_accounted = (
        projected_included + projected_excluded
    )

    projection_accounting_valid = (
        projected_included == included_files
        and projection_accounted == projected_total
    )

    capability_dimensions = {
        "git_provenance": (
            1.0
            if evidence.get("git")
            else 0.0
        ),
        "dependency_evidence": (
            1.0
            if evidence.get(
                "dependencies", {}
            ).get("files")
            else 0.0
        ),
        "runtime_processes": (
            1.0
            if evidence.get(
                "runtime", {}
            ).get(
                "processes", {}
            ).get("available")
            else 0.0
        ),
        "runtime_listeners": (
            1.0
            if evidence.get(
                "runtime", {}
            ).get(
                "listeners", {}
            ).get("available")
            else 0.0
        ),
        "toolchain": (
            1.0
            if any(
                value.get("available")
                for value in evidence.get(
                    "tools", {}
                ).values()
            )
            else 0.0
        ),
        "secret_safe_environment": 1.0,
    }

    capability_score = (
        sum(capability_dimensions.values())
        / len(capability_dimensions)
    )

    # Preserve the historical collection-health score.
    legacy_source_projection = (
        included_files / max(1, files_seen)
    )

    legacy_dimensions = {
        "source_projection":
            legacy_source_projection,
        "scan_integrity":
            discovery_integrity_score,
        **capability_dimensions,
    }

    legacy_score = (
        sum(legacy_dimensions.values())
        / len(legacy_dimensions)
    )

    accounting_warnings = []

    if projected_included != included_files:
        accounting_warnings.append(
            "projection included-record count "
            "does not equal stats.included_files"
        )

    if hard_failures != len(projection.failures):
        accounting_warnings.append(
            "stats.failures does not equal "
            "projection failure-ledger length"
        )

    if unknown_skip_events:
        accounting_warnings.append(
            f"{unknown_skip_events} skip events "
            "have unclassified reasons"
        )

    return {
        # Compatibility surface.
        "score": round(legacy_score, 6),
        "dimensions": {
            key: round(value, 6)
            for key, value
            in legacy_dimensions.items()
        },

        "schema": "savant.sdump.coverage.v3",

        "discovery": {
            "files_seen": files_seen,
            "hard_failures": hard_failures,
            "integrity_score": round(
                discovery_integrity_score,
                6,
            ),
        },

        "projection": {
            "candidate_records": projected_total,
            "included_records": projected_included,
            "excluded_records": projected_excluded,
            "capture_score": round(
                projection_score,
                6,
            ),
            "excluded_by_reason": dict(
                sorted(
                    record_reason_counts.items()
                )
            ),
        },

        "policy": {
            "skip_events": len(
                projection.skipped
            ),
            "known_policy_events":
                known_policy_events,
            "unknown_skip_events":
                unknown_skip_events,
            "skip_events_by_reason": dict(
                sorted(
                    skip_reason_counts.items()
                )
            ),
            "note": (
                "skip events are a diagnostic "
                "ledger and are not a partition "
                "of files_seen"
            ),
        },

        "failures": {
            "count": len(
                projection.failures
            ),
            "by_reason": dict(
                sorted(
                    failure_reason_counts.items()
                )
            ),
        },

        "volatile_runtime": {
            "unstable_files": int(
                skip_reason_counts.get(
                    "volatile_runtime_unstable",
                    0,
                )
            ),
            "policy": (
                "bounded stable-read retries; "
                "persistent volatility is "
                "recorded explicitly rather "
                "than silently discarded"
            ),
        },

        "capabilities": {
            "score": round(
                capability_score,
                6,
            ),
            "dimensions": {
                key: round(value, 6)
                for key, value
                in capability_dimensions.items()
            },
        },

        "accounting": {
            "projection_invariant_valid":
                projection_accounting_valid,
            "warnings":
                accounting_warnings,
        },

        "meaning": (
            "collection and evidence coverage; "
            "not a software quality score. "
            "Discovery, projection, policy "
            "dispositions, integrity, and "
            "collector capabilities use "
            "explicitly separate populations."
        ),
    }

def collect_audit_evidence(targets: list[Path], projection: Projection, validation: bool = False) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": AUDIT_SCHEMA, "collected_at": now_iso(), "targets": [str(p) for p in targets],
        "host": collect_host(), "environment": collect_environment(), "tools": collect_tools(),
        "git": collect_git(targets), "dependencies": collect_dependency_files(targets),
        "oversize_fingerprints": collect_oversize_fingerprints(projection, targets),
        "runtime": {"processes": collect_processes(), "listeners": collect_listeners()},
        "python_environment": collect_python_packages(), "validation": collect_validation(targets, validation),
        "projection": _projection_inventory(projection),
        "security": {"secret_values_captured": False, "credential_files_read": False, "commands_mutating": False},
    }
    stable = {k: v for k, v in evidence.items() if k not in {"collected_at", "evidence_hash", "coverage"}}
    evidence["evidence_hash"] = stable_hash(stable)
    evidence["coverage"] = _coverage(projection, evidence)
    return evidence


def compare_evidence(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    def filemap(doc: Mapping[str, Any]) -> dict[str, str | None]:
        records = doc.get("projection", {}).get("included", [])
        return {str(r.get("path")): r.get("source_sha256") for r in records if isinstance(r, dict) and r.get("path")}
    old, new = filemap(previous), filemap(current)
    added = sorted(set(new) - set(old)); removed = sorted(set(old) - set(new))
    changed = sorted(path for path in set(old) & set(new) if old[path] != new[path])
    unchanged = len(set(old) & set(new)) - len(changed)
    return {"schema": "savant.sdump.audit-delta.v1", "previous_evidence_hash": previous.get("evidence_hash"),
            "current_evidence_hash": current.get("evidence_hash"), "added": added, "removed": removed,
            "changed": changed, "unchanged_count": unchanged,
            "delta_hash": stable_hash({"added": added, "removed": removed, "changed": changed, "unchanged_count": unchanged})}


def write_audit_sidecars(root: Path, evidence: Mapping[str, Any], delta: Mapping[str, Any] | None = None) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    metadata = root / "metadata"; diagnostics = root / "diagnostics"
    metadata.mkdir(exist_ok=True); diagnostics.mkdir(exist_ok=True)
    paths = {
        "evidence": metadata / "evidence.json", "files": metadata / "files.jsonl", "git": metadata / "git.json",
        "environment": metadata / "environment.json", "dependencies": metadata / "dependencies.json",
        "runtime": diagnostics / "runtime.json", "validation": diagnostics / "validation.json", "summary": root / "SUMMARY.md",
    }
    atomic_write_json(paths["evidence"], dict(evidence)); atomic_write_json(paths["git"], {"git": evidence.get("git", [])})
    atomic_write_json(paths["environment"], {"host": evidence.get("host"), "environment": evidence.get("environment"), "tools": evidence.get("tools")})
    atomic_write_json(paths["dependencies"], dict(evidence.get("dependencies", {})))
    atomic_write_json(paths["runtime"], dict(evidence.get("runtime", {}))); atomic_write_json(paths["validation"], dict(evidence.get("validation", {})))
    file_lines = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in evidence.get("projection", {}).get("included", []))
    atomic_write_text(paths["files"], file_lines)
    if delta is not None:
        paths["delta"] = metadata / "delta.json"; atomic_write_json(paths["delta"], dict(delta))
    coverage = evidence.get("coverage", {})
    projection_coverage = coverage.get("projection", {})
    discovery_coverage = coverage.get("discovery", {})
    capability_coverage = coverage.get("capabilities", {})
    policy_coverage = coverage.get("policy", {})
    accounting = coverage.get("accounting", {})

    summary = [
        "# sdump audit",
        "",
        f"- schema: `{evidence.get('schema')}`",
        f"- evidence hash: `{evidence.get('evidence_hash')}`",
        (
            "- projection snapshot: "
            f"`{evidence.get('projection', {}).get('snapshot_hash')}`"
        ),
        f"- legacy collection coverage: `{coverage.get('score')}`",
        (
            "- projection capture: "
            f"`{projection_coverage.get('capture_score')}`"
        ),
        (
            "- scan integrity: "
            f"`{discovery_coverage.get('integrity_score')}`"
        ),
        (
            "- capability coverage: "
            f"`{capability_coverage.get('score')}`"
        ),
        (
            "- projection accounting: "
            + (
                "`valid`"
                if accounting.get(
                    "projection_invariant_valid"
                )
                else "`WARNING`"
            )
        ),
        (
            "- targets: "
            + ", ".join(
                evidence.get("targets", [])
            )
        ),
        "",
        "## coverage intelligence",
        "",
        (
            "- discovered filesystem entries: "
            f"{discovery_coverage.get('files_seen', 0)}"
        ),
        (
            "- authoritative candidate records: "
            f"{projection_coverage.get('candidate_records', 0)}"
        ),
        (
            "- included candidate records: "
            f"{projection_coverage.get('included_records', 0)}"
        ),
        (
            "- excluded candidate records: "
            f"{projection_coverage.get('excluded_records', 0)}"
        ),
        (
            "- policy/diagnostic skip events: "
            f"{policy_coverage.get('skip_events', 0)}"
        ),
        (
            "- unclassified skip events: "
            f"{policy_coverage.get('unknown_skip_events', 0)}"
        ),
        (
            "- hard failures: "
            f"{discovery_coverage.get('hard_failures', 0)}"
        ),
        "",
        "### policy dispositions",
        "",
    ]

    skip_reasons = policy_coverage.get(
        "skip_events_by_reason", {}
    )

    if skip_reasons:
        for reason, count in sorted(
            skip_reasons.items()
        ):
            summary.append(
                f"- `{reason}`: {count}"
            )
    else:
        summary.append("- none")

    warnings = accounting.get(
        "warnings", []
    )

    summary += [
        "",
        "### accounting warnings",
        "",
    ]

    if warnings:
        for warning in warnings:
            summary.append(
                f"- WARNING: {warning}"
            )
    else:
        summary.append("- none")

    summary += [
        "",
        "## guarantees",
        "",
        (
            "- source projection remains "
            "content-addressed and deduplicated"
        ),
        (
            "- environment secret-like values "
            "are never captured"
        ),
        (
            "- evidence commands are read-only "
            "and bounded"
        ),
        (
            "- skipped and oversized material "
            "remains explicitly represented"
        ),
        (
            "- discovery, projection, skip-event, "
            "and failure populations are "
            "accounted separately"
        ),
        "",
    ]
    if delta is not None:
        summary += ["## delta", "", f"- added: {len(delta.get('added', []))}", f"- removed: {len(delta.get('removed', []))}",
                    f"- changed: {len(delta.get('changed', []))}", f"- unchanged: {delta.get('unchanged_count', 0)}", ""]
    atomic_write_text(paths["summary"], "\n".join(summary))
    return {key: str(path) for key, path in paths.items()}


def load_previous_evidence(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def archive_audit_directory(root: Path) -> Path:
    destination = root.with_suffix(".tar.gz")
    base = str(destination)[:-7] if str(destination).endswith(".tar.gz") else str(destination)
    made = shutil.make_archive(base, "gztar", root_dir=root.parent, base_dir=root.name)
    return Path(made)
