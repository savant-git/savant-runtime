#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
from primitives import write_json


SCHEMA_ID = "savant://assurance/structure-intelligence/1.0.0"
DEFAULT_ROOT = Path("/root/savant-runtime")
DEFAULT_OUTPUT_ROOT = DEFAULT_ROOT / "assurance/structure-intelligence"

IDENTITY_LEVELS = (
    "iota",
    "mote",
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "portal",
    "obelisk",
)

IDENTITY_COMPATIBILITY = {
    "shard": "mote",
    "gate": "portal",
}

CONTENT_LEVELS = (
    "character",
    "line",
    "snippet",
    "script",
    "module",
    "service",
    "application",
    "suite",
    "estate",
)

MOODS = (
    "anima",
    "weld",
    "kiln",
    "graft",
    "aria",
    "mantle",
    "fulcrum",
    "echelon",
    "ascent",
)

KINDRED_TREES = (
    "structural",
    "semantic",
    "rubric",
    "authority",
    "composition",
    "dependency",
    "provenance",
    "succession",
    "compatibility",
)

KINDRED_COORDINATES = (
    "generation",
    "collateral",
    "affinity",
    "authority",
    "dependency",
    "composition",
    "temporal",
    "provenance",
    "compatibility",
)

RUBRIC_FACILITIES = (
    "source",
    "contracts",
    "schemas",
    "adapters",
    "commands",
    "tests",
    "migrations",
    "tasks",
    "receipts",
)

CABAL_LAWS = (
    "chorus",
    "commons",
    "covenant",
    "equinox",
    "gauntlet",
    "distillate",
    "severance",
    "cascade",
    "bridge",
)

SOURCE_SUFFIXES = {
    ".py",
    ".pyi",
    ".pyx",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".rs",
    ".go",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".java",
    ".kt",
    ".kts",
    ".swift",
    ".rb",
    ".php",
    ".pl",
    ".lua",
    ".cue",
    ".rego",
    ".sql",
    ".proto",
    ".graphql",
    ".gql",
}

STRUCTURED_SUFFIXES = {
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".schema",
}

DOCUMENT_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
}

KNOWN_FILENAMES = {
    "Makefile",
    "Dockerfile",
    "Containerfile",
    "Procfile",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
    ".gitignore",
    ".dockerignore",
    ".env.example",
    ".env.sample",
}

PRUNED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    "site-packages",
    "dist",
    "build",
    "cache",
    "tmp",
    "temp",
    "logs",
}

PRUNED_RELATIVE_PREFIXES = (
    "audit/",
    "assurance/structure-intelligence/",
    "backups/",
    "vault/backups/",
    "imports/savant-runtime-2-conflicts/",
)

BINARY_SUFFIXES = {
    ".zip",
    ".tar",
    ".gz",
    ".zst",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp3",
    ".wav",
    ".flac",
    ".mp4",
    ".mkv",
    ".mov",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".pyc",
    ".pyo",
}

IMPORT_PATTERNS = (
    re.compile(r"""(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)"""),
    re.compile(r"""require\(\s*["']([^"']+)["']\s*\)"""),
    re.compile(r"""from\s+["']([^"']+)["']"""),
    re.compile(r"""import\(\s*["']([^"']+)["']\s*\)"""),
    re.compile(r"""#include\s*[<"]([^>"]+)[>"]"""),
)

PATH_PATTERNS = (
    re.compile(r"""(?:/root/savant-runtime|savant-runtime)/[A-Za-z0-9_./-]+"""),
    re.compile(r"""(?:\.\.?/)+[A-Za-z0-9_./-]+"""),
)

INSTANCE_MARKERS = (
    "instance.yaml",
    "instance.yml",
    "instance.json",
    "entity.json",
    "module.json",
)

AUTHORITY_MARKERS = (
    "authority",
    "accepted-decisions",
    "constitution",
    "canon",
)

PROJECTION_MARKERS = (
    "projection",
    "projections",
    "generated",
    "report",
    "reports",
    "view",
    "views",
)

RUNTIME_MARKERS = (
    "runtime",
    "queue",
    "queues",
    "session",
    "sessions",
    "cache",
    "state",
    "transactions",
    "events",
)

HISTORY_MARKERS = (
    "history",
    "archive",
    "archives",
    "legacy",
    "deprecated",
    "relics",
)

ASSURANCE_MARKERS = (
    "test",
    "tests",
    "audit",
    "validation",
    "verification",
    "observatory",
    "diagnostics",
    "assurance",
)

RUBRIC_HINTS = (
    "rubric",
    "apps",
    "app",
    "engine",
    "engines",
    "service",
    "services",
    "module",
    "modules",
    "src",
    "source",
)

CABAL_HINTS = (
    "cabal",
    "shared",
    "common",
    "commons",
    "utilities",
    "utility",
    "lib",
    "libs",
    "library",
    "libraries",
)


