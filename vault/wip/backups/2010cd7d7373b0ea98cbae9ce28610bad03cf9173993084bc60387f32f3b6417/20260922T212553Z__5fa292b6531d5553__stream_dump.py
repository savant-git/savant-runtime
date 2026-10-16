from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Iterable

try:
    from straub.source_datrix import current_from_datrix, datrix
except Exception:
    current_from_datrix = None
    datrix = None


schema = "savant.sdump.stream.v4"
command_schema = "savant.sdump.command.v4"
publish_schema = "savant.sdump.publish.v2"

chunk_size = 4 * 1024 * 1024
gzip_level = 6

s3_bucket = "savant-ai-cluster"
github_owner = "savant-git"
github_repository = "savant-runtime"
github_remote = f"https://github.com/{github_owner}/{github_repository}.git"

default_env_paths = (
    Path("/root/.env"),
    Path.home() / ".env",
)

# Broad, source-positive admission. Directory names never imply that Savant
# architecture is disposable. Only concrete non-source classes are excluded.
source_extensions = frozenset({
    ".py", ".pyi", ".pyx", ".pxd",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".cs", ".fs", ".fsx", ".vb",
    ".rb", ".php", ".lua", ".pl", ".pm", ".r",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".sql", ".graphql", ".gql",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".json", ".jsonc", ".json5",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte",
    ".xml", ".xsd", ".xsl", ".xslt",
    ".tf", ".tfvars", ".hcl",
    ".gradle", ".properties",
    ".proto", ".thrift",
    ".md", ".mdx", ".rst", ".adoc", ".txt",
})

source_filenames = frozenset({
    "dockerfile", "containerfile", "makefile", "procfile", "rakefile",
    "gemfile", "gemfile.lock", "pipfile", "pipfile.lock", "justfile",
    "compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml",
    "pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "noxfile.py",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
    "constraints.txt",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    "pom.xml", "build.gradle", "settings.gradle",
    "composer.json", "composer.lock",
    "deno.json", "deno.jsonc", "bunfig.toml",
    "tsconfig.json", "jsconfig.json",
    "manifest.json", "manifest.webmanifest",
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.json", ".eslintrc", ".eslintrc.json",
    ".prettierrc", ".prettierrc.json", ".babelrc", ".babelrc.json",
    "babel.config.js", "babel.config.json",
    "jest.config.js", "jest.config.ts", "jest.config.json",
    "vite.config.js", "vite.config.ts",
    "webpack.config.js", "webpack.config.ts",
    "rollup.config.js", "rollup.config.ts",
    "nodemon.json", "launch.json", "tasks.json", "settings.json",
    "extensions.json",
})

excluded_dir_names = frozenset({
    ".git", ".hg", ".svn",
    "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".coverage", "coverage", ".nyc_output",
    ".next", ".nuxt", ".svelte-kit", ".parcel-cache", ".turbo",
    "dist", "build",
    ".gradle", ".idea", ".vscode",
    "venv", ".venv", "env", ".envdir",
    "site-packages",
    "savant-sdump-output",
    "source-datrix-state",
})

excluded_suffixes = frozenset({
    ".pyc", ".pyo", ".class", ".o", ".obj", ".so", ".dll", ".dylib",
    ".a", ".lib", ".exe", ".bin",
    ".zip", ".gz", ".bz2", ".xz", ".zst", ".7z", ".rar", ".tar",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mov", ".avi", ".mkv",
    ".pdf", ".woff", ".woff2", ".ttf", ".otf",
    ".db", ".sqlite", ".sqlite3",
    ".log", ".tmp", ".temp", ".swp", ".swo",
})

secret_names = frozenset({
    ".env", ".env.local", ".env.production", ".env.development",
    "id_rsa", "id_ed25519", "credentials", "credentials.json",
    "secrets.json", "secret.json",
})

# These are known generated/recovery families, not architectural source.
excluded_relative_prefixes = (
    "audit/",
    "backups/",
    "repair_backups/",
    "relics/",
    "exports/",
    "imports/",
    "evolution/structure-migration/",
    "state/earmark-projection/",
    "runtime/recovery/",
    "recovery/sqlite-corruption-",
)

