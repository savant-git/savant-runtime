from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Iterable

from .ignore import IgnoreMatcher
from .model import Candidate, FileRecord, Profile, Projection, ScanStats, SkipRecord
from .redact import redact_text
from .util import atomic_write_text, stable_hash


LANGUAGES = {
    ".py": "python",
    ".pyi": "python-interface",
    ".js": "javascript",
    ".jsx": "javascript-react",
    ".mjs": "javascript-module",
    ".cjs": "javascript-commonjs",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".mts": "typescript-module",
    ".cts": "typescript-commonjs",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin-script",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".h": "c-header",
    ".hh": "cpp-header",
    ".hpp": "cpp-header",
    ".hxx": "cpp-header",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".lua": "lua",
    ".pl": "perl",
    ".r": "r",
    ".sh": "shell",
    ".bash": "bash",
    ".zsh": "zsh",
    ".fish": "fish",
    ".ps1": "powershell",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".json": "json",
    ".jsonl": "json-lines",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "config",
    ".conf": "config",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".rst": "restructuredtext",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    ".xml": "xml",
    ".xsd": "xml-schema",
    ".tf": "terraform",
    ".tfvars": "terraform-vars",
    ".gradle": "gradle",
    ".properties": "properties",
    ".csv": "csv",
    ".tsv": "tsv",
}


class ScanError(RuntimeError):
    pass


def language(path: Path) -> str:
    name = path.name.casefold()
    if name in {"dockerfile", "containerfile"}:
        return "containerfile"
    if name == "makefile":
        return "makefile"
    return LANGUAGES.get(path.suffix.casefold(), path.suffix.lstrip(".") or "text")


def category(path: Path, profile: Profile) -> str:
    lowered_parts = {part.casefold() for part in path.parts}
    return "canon" if lowered_parts & profile.canon_path_names else "source"