@dataclass(frozen=True, slots=True)
class FileRecord:
    relative_path: str
    absolute_path: str
    suffix: str
    artifact_kind: str
    size: int
    mode: str
    sha256: str
    symlink_target: str | None
    semantic_owner: str | None
    owner_confidence: float
    authority_state: str
    projection_state: str
    history_state: str
    edifice_level: str | None
    rubric_candidate: str | None
    rubric_confidence: float
    cabal_candidate: str | None
    cabal_confidence: float
    instance_candidate: str | None
    moods: tuple[str, ...]
    kindred_terms: tuple[str, ...]
    imports: tuple[str, ...]
    path_references: tuple[str, ...]
    parse_error: str | None


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    source: str
    target: str
    edge_kind: str
    confidence: float


@dataclass(slots=True)
class Analysis:
    root: str
    generated_at: str
    files: list[FileRecord] = field(default_factory=list)
    dependencies: list[DependencyEdge] = field(default_factory=list)
    duplicate_groups: list[dict[str, Any]] = field(default_factory=list)
    rubric_candidates: list[dict[str, Any]] = field(default_factory=list)
    cabal_candidates: list[dict[str, Any]] = field(default_factory=list)
    instance_candidates: list[dict[str, Any]] = field(default_factory=list)
    edifice_findings: list[dict[str, Any]] = field(default_factory=list)
    mood_findings: list[dict[str, Any]] = field(default_factory=list)
    kindred_findings: list[dict[str, Any]] = field(default_factory=list)
    ownership_conflicts: list[dict[str, Any]] = field(default_factory=list)
    migration_candidates: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_link(path: Path) -> str:
    target = os.readlink(path)
    return hashlib.sha256(f"link:{target}".encode("utf-8")).hexdigest()


def is_pruned_relative(relative: str) -> bool:
    normalized = relative.replace("\\", "/")

    return any(
        normalized == prefix.rstrip("/")
        or normalized.startswith(prefix)
        for prefix in PRUNED_RELATIVE_PREFIXES
    )


def is_relevant(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return False

    if path.name.startswith("sdump_"):
        return False

    if path.name.startswith("current_runtime_source_dump_"):
        return False

    if path.name in KNOWN_FILENAMES:
        return True

    suffix = path.suffix.lower()

    if suffix in SOURCE_SUFFIXES | STRUCTURED_SUFFIXES:
        return True

    if suffix in DOCUMENT_SUFFIXES:
        lowered_parts = {part.lower() for part in path.parts}

        return bool(
            lowered_parts.intersection(
                {
                    "docs",
                    "canon",
                    "authority",
                    "context",
                    "lexicon",
                    "contracts",
                    "tasks",
                    "migrations",
                    "history",
                }
            )
        )

    return False


def iter_relevant_paths(root: Path, maximum: int) -> Iterator[Path]:
    emitted = 0

    for current_root, directories, filenames in os.walk(root):
        current = Path(current_root)
        relative_root = current.relative_to(root).as_posix()

        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in PRUNED_NAMES
            and not is_pruned_relative(
                (
                    Path(relative_root) / directory
                    if relative_root != "."
                    else Path(directory)
                ).as_posix()
            )
        )

        for filename in sorted(filenames):
            path = current / filename
            relative = path.relative_to(root).as_posix()

            if is_pruned_relative(relative):
                continue

            if not is_relevant(path):
                continue

            emitted += 1

            if emitted > maximum:
                raise RuntimeError(
                    f"relevant-file ceiling exceeded: {maximum}"
                )

            yield path


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name

    if suffix in SOURCE_SUFFIXES:
        return "source"

    if suffix in STRUCTURED_SUFFIXES:
        if "schema" in name.lower() or "schemas" in path.parts:
            return "schema"
        if "manifest" in name.lower():
            return "manifest"
        return "structured-record"

    if suffix in DOCUMENT_SUFFIXES:
        lowered_parts = {part.lower() for part in path.parts}

        if lowered_parts.intersection(
            {
                "docs",
                "canon",
                "authority",
                "context",
                "lexicon",
                "contracts",
                "tasks",
                "migrations",
                "history",
            }
        ):
            return "document"

        return "other"

    if name.endswith((".service", ".timer", ".socket", ".target", ".path")):
        return "service-unit"

    if name in KNOWN_FILENAMES:
        return "environment"

    return "other"


def path_tokens(relative: str) -> tuple[str, ...]:
    tokens: list[str] = []

    for part in Path(relative).parts:
        tokens.extend(
            token.lower()
            for token in re.split(r"[^A-Za-z0-9]+", part)
            if token
        )

    return tuple(tokens)


def classify_authority(tokens: Sequence[str]) -> str:
    token_set = set(tokens)

    if "accepted" in token_set and "decisions" in token_set:
        return "accepted-authority"

    if token_set.intersection(AUTHORITY_MARKERS):
        return "authority-candidate"

    return "non-authority"


def classify_projection(tokens: Sequence[str]) -> str:
    return (
        "projection-candidate"
        if set(tokens).intersection(PROJECTION_MARKERS)
        else "non-projection"
    )