excluded_name_prefixes = (
    "sdump_",
    "sdump-",
    "current_runtime_source_dump_",
)


class StreamDumpError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise StreamDumpError(
            f"command failed: {command[0]}: "
            f"{detail or f'exit {result.returncode}'}"
        )
    return result


def require_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise StreamDumpError(f"required executable not found: {name}")
    return executable


def load_env_file() -> dict[str, str]:
    environment = dict(os.environ)
    path = next((item for item in default_env_paths if item.is_file()), None)
    if path is None:
        raise StreamDumpError("environment file not found: /root/.env or ~/.env")

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0:1] == value[-1:] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in environment:
            environment[key] = value
    return environment


def publication_environment() -> dict[str, str]:
    environment = load_env_file()
    if not (
        environment.get("AWS_ACCESS_KEY_ID")
        and environment.get("AWS_SECRET_ACCESS_KEY")
    ):
        raise StreamDumpError("missing AWS credentials in .env")
    return environment


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as error:
        raise StreamDumpError(f"path escaped target: {path}") from error


def is_hidden_relative(relative: str) -> bool:
    parts = Path(relative).parts
    for part in parts:
        if part.startswith(".") and part not in {
            ".github", ".config", ".well-known",
        }:
            return True
    return False


def is_secret_name(name: str) -> bool:
    lowered = name.casefold()
    if lowered in secret_names:
        return True
    if lowered.startswith(".env."):
        return True
    return any(
        token in lowered
        for token in (
            "private_key", "private-key", "apikey", "api_key",
            "access_token", "refresh_token",
        )
    )


def has_program_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            first = handle.readline(512)
    except OSError:
        return False
    if not first.startswith(b"#!"):
        return False
    lowered = first.lower()
    return any(
        token in lowered
        for token in (
            b"python", b"node", b"deno", b"bun", b"bash", b"/sh",
            b"zsh", b"fish", b"ruby", b"perl", b"php", b"lua",
        )
    )


def admitted(path: Path, root: Path, file_stat: os.stat_result) -> bool:
    relative = safe_relative(path, root)
    lowered_relative = relative.casefold()
    lowered_name = path.name.casefold()

    parts = tuple(part.casefold() for part in Path(relative).parts[:-1])
    if any(part in excluded_dir_names for part in parts):
        return False

    if is_hidden_relative(relative):
        return False

    if is_secret_name(path.name):
        return False

    if any(lowered_relative.startswith(prefix) for prefix in excluded_relative_prefixes):
        return False

    if lowered_name.startswith(excluded_name_prefixes):
        return False

    suffix = path.suffix.casefold()
    if suffix in excluded_suffixes:
        return False

    if lowered_name in source_filenames:
        return True

    if suffix in source_extensions:
        return True

    if file_stat.st_mode & stat.S_IXUSR:
        return True

    return has_program_shebang(path)


def discover_source(root: Path) -> tuple[list[Any], dict[str, Any]]:
    candidates: list[Any] = []
    files_seen = 0
    skipped = 0
    total_bytes = 0

    def onerror(error: OSError) -> None:
        raise StreamDumpError(f"source discovery failed: {error}")

    for directory, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        directory_path = Path(directory)
        relative_directory = safe_relative(directory_path, root) if directory_path != root else ""

        retained_dirs: list[str] = []
        for name in dirs:
            child = directory_path / name
            relative = f"{relative_directory}/{name}".strip("/")
            lowered = name.casefold()
            if child.is_symlink():
                skipped += 1
                continue
            if lowered in excluded_dir_names:
                skipped += 1
                continue
            if is_hidden_relative(relative):
                skipped += 1
                continue
            if any(relative.casefold().startswith(prefix) for prefix in excluded_relative_prefixes):
                skipped += 1
                continue
            retained_dirs.append(name)
        dirs[:] = retained_dirs

        for name in files:
            files_seen += 1
            path = directory_path / name
            try:
                if path.is_symlink():
                    skipped += 1
                    continue
                file_stat = path.stat()
            except OSError as error:
                raise StreamDumpError(f"unable to stat source candidate {path}: {error}") from error

            if not stat.S_ISREG(file_stat.st_mode):
                skipped += 1
                continue

            if not admitted(path, root, file_stat):
                skipped += 1
                continue

            relative = safe_relative(path, root)
            candidates.append(
                SimpleNamespace(
                    relative_path=relative,
                    absolute_path=path,
                    size=file_stat.st_size,
                )
            )
            total_bytes += file_stat.st_size

    candidates.sort(key=lambda item: (item.relative_path.casefold(), item.relative_path))
    return candidates, {
        "candidate_count": len(candidates),
        "candidate_bytes": total_bytes,
        "files_seen": files_seen,
        "skipped_count": skipped,
    }