def normalized_targets(raw_targets: Iterable[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in raw_targets:
        path = Path(raw).expanduser().resolve(strict=False)
        if not path.exists():
            raise ScanError(f"target does not exist: {raw}")
        resolved.append(path)
    resolved = sorted(set(resolved), key=lambda item: str(item).casefold())
    normalized: list[Path] = []
    for candidate in resolved:
        nested = False
        for parent in resolved:
            if candidate == parent or not parent.is_dir():
                continue
            try:
                candidate.relative_to(parent)
                nested = True
                break
            except ValueError:
                pass
        if not nested:
            normalized.append(candidate)
    return normalized


def target_ids(targets: list[Path]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    used: Counter[str] = Counter()
    for target in targets:
        base = target.name or "root"
        used[base] += 1
        target_id = base if used[base] == 1 else f"{base}-{used[base]}"
        result[target] = target_id
    return result


def _relative(root: Path, path: Path, target_id: str, multiple: bool) -> str:
    if root.is_file():
        local = root.name
    else:
        local = path.relative_to(root).as_posix()
    return f"{target_id}/{local}" if multiple else local


def _authoritative_candidate(path: Path, profile: Profile, mode: int) -> bool:
    lowered_name = path.name.casefold()
    suffix = path.suffix.casefold()
    if lowered_name in profile.include_filenames or suffix in profile.include_extensions:
        return True
    return bool(mode & stat.S_IXUSR)


def discover(
    targets: list[Path],
    profile: Profile,
    absolute_excluded_roots: Iterable[Path],
    include_hidden: bool,
    include_secrets: bool,
    extra_patterns: Iterable[str],
    respect_gitignore: bool | None,
) -> tuple[list[Candidate], list[SkipRecord], list[SkipRecord], list[dict[str, Any]], ScanStats]:
    candidates: list[Candidate] = []
    skipped: list[SkipRecord] = []
    failures: list[SkipRecord] = []
    symlinks: list[dict[str, Any]] = []
    stats = ScanStats()
    ids = target_ids(targets)
    multiple = len(targets) > 1

    for root in targets:
        target_id = ids[root]
        matcher_root = root if root.is_dir() else root.parent
        matcher = IgnoreMatcher(
            profile=profile,
            target_root=matcher_root,
            absolute_excluded_roots=absolute_excluded_roots,
            include_hidden=include_hidden,
            include_secrets=include_secrets,
            extra_patterns=extra_patterns,
            respect_gitignore=respect_gitignore,
        )

        if root.is_file():
            try:
                relative = _relative(root, root, target_id, multiple)
                reason = matcher.skip_reason(root, relative, False)
                st = root.lstat()
                stats.files_seen += 1
                if reason:
                    skipped.append(SkipRecord(relative, reason, st.st_size))
                    continue
                if not stat.S_ISREG(st.st_mode):
                    skipped.append(SkipRecord(relative, "not_regular_file", st.st_size))
                    continue
                if not _authoritative_candidate(root, profile, st.st_mode):
                    skipped.append(SkipRecord(relative, "non_authoritative_extension", st.st_size))
                    continue
                candidates.append(
                    Candidate(
                        absolute_path=root,
                        relative_path=relative,
                        target_id=target_id,
                        category=category(root, profile),
                        mode=st.st_mode,
                        size=st.st_size,
                        mtime_ns=st.st_mtime_ns,
                        inode=st.st_ino,
                        device=st.st_dev,
                    )
                )
            except Exception as error:
                failures.append(SkipRecord(str(root), f"discovery_error:{error}"))
            continue

        for current, subdirs, filenames in os.walk(
            root,
            topdown=True,
            followlinks=profile.follow_symlinks,
        ):
            current_path = Path(current)
            stats.directories_seen += 1
            kept_subdirs: list[str] = []
            for name in sorted(subdirs, key=str.casefold):
                path = current_path / name
                relative = _relative(root, path, target_id, multiple)
                try:
                    if path.is_symlink():
                        stats.symlinks_seen += 1
                        symlinks.append(
                            {
                                "path": relative,
                                "target": os.readlink(path),
                                "kind": "directory_symlink",
                            }
                        )
                        if not profile.follow_symlinks:
                            continue
                    reason = matcher.skip_reason(path, relative, True)
                    if reason:
                        skipped.append(SkipRecord(relative, reason))
                        continue
                    kept_subdirs.append(name)
                except Exception as error:
                    failures.append(SkipRecord(relative, f"directory_error:{error}"))
            subdirs[:] = kept_subdirs

            for name in sorted(filenames, key=str.casefold):
                path = current_path / name
                relative = _relative(root, path, target_id, multiple)
                stats.files_seen += 1
                try:
                    if path.is_symlink():
                        stats.symlinks_seen += 1
                        symlinks.append(
                            {
                                "path": relative,
                                "target": os.readlink(path),
                                "kind": "file_symlink",
                            }
                        )
                        continue
                    reason = matcher.skip_reason(path, relative, False)
                    if reason:
                        try:
                            size = path.lstat().st_size
                        except OSError:
                            size = None
                        skipped.append(SkipRecord(relative, reason, size))
                        continue
                    st = path.lstat()
                    if not stat.S_ISREG(st.st_mode):
                        skipped.append(SkipRecord(relative, "not_regular_file", st.st_size))
                        continue
                    if not _authoritative_candidate(path, profile, st.st_mode):
                        skipped.append(SkipRecord(relative, "non_authoritative_extension", st.st_size))
                        continue
                    if st.st_size > profile.max_file_bytes:
                        skipped.append(SkipRecord(relative, "max_file_bytes_exceeded", st.st_size))
                        continue
                    candidates.append(
                        Candidate(
                            absolute_path=path,
                            relative_path=relative,
                            target_id=target_id,
                            category=category(path, profile),
                            mode=st.st_mode,
                            size=st.st_size,
                            mtime_ns=st.st_mtime_ns,
                            inode=st.st_ino,
                            device=st.st_dev,
                        )
                    )
                except Exception as error:
                    failures.append(SkipRecord(relative, f"file_error:{error}"))

    candidates.sort(key=lambda item: item.relative_path.casefold())
    skipped.sort(key=lambda item: (item.path.casefold(), item.reason))
    failures.sort(key=lambda item: (item.path.casefold(), item.reason))
    symlinks.sort(key=lambda item: item["path"].casefold())
    stats.candidates = len(candidates)
    stats.skipped = len(skipped)
    stats.failures = len(failures)
    if len(candidates) > profile.max_files:
        raise ScanError(
            f"candidate count {len(candidates)} exceeds profile max_files {profile.max_files}; use a narrower target or forensic profile"
        )
    return candidates, skipped, failures, symlinks, stats


def _binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    sample = data[:8192]
    if not sample:
        return False
    controls = sum(byte < 9 or (13 < byte < 32) for byte in sample)
    return controls / len(sample) > 0.08


def _decode(data: bytes) -> tuple[str, str] | None:
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        from charset_normalizer import from_bytes

        match = from_bytes(data).best()
        if match is not None and match.encoding:
            return str(match), match.encoding
    except Exception:
        pass
    for encoding in ("utf-16", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return None


def _analyze_one(candidate: Candidate, redact: bool) -> tuple[Candidate, bytes | None, dict[str, Any]]:
    before = candidate.absolute_path.stat()
    signature_before = (
        before.st_size,
        before.st_mtime_ns,
        before.st_ino,
        before.st_dev,
    )
    if signature_before != (
        candidate.size,
        candidate.mtime_ns,
        candidate.inode,
        candidate.device,
    ):
        return candidate, None, {"reason": "changed_before_read"}

    data = candidate.absolute_path.read_bytes()
    after = candidate.absolute_path.stat()
    signature_after = (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev)
    if signature_after != signature_before:
        return candidate, None, {"reason": "changed_during_read"}
    if _binary(data):
        return candidate, None, {"reason": "binary_content"}
    decoded = _decode(data)
    if decoded is None:
        return candidate, None, {"reason": "undecodable_text"}
    text, encoding = decoded
    redactions = 0
    if redact:
        text, redactions = redact_text(text)
    rendered = text.encode("utf-8")
    return candidate, rendered, {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "rendered_sha256": hashlib.sha256(rendered).hexdigest(),
        "encoding": encoding,
        "redactions": redactions,
    }


def build_projection(
    candidates: list[Candidate],
    skipped: list[SkipRecord],
    failures: list[SkipRecord],
    symlinks: list[dict[str, Any]],
    stats: ScanStats,
    profile: Profile,
    content_store: Path,
    workers: int,
    include_secrets: bool,
) -> Projection:
    content_store.mkdir(parents=True, exist_ok=True)
    records: list[FileRecord] = []
    canonical_by_source_hash: dict[str, str] = {}
    store_by_content_id: dict[str, Path] = {}
    unique_rendered_bytes = 0
    redact = profile.redact_secrets and not include_secrets

    max_workers = max(1, workers)
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sdump-scan") as executor:
        for candidate, rendered, analysis in executor.map(
            lambda item: _analyze_one(item, redact), candidates
        ):
            reason = analysis.get("reason")
            if reason or rendered is None:
                failure_reason = str(reason or "analysis_failed")
                destination = skipped if failure_reason in {"binary_content", "undecodable_text"} else failures
                destination.append(SkipRecord(candidate.relative_path, failure_reason, candidate.size))
                records.append(
                    FileRecord(
                        path=candidate.relative_path,
                        target_id=candidate.target_id,
                        category=candidate.category,
                        language=language(candidate.absolute_path),
                        size=candidate.size,
                        mode=oct(stat.S_IMODE(candidate.mode)),
                        mtime_ns=candidate.mtime_ns,
                        source_sha256="",
                        rendered_sha256=None,
                        content_id=None,
                        duplicate_of=None,
                        encoding=None,
                        redactions=0,
                        authoritative=True,
                        included=False,
                        reason=str(reason or "analysis_failed"),
                    )
                )
                continue

            source_sha256 = str(analysis["source_sha256"])
            rendered_sha256 = str(analysis["rendered_sha256"])
            duplicate_of = canonical_by_source_hash.get(source_sha256)
            content_id = f"sha256:{rendered_sha256}"

            if duplicate_of is None:
                if unique_rendered_bytes + len(rendered) > profile.max_total_content_bytes:
                    records.append(
                        FileRecord(
                            path=candidate.relative_path,
                            target_id=candidate.target_id,
                            category=candidate.category,
                            language=language(candidate.absolute_path),
                            size=candidate.size,
                            mode=oct(stat.S_IMODE(candidate.mode)),
                            mtime_ns=candidate.mtime_ns,
                            source_sha256=source_sha256,
                            rendered_sha256=rendered_sha256,
                            content_id=None,
                            duplicate_of=None,
                            encoding=str(analysis["encoding"]),
                            redactions=int(analysis["redactions"]),
                            authoritative=True,
                            included=False,
                            reason="max_total_content_bytes_exceeded",
                        )
                    )
                    skipped.append(
                        SkipRecord(candidate.relative_path, "max_total_content_bytes_exceeded", candidate.size)
                    )
                    continue

                canonical_by_source_hash[source_sha256] = candidate.relative_path
                unique_rendered_bytes += len(rendered)
                store_path = content_store / f"{rendered_sha256}.txt"
                if not store_path.exists():
                    atomic_write_text(store_path, rendered.decode("utf-8"), mode=0o600)
                store_by_content_id[content_id] = store_path
            else:
                stats.duplicate_bytes_avoided += len(rendered)

            records.append(
                FileRecord(
                    path=candidate.relative_path,
                    target_id=candidate.target_id,
                    category=candidate.category,
                    language=language(candidate.absolute_path),
                    size=candidate.size,
                    mode=oct(stat.S_IMODE(candidate.mode)),
                    mtime_ns=candidate.mtime_ns,
                    source_sha256=source_sha256,
                    rendered_sha256=rendered_sha256,
                    content_id=content_id,
                    duplicate_of=duplicate_of,
                    encoding=str(analysis["encoding"]),
                    redactions=int(analysis["redactions"]),
                    authoritative=True,
                    included=True,
                    reason=None,
                )
            )

    records.sort(key=lambda item: item.path.casefold())
    skipped.sort(key=lambda item: (item.path.casefold(), item.reason))
    failures.sort(key=lambda item: (item.path.casefold(), item.reason))
    included = [record for record in records if record.included]
    stats.included_files = len(included)
    stats.unique_contents = sum(record.duplicate_of is None for record in included)
    stats.duplicate_files = sum(record.duplicate_of is not None for record in included)
    stats.source_bytes = sum(record.size for record in included)
    stats.rendered_bytes = unique_rendered_bytes
    stats.redactions = sum(record.redactions for record in included if record.duplicate_of is None)
    stats.skipped = len(skipped)
    stats.failures = len(failures)

    stable_records = [
        {
            "path": record.path,
            "category": record.category,
            "size": record.size,
            "source_sha256": record.source_sha256,
            "rendered_sha256": record.rendered_sha256,
            "duplicate_of": record.duplicate_of,
            "included": record.included,
            "reason": record.reason,
        }
        for record in records
    ]
    snapshot_hash = stable_hash(
        {
            "profile": profile.id,
            "files": stable_records,
            "symlinks": symlinks,
        }
    )

    return Projection(
        records=records,
        skipped=skipped,
        failures=failures,
        symlinks=symlinks,
        stats=stats,
        content_store=content_store,
        snapshot_hash=snapshot_hash,
        unique_content_paths=store_by_content_id,
    )