def classify_history(tokens: Sequence[str]) -> str:
    return (
        "historical-candidate"
        if set(tokens).intersection(HISTORY_MARKERS)
        else "current-candidate"
    )


def identify_edifice_level(tokens: Sequence[str]) -> str | None:
    token_set = set(tokens)

    for level in reversed(IDENTITY_LEVELS):
        if level in token_set or f"{level}s" in token_set:
            return level

    for legacy, canonical in IDENTITY_COMPATIBILITY.items():
        if legacy in token_set or f"{legacy}s" in token_set:
            return canonical

    for level in reversed(CONTENT_LEVELS):
        if level in token_set or f"{level}s" in token_set:
            return level

    return None

def infer_owner(relative: str) -> tuple[str | None, float]:
    parts = Path(relative).parts
    lowered = tuple(part.lower() for part in parts)

    owner_markers = {
        "obelisks": 1,
        "portals": 2,
        "gates": 2,
        "innates": 3,
        "exiles": 4,
        "prodigals": 5,
        "quirks": 6,
        "traits": 7,
        "motes": 8,
        "shards": 8,
        "iotas": 9,
        "estates": 1,
        "suites": 2,
        "applications": 3,
        "services": 4,
        "modules": 5,
        "scripts": 6,
        "snippets": 7,
        "lines": 8,
        "characters": 9,
    }

    candidates: list[tuple[int, int, str]] = []

    for index, part in enumerate(lowered[:-1]):
        depth = owner_markers.get(part)

        if depth is None or index + 1 >= len(parts):
            continue

        candidate = parts[index + 1]

        if candidate.startswith("_") or candidate == "segue":
            continue

        candidates.append((depth, index, candidate))

    if candidates:
        depth, _, candidate = max(
            candidates,
            key=lambda item: (item[0], item[1]),
        )

        return candidate, min(0.99, 0.90 + (depth * 0.01))

    canonical_exiles = (
        "niche",
        "opus",
        "notary",
        "pact",
        "modus",
        "underscore",
        "shatter",
        "palaver",
        "envoy",
    )

    for marker in canonical_exiles:
        if marker in lowered:
            return marker, 0.90

    if not lowered:
        return None, 0.0

    root = lowered[0]

    root_owners = {
        "authority": "savant-runtime",
        "authority_graph": "savant-runtime",
        "assurance": "savant-runtime",
        "canon": "savant-runtime",
        "canon-system": "savant-runtime",
        "context": "savant-runtime",
        "docs": "savant-runtime",
        "evolution": "savant-runtime",
        "frontend": "savant-runtime",
        "imports": "savant-runtime",
        "lexicon": "savant-runtime",
        "migrations": "savant-runtime",
        "ontology": "ontology",
        "port": "savant-runtime",
        "present": "savant-runtime",
        "reports": "savant-runtime",
        "runtime": "savant-runtime",
        "scripts": "savant-runtime",
        "tests": "savant-runtime",
        "tools": "savant-runtime",
        "vault": "savant-runtime",
    }

    if root in root_owners:
        return root_owners[root], 0.70

    return None, 0.0

def nearest_named_scope(
    relative: str,
    hints: Sequence[str],
) -> tuple[str | None, float]:
    path = Path(relative)
    parts = path.parts

    for index in range(len(parts) - 2, -1, -1):
        part = parts[index]
        normalized = part.lower()

        if normalized in hints:
            if index + 1 < len(parts) - 1:
                return "/".join(parts[: index + 2]), 0.92

            return "/".join(parts[: index + 1]), 0.80

    return None, 0.0


def probable_rubric(
    relative: str,
    kind: str,
    owner: str | None,
) -> tuple[str | None, float]:
    if kind not in {
        "source",
        "schema",
        "manifest",
        "service-unit",
        "environment",
    }:
        return None, 0.0

    explicit, confidence = nearest_named_scope(relative, ("rubric",))

    if explicit:
        return explicit, 1.0

    inferred, inferred_confidence = nearest_named_scope(
        relative,
        RUBRIC_HINTS,
    )

    if inferred:
        return inferred, inferred_confidence

    if owner:
        return f"owner:{owner}:unresolved-rubric", 0.45

    return None, 0.0


def probable_cabal(
    relative: str,
    kind: str,
) -> tuple[str | None, float]:
    if kind not in {
        "source",
        "schema",
        "manifest",
        "service-unit",
        "environment",
    }:
        return None, 0.0

    explicit, _ = nearest_named_scope(relative, ("cabal",))

    if explicit:
        return explicit, 1.0

    inferred, confidence = nearest_named_scope(relative, CABAL_HINTS)

    if inferred:
        return inferred, min(confidence, 0.65)

    return None, 0.0