def datrix_context(target: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if datrix is None or current_from_datrix is None:
        return {}, {
            "available": False,
            "status": "unavailable",
            "role": "provenance-context",
        }

    try:
        source_datrix = datrix()
        health = source_datrix.health()
        if health.get("status") != "ok":
            return {}, {
                "available": True,
                "status": str(health.get("status") or "not-ok"),
                "role": "provenance-context",
            }

        current = current_from_datrix(source_datrix)
        index: dict[str, dict[str, Any]] = {}
        target_resolved = target.resolve()

        for record in current.values():
            if not isinstance(record, dict):
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict) or payload.get("deleted"):
                continue
            raw_path = payload.get("path")
            if not isinstance(raw_path, str) or not raw_path:
                continue

            source_path = Path(raw_path)
            if not source_path.is_absolute():
                source_path = Path("/root/savant-runtime") / source_path
            try:
                relative = source_path.resolve().relative_to(target_resolved).as_posix()
            except (OSError, ValueError):
                continue
            index[relative] = record

        return index, {
            "available": True,
            "status": "ok",
            "role": "provenance-context",
            "current_revisions": len(current),
        }
    except Exception as error:
        return {}, {
            "available": False,
            "status": "unavailable",
            "role": "provenance-context",
            "error_type": type(error).__name__,
        }