def identify_instance(relative: str) -> str | None:
    path = Path(relative)

    if path.name.lower() in INSTANCE_MARKERS:
        return path.parent.as_posix()

    parts = tuple(part.lower() for part in path.parts)

    for marker in (
        "obelisks",
        "portals",
        "gates",
        "innates",
        "exiles",
        "prodigals",
        "quirks",
        "traits",
        "motes",
        "shards",
        "iotas",
        "estates",
        "suites",
        "applications",
        "services",
        "modules",
        "scripts",
        "snippets",
        "lines",
        "characters",
    ):
        if marker not in parts:
            continue

        index = parts.index(marker)

        if index + 1 >= len(path.parts):
            continue

        candidate = path.parts[index + 1]

        if candidate.startswith("_") or candidate == "segue":
            continue

        return "/".join(path.parts[: index + 2])

    return None


def read_text(path: Path, maximum_bytes: int) -> tuple[str, str | None]:
    try:
        size = path.stat().st_size

        if size > maximum_bytes:
            return "", f"size-ceiling:{size}"

        return path.read_text(encoding="utf-8", errors="replace"), None

    except OSError as exc:
        return "", f"{type(exc).__name__}:{exc}"


def parse_python_imports(text: str) -> tuple[set[str], str | None]:
    imports: set[str] = set()

    try:
        tree = ast.parse(text)

    except SyntaxError as exc:
        return imports, f"SyntaxError:{exc.lineno}:{exc.offset}:{exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports, None


def extract_references(
    path: Path,
    text: str,
) -> tuple[tuple[str, ...], tuple[str, ...], str | None]:
    imports: set[str] = set()
    paths: set[str] = set()
    parse_error: str | None = None

    if path.suffix.lower() == ".py":
        imports, parse_error = parse_python_imports(text)

    else:
        for pattern in IMPORT_PATTERNS:
            imports.update(
                match.group(1)
                for match in pattern.finditer(text)
            )

    for pattern in PATH_PATTERNS:
        paths.update(match.group(0) for match in pattern.finditer(text))

    return (
        tuple(sorted(imports)),
        tuple(sorted(paths)),
        parse_error,
    )


def find_moods(text: str, tokens: Sequence[str]) -> tuple[str, ...]:
    haystack = f"{' '.join(tokens)} {text[:250000]}".lower()

    return tuple(
        mood
        for mood in MOODS
        if re.search(rf"\b{re.escape(mood)}\b", haystack)
    )


def find_kindred_terms(text: str, tokens: Sequence[str]) -> tuple[str, ...]:
    terms = set(KINDRED_TREES) | set(KINDRED_COORDINATES) | {
        "kindred",
        "parent",
        "child",
        "mother",
        "father",
        "daughter",
        "son",
        "sibling",
        "sister",
        "brother",
        "grandparent",
        "grandchild",
        "aunt",
        "uncle",
        "pibling",
        "nibling",
        "niece",
        "nephew",
        "cousin",
        "spouse",
        "guardian",
        "ward",
        "ancestor",
        "descendant",
        "predecessor",
        "successor",
    }

    haystack = f"{' '.join(tokens)} {text[:250000]}".lower()

    return tuple(
        term
        for term in sorted(terms)
        if re.search(rf"\b{re.escape(term)}\b", haystack)
    )


def build_record(
    root: Path,
    path: Path,
    maximum_text_bytes: int,
) -> FileRecord:
    relative = path.relative_to(root).as_posix()
    tokens = path_tokens(relative)
    kind = artifact_kind(path)
    owner, owner_confidence = infer_owner(relative)
    rubric, rubric_confidence = probable_rubric(
        relative,
        kind,
        owner,
    )
    cabal, cabal_confidence = probable_cabal(relative, kind)
    symlink_target: str | None = None

    if path.is_symlink():
        symlink_target = os.readlink(path)
        digest = sha256_link(path)
        size = len(symlink_target.encode("utf-8"))
        text = ""
        read_error = None

    else:
        digest = sha256_file(path)
        size = path.stat().st_size
        text, read_error = read_text(path, maximum_text_bytes)

    imports, references, parse_error = extract_references(path, text)

    if parse_error is None:
        parse_error = read_error

    mode = stat.filemode(path.lstat().st_mode)

    return FileRecord(
        relative_path=relative,
        absolute_path=str(path),
        suffix=path.suffix.lower(),
        artifact_kind=kind,
        size=size,
        mode=mode,
        sha256=digest,
        symlink_target=symlink_target,
        semantic_owner=owner,
        owner_confidence=owner_confidence,
        authority_state=classify_authority(tokens),
        projection_state=classify_projection(tokens),
        history_state=classify_history(tokens),
        edifice_level=identify_edifice_level(tokens),
        rubric_candidate=rubric,
        rubric_confidence=rubric_confidence,
        cabal_candidate=cabal,
        cabal_confidence=cabal_confidence,
        instance_candidate=identify_instance(relative),
        moods=find_moods(text, tokens),
        kindred_terms=find_kindred_terms(text, tokens),
        imports=imports,
        path_references=references,
        parse_error=parse_error,
    )


def path_module_candidates(relative: str) -> set[str]:
    path = Path(relative)
    candidates: set[str] = set()

    if path.suffix.lower() == ".py":
        without_suffix = path.with_suffix("")
        dotted = ".".join(without_suffix.parts)
        candidates.add(dotted)

        if without_suffix.name == "__init__":
            candidates.add(".".join(without_suffix.parent.parts))

        for index in range(len(without_suffix.parts)):
            candidates.add(".".join(without_suffix.parts[index:]))

    return {candidate for candidate in candidates if candidate}


def resolve_dependencies(
    records: Sequence[FileRecord],
) -> list[DependencyEdge]:
    module_index: dict[str, set[str]] = defaultdict(set)
    basename_index: dict[str, set[str]] = defaultdict(set)
    path_index = {record.relative_path: record for record in records}

    for record in records:
        for module in path_module_candidates(record.relative_path):
            module_index[module].add(record.relative_path)

        basename_index[Path(record.relative_path).name].add(
            record.relative_path
        )

    edges: dict[tuple[str, str, str], DependencyEdge] = {}

    for record in records:
        for imported in record.imports:
            targets: set[str] = set()

            for candidate, paths in module_index.items():
                if candidate == imported or candidate.endswith(
                    f".{imported}"
                ):
                    targets.update(paths)

            for target in targets:
                if target == record.relative_path:
                    continue

                key = (record.relative_path, target, "import")

                edges[key] = DependencyEdge(
                    source=record.relative_path,
                    target=target,
                    edge_kind="import",
                    confidence=0.90,
                )

        for reference in record.path_references:
            normalized = reference

            if normalized.startswith("/root/savant-runtime/"):
                normalized = normalized.removeprefix(
                    "/root/savant-runtime/"
                )

            if normalized.startswith("savant-runtime/"):
                normalized = normalized.removeprefix("savant-runtime/")

            normalized = normalized.lstrip("./")

            if normalized in path_index and normalized != record.relative_path:
                key = (record.relative_path, normalized, "path-reference")

                edges[key] = DependencyEdge(
                    source=record.relative_path,
                    target=normalized,
                    edge_kind="path-reference",
                    confidence=0.98,
                )
                continue

            basename = Path(normalized).name

            if not basename:
                continue

            candidates = basename_index.get(basename, set())

            if len(candidates) == 1:
                target = next(iter(candidates))

                if target == record.relative_path:
                    continue

                key = (
                    record.relative_path,
                    target,
                    "basename-reference",
                )

                edges[key] = DependencyEdge(
                    source=record.relative_path,
                    target=target,
                    edge_kind="basename-reference",
                    confidence=0.55,
                )

    return sorted(
        edges.values(),
        key=lambda edge: (
            edge.source,
            edge.target,
            edge.edge_kind,
        ),
    )