def output_path(target: Path) -> Path:
    parent = Path(tempfile.mkdtemp(prefix="savant-sdump-"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S%f") + "z"
    return parent / f"sdump_{target.name}_{timestamp}.txt.gz"


def capture_candidate(
    candidate: Any,
    datrix_index: dict[str, dict[str, Any]],
) -> tuple[Any, dict[str, Any], os.stat_result, str, bool]:
    relative = candidate.relative_path
    source = candidate.absolute_path
    try:
        before = source.stat()
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as reader:
            while block := reader.read(chunk_size):
                digest.update(block)
                size += len(block)
        after = source.stat()
    except OSError as error:
        raise StreamDumpError(f"unable to capture source {relative}: {error}") from error

    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or size != before.st_size
    ):
        raise StreamDumpError(f"source changed while capturing: {relative}")

    actual_sha = digest.hexdigest()
    record = datrix_index.get(relative) or {}
    payload = record.get("payload") if isinstance(record, dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    datrix_matches = str(payload.get("sha256") or "") == actual_sha
    return candidate, record, before, actual_sha, datrix_matches

def write_text(handle: Any, text: str, digest: Any) -> int:
    encoded = text.encode("utf-8")
    handle.write(text)
    digest.update(encoded)
    return len(encoded)


def write_json_line(handle: Any, value: Any, digest: Any) -> int:
    return write_text(handle, canonical_json(value) + "\n", digest)


def language(path: Path) -> str:
    suffix = path.suffix.casefold()
    mapping = {
        ".py": "python", ".pyi": "python",
        ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".json": "json", ".jsonc": "json",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".md": "markdown", ".mdx": "markdown", ".rst": "rst",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".sql": "sql", ".xml": "xml",
        ".go": "go", ".rs": "rust", ".java": "java",
    }
    return mapping.get(suffix, suffix.lstrip(".") or "text")


def write_file_record(
    handle: Any,
    candidate: Any,
    record: dict[str, Any],
    file_stat: os.stat_result,
    actual_sha: str,
    artifact_digest: Any,
) -> int:
    payload = record.get("payload") if isinstance(record, dict) else {}
    if not isinstance(payload, dict):
        payload = {}

    metadata = {
        "path": candidate.relative_path,
        "sha256": actual_sha,
        "size": file_stat.st_size,
        "mode": oct(stat.S_IMODE(file_stat.st_mode)),
        "language": language(candidate.absolute_path),
        "source_revision_id": record.get("id") if isinstance(record, dict) else None,
        "datrix_payload_sha256": payload.get("sha256"),
        "observed_at": record.get("observed_at") if isinstance(record, dict) else None,
    }

    rendered = 0
    rendered += write_text(handle, "=== file ===\n", artifact_digest)
    rendered += write_json_line(handle, metadata, artifact_digest)
    rendered += write_text(handle, "=== content ===\n", artifact_digest)

    with candidate.absolute_path.open(
        "r", encoding="utf-8", errors="replace", newline=None
    ) as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            rendered += write_text(handle, chunk, artifact_digest)

    rendered += write_text(
        handle,
        "\n=== /content ===\n=== /file ===\n\n",
        artifact_digest,
    )
    return rendered


def stream_dump(target_raw: str) -> tuple[Path, list[Any], dict[str, Any]]:
    target = Path(target_raw).expanduser().resolve(strict=True)
    if not target.is_dir():
        raise StreamDumpError("sdump target must be a directory")

    candidates, discovery = discover_source(target)
    if not candidates:
        raise StreamDumpError("no relevant Savant source admitted")

    datrix_index, datrix_meta = datrix_context(target)
    captured = [capture_candidate(candidate, datrix_index) for candidate in candidates]
    admitted_paths = {item.relative_path for item in candidates}
    captured_paths = {item[0].relative_path for item in captured}
    if admitted_paths != captured_paths:
        raise StreamDumpError("source admission and capture sets differ")

    datrix_matched = sum(1 for item in captured if item[4])
    datrix_unmatched = len(captured) - datrix_matched
    output = output_path(target)
    artifact_digest = hashlib.sha256()
    serialized_paths: set[str] = set()
    included_source_bytes = 0
    rendered_bytes = 0

    with gzip.open(output, "wt", encoding="utf-8", newline="\n", compresslevel=gzip_level) as handle:
        rendered_bytes += write_text(handle, "=== sdump manifest ===\n", artifact_digest)
        rendered_bytes += write_json_line(handle, {
            "schema": schema,
            "generated_at": now_iso(),
            "target_name": target.name,
            "purpose": "portable comprehensive Savant source and architecture context",
            "source_admission": "broad-positive-source-with-concrete-generated-evidence-exclusions",
            "source_capture": "bounded-memory-stability-verified",
            "source_files": len(captured),
            "source_bytes": discovery["candidate_bytes"],
            "datrix": datrix_meta,
            "datrix_matching_files": datrix_matched,
            "datrix_nonmatching_or_missing_files": datrix_unmatched,
            "gzip_level": gzip_level,
            "authority_effect": "none",
            "filesystem_presence_establishes_authority": False,
            "strict_completeness": True,
        }, artifact_digest)
        rendered_bytes += write_text(handle, "=== /sdump manifest ===\n\n", artifact_digest)

        for candidate, record, captured_stat, captured_sha, _matches in captured:
            try:
                current = candidate.absolute_path.stat()
            except OSError as error:
                raise StreamDumpError(f"source disappeared: {candidate.relative_path}") from error
            if (
                current.st_dev != captured_stat.st_dev
                or current.st_ino != captured_stat.st_ino
                or current.st_size != captured_stat.st_size
                or current.st_mtime_ns != captured_stat.st_mtime_ns
            ):
                raise StreamDumpError(f"source changed before serialization: {candidate.relative_path}")

            if candidate.relative_path in serialized_paths:
                raise StreamDumpError(f"duplicate serialized path: {candidate.relative_path}")

            serialized_paths.add(candidate.relative_path)
            included_source_bytes += captured_stat.st_size
            rendered_bytes += write_file_record(
                handle, candidate, record, captured_stat, captured_sha, artifact_digest
            )

            # write_file_record read the source. Verify it remained the captured file.
            after = candidate.absolute_path.stat()
            if (
                after.st_dev != captured_stat.st_dev
                or after.st_ino != captured_stat.st_ino
                or after.st_size != captured_stat.st_size
                or after.st_mtime_ns != captured_stat.st_mtime_ns
            ):
                raise StreamDumpError(f"source changed during serialization: {candidate.relative_path}")

        complete = (
            admitted_paths == captured_paths == serialized_paths
            and included_source_bytes == discovery["candidate_bytes"]
        )
        rendered_bytes += write_text(handle, "=== sdump completeness ===\n", artifact_digest)
        rendered_bytes += write_json_line(handle, {
            "admitted_files": len(admitted_paths),
            "captured_files": len(captured_paths),
            "serialized_files": len(serialized_paths),
            "admitted_bytes": discovery["candidate_bytes"],
            "serialized_source_bytes": included_source_bytes,
            "complete": complete,
        }, artifact_digest)
        rendered_bytes += write_text(handle, "=== /sdump completeness ===\n", artifact_digest)

    if not complete:
        raise StreamDumpError("strict source completeness invariant failed")

    return output, candidates, {
        "target": target,
        "discovery": discovery,
        "captured": captured,
        "datrix": datrix_meta,
        "datrix_matched": datrix_matched,
        "datrix_unmatched": datrix_unmatched,
        "rendered_bytes": rendered_bytes,
    }

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def upload_to_s3(
    artifact: Path,
    environment: dict[str, str],
    artifact_sha256: str,
) -> dict[str, Any]:
    aws = require_executable("aws")
    key = artifact.name
    destination = f"s3://{s3_bucket}/{key}"

    run(
        [
            aws, "s3api", "put-object",
            "--bucket", s3_bucket,
            "--key", key,
            "--body", str(artifact),
            "--metadata", f"sha256={artifact_sha256}",
        ],
        env=environment,
    )

    head = run(
        [
            aws, "s3api", "head-object",
            "--bucket", s3_bucket,
            "--key", key,
            "--output", "json",
        ],
        env=environment,
    )

    try:
        remote = json.loads(head.stdout)
    except json.JSONDecodeError as error:
        raise StreamDumpError("S3 verification returned invalid JSON") from error

    local_size = artifact.stat().st_size
    remote_size = int(remote.get("ContentLength", -1))
    metadata = remote.get("Metadata") or {}
    remote_sha = str(metadata.get("sha256") or "")

    if remote_size != local_size:
        raise StreamDumpError("S3 upload verification size mismatch")
    if remote_sha != artifact_sha256:
        raise StreamDumpError("S3 upload verification sha256 mismatch")

    return {
        "bucket": s3_bucket,
        "key": key,
        "uri": destination,
        "bytes": remote_size,
        "sha256": remote_sha,
        "version_id": remote.get("VersionId"),
        "verified": True,
    }


def git_identity(git: str) -> None:
    if not run([git, "config", "--global", "--get", "user.name"]).stdout.strip():
        raise StreamDumpError("global git user.name is not configured")
    if not run([git, "config", "--global", "--get", "user.email"]).stdout.strip():
        raise StreamDumpError("global git user.email is not configured")


def clean_checkout_contents(checkout: Path) -> None:
    for child in checkout.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_authoritative_source(checkout: Path, captured: Iterable[Any]) -> None:
    for candidate, _record, captured_stat, captured_sha, _matches in captured:
        destination = checkout / candidate.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with candidate.absolute_path.open("rb") as reader, destination.open("wb") as writer:
            while block := reader.read(chunk_size):
                writer.write(block)
                digest.update(block)
        if digest.hexdigest() != captured_sha:
            raise StreamDumpError(
                f"source changed before GitHub synchronization: {candidate.relative_path}"
            )
        os.chmod(destination, stat.S_IMODE(captured_stat.st_mode))


def push_source_to_github(
    captured: list[Any],
    environment: dict[str, str],
) -> dict[str, Any]:
    git = require_executable("git")
    git_identity(git)
    branch = environment.get("SDUMP_GITHUB_BRANCH", "main").strip() or "main"

    with tempfile.TemporaryDirectory(prefix="savant-sdump-git-") as temporary:
        checkout = Path(temporary) / "repository"
        run(
            [
                git, "clone", "--quiet", "--depth", "1",
                "--branch", branch, "--single-branch",
                github_remote, str(checkout),
            ],
            env=environment,
        )

        clean_checkout_contents(checkout)
        copy_authoritative_source(checkout, captured)

        run([git, "add", "--all"], cwd=checkout, env=environment)
        status = run([git, "status", "--porcelain"], cwd=checkout, env=environment).stdout
        changed = bool(status.strip())

        if changed:
            run(
                [git, "commit", "--quiet", "-m", "sdump: synchronize authoritative source"],
                cwd=checkout,
                env=environment,
            )

        run([git, "push", "--quiet", "origin", branch], cwd=checkout, env=environment)

        local_head = run([git, "rev-parse", "HEAD"], cwd=checkout, env=environment).stdout.strip()
        remote = run(
            [git, "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
            cwd=checkout,
            env=environment,
        ).stdout.strip()

        if not remote:
            raise StreamDumpError("GitHub verification returned no remote head")
        remote_head = remote.split()[0]
        if remote_head != local_head:
            raise StreamDumpError("GitHub push verification head mismatch")

        return {
            "repository": f"{github_owner}/{github_repository}",
            "branch": branch,
            "commit": local_head,
            "changed": changed,
            "verified": True,
        }


def delete_local_artifact(artifact: Path) -> None:
    artifact.unlink()
    try:
        artifact.parent.rmdir()
    except OSError:
        pass
    if artifact.exists():
        raise StreamDumpError("local sdump artifact could not be deleted")


def publish(
    artifact: Path,
    captured: list[Any],
    environment: dict[str, str],
    artifact_sha256: str,
) -> dict[str, Any]:
    s3_result = upload_to_s3(artifact, environment, artifact_sha256)
    github_result = push_source_to_github(captured, environment)
    delete_local_artifact(artifact)

    return {
        "schema": publish_schema,
        "s3": s3_result,
        "github": github_result,
        "local_artifact_deleted": True,
        "authority_effect": "none",
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        raise StreamDumpError("usage: sdump TARGET")

    environment = publication_environment()
    artifact, candidates, metadata = stream_dump(arguments[0])

    artifact_sha256 = sha256_file(artifact)
    artifact_size = artifact.stat().st_size

    try:
        publication = publish(
            artifact,
            metadata["captured"],
            environment,
            artifact_sha256,
        )
    except Exception as error:
        raise StreamDumpError(
            f"publication failed; local sdump retained at {artifact}: {error}"
        ) from error

    result = {
        "schema": command_schema,
        "status": "ok",
        "target": str(metadata["target"]),
        "source_files": len(candidates),
        "source_bytes": metadata["discovery"]["candidate_bytes"],
        "artifact_sha256": artifact_sha256,
        "artifact_compressed_bytes": artifact_size,
        "datrix": metadata["datrix"],
        "datrix_matching_files": metadata["datrix_matched"],
        "datrix_nonmatching_or_missing_files": metadata["datrix_unmatched"],
        "s3": publication["s3"],
        "github": publication["github"],
        "local_artifact_deleted": publication["local_artifact_deleted"],
        "authority_effect": "none",
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StreamDumpError as error:
        print(f"sdump error: {error}", file=sys.stderr)
        raise SystemExit(1)