def compile_duplicates(
    records: Sequence[FileRecord],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        if record.size == 0:
            continue

        grouped[record.sha256].append(record)

    rows: list[dict[str, Any]] = []

    for digest, group in grouped.items():
        if len(group) < 2:
            continue

        owners = sorted(
            {
                record.semantic_owner
                for record in group
                if record.semantic_owner
            }
        )

        rows.append(
            {
                "sha256": digest,
                "size": group[0].size,
                "count": len(group),
                "owners": owners,
                "cross_owner": len(owners) > 1,
                "paths": sorted(
                    record.relative_path
                    for record in group
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            not row["cross_owner"],
            -row["count"],
            row["sha256"],
        ),
    )


def compile_scope_candidates(
    records: Sequence[FileRecord],
    attribute: str,
    confidence_attribute: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        candidate = getattr(record, attribute)

        if candidate:
            grouped[candidate].append(record)

    rows: list[dict[str, Any]] = []

    for candidate, group in grouped.items():
        owners = sorted(
            {
                record.semantic_owner
                for record in group
                if record.semantic_owner
            }
        )
        confidences = [
            float(getattr(record, confidence_attribute))
            for record in group
        ]

        rows.append(
            {
                "candidate": candidate,
                "file_count": len(group),
                "owners": owners,
                "owner_count": len(owners),
                "confidence": round(
                    sum(confidences) / len(confidences),
                    4,
                ),
                "paths": sorted(
                    record.relative_path
                    for record in group
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -row["confidence"],
            -row["file_count"],
            row["candidate"],
        ),
    )


def compile_instances(
    records: Sequence[FileRecord],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        if record.instance_candidate:
            grouped[record.instance_candidate].append(record)

    rows: list[dict[str, Any]] = []

    for candidate, group in grouped.items():
        levels = sorted(
            {
                record.edifice_level
                for record in group
                if record.edifice_level
            }
        )
        owners = sorted(
            {
                record.semantic_owner
                for record in group
                if record.semantic_owner
            }
        )

        rows.append(
            {
                "instance_candidate": candidate,
                "levels": levels,
                "owners": owners,
                "file_count": len(group),
                "rubrics": sorted(
                    {
                        record.rubric_candidate
                        for record in group
                        if record.rubric_candidate
                    }
                ),
                "cabals": sorted(
                    {
                        record.cabal_candidate
                        for record in group
                        if record.cabal_candidate
                    }
                ),
                "moods": sorted(
                    {
                        mood
                        for record in group
                        for mood in record.moods
                    }
                ),
                "kindred_terms": sorted(
                    {
                        term
                        for record in group
                        for term in record.kindred_terms
                    }
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: row["instance_candidate"],
    )


def compile_edifice_findings(
    records: Sequence[FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    counts = Counter(
        record.edifice_level
        for record in records
        if record.edifice_level
    )

    for level in IDENTITY_LEVELS:
        rows.append(
            {
                "edifice": "identity",
                "level": level,
                "file_count": counts[level],
                "status": (
                    "observed"
                    if counts[level]
                    else "not-observed-in-relevant-scope"
                ),
            }
        )

    for level in CONTENT_LEVELS:
        rows.append(
            {
                "edifice": "content",
                "level": level,
                "file_count": counts[level],
                "status": (
                    "observed"
                    if counts[level]
                    else "not-observed-in-relevant-scope"
                ),
            }
        )

    legacy_counts = Counter()

    for record in records:
        tokens = set(path_tokens(record.relative_path))

        for legacy in IDENTITY_COMPATIBILITY:
            if legacy in tokens or f"{legacy}s" in tokens:
                legacy_counts[legacy] += 1

    for legacy, canonical in IDENTITY_COMPATIBILITY.items():
        rows.append(
            {
                "edifice": "identity-compatibility",
                "level": legacy,
                "canonical": canonical,
                "file_count": legacy_counts[legacy],
                "status": "requires-semantic-classification",
            }
        )

    return rows


def compile_mood_findings(
    records: Sequence[FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for mood in MOODS:
        paths = sorted(
            record.relative_path
            for record in records
            if mood in record.moods
        )

        rows.append(
            {
                "mood": mood,
                "file_count": len(paths),
                "paths": paths,
            }
        )

    return rows


def compile_kindred_findings(
    records: Sequence[FileRecord],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    terms = sorted(
        {
            term
            for record in records
            for term in record.kindred_terms
        }
    )

    for term in terms:
        paths = sorted(
            record.relative_path
            for record in records
            if term in record.kindred_terms
        )

        rows.append(
            {
                "term": term,
                "file_count": len(paths),
                "paths": paths,
            }
        )

    return rows


def compile_ownership_conflicts(
    records: Sequence[FileRecord],
    duplicate_groups: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for record in records:
        if record.artifact_kind == "source" and not record.semantic_owner:
            rows.append(
                {
                    "kind": "unresolved-source-owner",
                    "path": record.relative_path,
                    "severity": "blocker",
                }
            )

        if (
            record.rubric_candidate
            and record.cabal_candidate
            and record.rubric_confidence >= 0.80
            and record.cabal_confidence >= 0.80
        ):
            rows.append(
                {
                    "kind": "rubric-cabal-ambiguity",
                    "path": record.relative_path,
                    "rubric": record.rubric_candidate,
                    "cabal": record.cabal_candidate,
                    "severity": "blocker",
                }
            )

    for group in duplicate_groups:
        if group["cross_owner"]:
            rows.append(
                {
                    "kind": "cross-owner-identical-substance",
                    "sha256": group["sha256"],
                    "paths": group["paths"],
                    "owners": group["owners"],
                    "severity": "review",
                }
            )

    return sorted(
        rows,
        key=lambda row: (
            row.get("severity", ""),
            row.get("kind", ""),
            row.get("path", ""),
            row.get("sha256", ""),
        ),
    )


def proposed_destination(record: FileRecord) -> str | None:
    if record.authority_state in {
        "accepted-authority",
        "authority-candidate",
    }:
        return None

    if record.history_state == "historical-candidate":
        return None

    if record.projection_state == "projection-candidate":
        return None

    if record.cabal_candidate and record.cabal_confidence >= 0.80:
        return record.cabal_candidate

    if record.rubric_candidate and record.rubric_confidence >= 0.80:
        return record.rubric_candidate

    return None


def compile_migration_candidates(
    records: Sequence[FileRecord],
    reverse_dependencies: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for record in records:
        destination_scope = proposed_destination(record)

        if not destination_scope:
            continue

        current_parent = Path(record.relative_path).parent.as_posix()

        if current_parent == destination_scope:
            continue

        rows.append(
            {
                "stable_id": f"artifact:sha256:{record.sha256}",
                "current_path": record.relative_path,
                "candidate_scope": destination_scope,
                "artifact_kind": record.artifact_kind,
                "semantic_owner": record.semantic_owner,
                "owner_confidence": record.owner_confidence,
                "rubric_candidate": record.rubric_candidate,
                "rubric_confidence": record.rubric_confidence,
                "cabal_candidate": record.cabal_candidate,
                "cabal_confidence": record.cabal_confidence,
                "authority_state": record.authority_state,
                "projection_state": record.projection_state,
                "history_state": record.history_state,
                "source_sha256": record.sha256,
                "dependents": reverse_dependencies.get(
                    record.relative_path,
                    [],
                ),
                "migration_action": "unresolved",
                "rollback_action": "restore-original-path",
                "authorized": False,
                "mutation_performed": False,
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -max(
                row["rubric_confidence"],
                row["cabal_confidence"],
            ),
            row["current_path"],
        ),
    )


def compile_analysis(
    root: Path,
    maximum_files: int,
    maximum_text_bytes: int,
) -> Analysis:
    analysis = Analysis(
        root=str(root),
        generated_at=utc_now(),
    )

    for path in iter_relevant_paths(root, maximum_files):
        analysis.files.append(
            build_record(root, path, maximum_text_bytes)
        )

    analysis.dependencies = resolve_dependencies(analysis.files)
    analysis.duplicate_groups = compile_duplicates(analysis.files)
    analysis.rubric_candidates = compile_scope_candidates(
        analysis.files,
        "rubric_candidate",
        "rubric_confidence",
    )
    analysis.cabal_candidates = compile_scope_candidates(
        analysis.files,
        "cabal_candidate",
        "cabal_confidence",
    )
    analysis.instance_candidates = compile_instances(analysis.files)
    analysis.edifice_findings = compile_edifice_findings(
        analysis.files
    )
    analysis.mood_findings = compile_mood_findings(analysis.files)
    analysis.kindred_findings = compile_kindred_findings(analysis.files)
    analysis.ownership_conflicts = compile_ownership_conflicts(
        analysis.files,
        analysis.duplicate_groups,
    )

    reverse_dependencies: dict[str, list[str]] = defaultdict(list)

    for edge in analysis.dependencies:
        reverse_dependencies[edge.target].append(edge.source)

    for target in reverse_dependencies:
        reverse_dependencies[target] = sorted(
            set(reverse_dependencies[target])
        )

    analysis.migration_candidates = compile_migration_candidates(
        analysis.files,
        reverse_dependencies,
    )

    parse_errors = [
        record
        for record in analysis.files
        if record.parse_error
    ]
    unresolved_owners = [
        record
        for record in analysis.files
        if record.artifact_kind == "source"
        and not record.semantic_owner
    ]
    probable_cabals = [
        row
        for row in analysis.cabal_candidates
        if row["owner_count"] >= 2
        and row["confidence"] >= 0.60
    ]

    analysis.summary = {
        "schema": SCHEMA_ID,
        "mutation_performed": False,
        "migration_authorized": False,
        "file_count": len(analysis.files),
        "source_count": sum(
            record.artifact_kind == "source"
            for record in analysis.files
        ),
        "structured_record_count": sum(
            record.artifact_kind
            in {"structured-record", "schema", "manifest"}
            for record in analysis.files
        ),
        "dependency_edge_count": len(analysis.dependencies),
        "duplicate_group_count": len(analysis.duplicate_groups),
        "cross_owner_duplicate_group_count": sum(
            bool(group["cross_owner"])
            for group in analysis.duplicate_groups
        ),
        "rubric_candidate_count": len(analysis.rubric_candidates),
        "cabal_candidate_count": len(analysis.cabal_candidates),
        "probable_multi_owner_cabal_count": len(probable_cabals),
        "instance_candidate_count": len(analysis.instance_candidates),
        "ownership_conflict_count": len(analysis.ownership_conflicts),
        "migration_candidate_count": len(analysis.migration_candidates),
        "parse_error_count": len(parse_errors),
        "unresolved_source_owner_count": len(unresolved_owners),
    }

    return analysis


def analysis_to_mapping(analysis: Analysis) -> dict[str, Any]:
    return {
        "schema": SCHEMA_ID,
        "root": analysis.root,
        "generated_at": analysis.generated_at,
        "mutation_performed": False,
        "migration_authorized": False,
        "summary": analysis.summary,
        "files": [asdict(record) for record in analysis.files],
        "dependencies": [
            asdict(edge)
            for edge in analysis.dependencies
        ],
        "duplicate_groups": analysis.duplicate_groups,
        "rubric_candidates": analysis.rubric_candidates,
        "cabal_candidates": analysis.cabal_candidates,
        "instance_candidates": analysis.instance_candidates,
        "edifice_findings": analysis.edifice_findings,
        "mood_findings": analysis.mood_findings,
        "kindred_findings": analysis.kindred_findings,
        "ownership_conflicts": analysis.ownership_conflicts,
        "migration_candidates": analysis.migration_candidates,
    }


def markdown_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]

    for row in rows:
        values = [
            str(value).replace("|", "\\|").replace("\n", " ")
            for value in row
        ]
        lines.append("| " + " | ".join(values) + " |")

    return lines


def write_markdown(path: Path, analysis: Analysis) -> None:
    summary = analysis.summary
    lines: list[str] = [
        "# Savant Structural Intelligence Report",
        "",
        f"- Schema: `{SCHEMA_ID}`",
        f"- Root: `{analysis.root}`",
        f"- Generated: `{analysis.generated_at}`",
        "- Mutation performed: `false`",
        "- Migration authorized: `false`",
        "",
        "## Summary",
        "",
    ]

    lines.extend(
        markdown_table(
            ("Measure", "Value"),
            (
                (key, value)
                for key, value in summary.items()
            ),
        )
    )

    lines.extend(
        [
            "",
            "## Highest-confidence Rubric candidates",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            (
                "Candidate",
                "Files",
                "Owners",
                "Confidence",
            ),
            (
                (
                    row["candidate"],
                    row["file_count"],
                    ", ".join(row["owners"]),
                    row["confidence"],
                )
                for row in analysis.rubric_candidates[:50]
            ),
        )
    )

    lines.extend(
        [
            "",
            "## Highest-confidence Cabal candidates",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            (
                "Candidate",
                "Files",
                "Owners",
                "Confidence",
            ),
            (
                (
                    row["candidate"],
                    row["file_count"],
                    ", ".join(row["owners"]),
                    row["confidence"],
                )
                for row in analysis.cabal_candidates[:50]
            ),
        )
    )

    lines.extend(
        [
            "",
            "## Ownership conflicts",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            ("Kind", "Severity", "Path or digest"),
            (
                (
                    row.get("kind", ""),
                    row.get("severity", ""),
                    row.get("path", row.get("sha256", "")),
                )
                for row in analysis.ownership_conflicts[:100]
            ),
        )
    )

    lines.extend(
        [
            "",
            "## Duplicate substance",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            ("Digest", "Count", "Cross-owner", "Owners"),
            (
                (
                    row["sha256"],
                    row["count"],
                    row["cross_owner"],
                    ", ".join(row["owners"]),
                )
                for row in analysis.duplicate_groups[:100]
            ),
        )
    )

    lines.extend(
        [
            "",
            "## Candidate migrations",
            "",
            "These are non-authoritative classifications. No movement is authorized.",
            "",
        ]
    )

    lines.extend(
        markdown_table(
            (
                "Current path",
                "Candidate scope",
                "Owner",
                "Rubric confidence",
                "Cabal confidence",
                "Dependents",
            ),
            (
                (
                    row["current_path"],
                    row["candidate_scope"],
                    row["semantic_owner"],
                    row["rubric_confidence"],
                    row["cabal_confidence"],
                    len(row["dependents"]),
                )
                for row in analysis.migration_candidates[:200]
            ),
        )
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_receipt(
    output_directory: Path,
    report_path: Path,
    markdown_path: Path,
    analysis: Analysis,
) -> Path:
    receipt_path = output_directory / "receipt.json"

    receipt = {
        "schema": "savant://receipt/structure-intelligence/1.0.0",
        "generated_at": utc_now(),
        "root": analysis.root,
        "report": {
            "path": str(report_path),
            "sha256": sha256_file(report_path),
        },
        "summary": {
            "path": str(markdown_path),
            "sha256": sha256_file(markdown_path),
        },
        "analysis": analysis.summary,
        "mutation_performed": False,
        "migration_authorized": False,
    }

    write_json(receipt_path, receipt)

    return receipt_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a read-only structural intelligence report "
            "for Savant Runtime."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--maximum-files",
        type=int,
        default=100000,
    )
    parser.add_argument(
        "--maximum-text-bytes",
        type=int,
        default=2_000_000,
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    root = arguments.root.resolve()
    output_root = arguments.output_root.resolve()

    if not root.is_dir():
        print(
            f"ERROR: runtime root unavailable: {root}",
            file=sys.stderr,
        )
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_directory = output_root / run_id
    output_directory.mkdir(parents=True, exist_ok=False)

    try:
        analysis = compile_analysis(
            root=root,
            maximum_files=arguments.maximum_files,
            maximum_text_bytes=arguments.maximum_text_bytes,
        )

        report_path = output_directory / "structure-intelligence.json"
        markdown_path = output_directory / "STRUCTURE_INTELLIGENCE.md"

        write_json(report_path, analysis_to_mapping(analysis))
        write_markdown(markdown_path, analysis)

        receipt_path = create_receipt(
            output_directory,
            report_path,
            markdown_path,
            analysis,
        )

    except Exception as exc:
        failure_path = output_directory / "failure.json"

        write_json(
            failure_path,
            {
                "schema": "savant://receipt/structure-intelligence-failure/1.0.0",
                "generated_at": utc_now(),
                "root": str(root),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "mutation_performed": False,
                "migration_authorized": False,
            },
        )

        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print(f"FAILURE RECEIPT: {failure_path}", file=sys.stderr)

        return 1

    print(f"REPORT: {report_path}")
    print(f"SUMMARY: {markdown_path}")
    print(f"RECEIPT: {receipt_path}")

    for key, value in analysis.summary.items():
        print(f"{key.upper()}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
