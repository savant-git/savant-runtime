from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Iterable



schema = "savant.sdump.stream.v8"
command_schema = "savant.sdump.command.v8"
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
    "_reports/",
    "reports/",
    "assurance/",
    "audit/",
    "backups/",
    "repair_backups/",
    "relics/",
    "exports/",
    "imports/",
    "evolution/structure-migration/",
    "state/",
    "runtime/recovery/",
    "recovery/",
    "runtime/straub/source-datrix-state/",
    "savant-sdump-output/",
)

excluded_name_prefixes = (
    "sdump_",
    "sdump-",
    "current_runtime_source_dump_",
)


excluded_exact_relative_paths = frozenset({
    "context/CANONICAL_OWNERSHIP_GRAPH.json",
    "context/SEMANTIC_REFERENCE_GRAPH.json",
})

structured_source_names = frozenset({
    "package.json", "package-lock.json", "tsconfig.json", "jsconfig.json",
    "composer.json", "composer.lock", "deno.json", "deno.jsonc",
    "manifest.json", "manifest.webmanifest", "import_map.json",
    "settings.json", "launch.json", "tasks.json", "extensions.json",
    ".eslintrc.json", ".prettierrc.json", ".babelrc.json",
    "babel.config.json", "jest.config.json", "nodemon.json",
})

structured_source_dirs = frozenset({
    "config", "configs", "configuration",
    "schema", "schemas",
    "contract", "contracts",
    "fixture", "fixtures",
    "testdata", "test-data",
    ".github",
})

text_source_names = frozenset({
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
    "constraints.txt",
})


class TerminalUI:
    """TTY-aware, dependency-free sdump terminal projection."""

    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    cyan = "\033[36m"
    green = "\033[32m"
    yellow = "\033[33m"
    red = "\033[31m"
    blue = "\033[34m"

    def __init__(self) -> None:
        self.tty = bool(getattr(sys.stderr, "isatty", lambda: False)())
        self.color = (
            self.tty
            and os.environ.get("TERM", "").casefold() != "dumb"
            and "NO_COLOR" not in os.environ
        )
        self.unicode = os.environ.get("SDUMP_ASCII", "").casefold() not in {"1", "true", "yes"}
        self.started = time.monotonic()
        self.last_render = 0.0
        self.last_line_width = 0
        self.phase_started = self.started

    def c(self, value: str, *styles: str) -> str:
        if not self.color:
            return value
        return "".join(styles) + value + self.reset

    def width(self) -> int:
        return max(54, min(shutil.get_terminal_size((80, 24)).columns, 120))

    def human_bytes(self, value: float) -> str:
        units = ("B", "KiB", "MiB", "GiB", "TiB")
        amount = float(max(0.0, value))
        for unit in units:
            if amount < 1024.0 or unit == units[-1]:
                return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
            amount /= 1024.0
        return f"{amount:.1f} TiB"

    def duration(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s"
        minutes, seconds = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {seconds:02d}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes:02d}m"

    def bar(self, fraction: float, width: int = 22) -> str:
        fraction = min(1.0, max(0.0, fraction))
        filled = int(round(width * fraction))
        if self.unicode:
            return "█" * filled + "░" * (width - filled)
        return "#" * filled + "-" * (width - filled)

    def clear_progress(self) -> None:
        if not self.tty or not self.last_line_width:
            return
        sys.stderr.write("\r" + (" " * self.last_line_width) + "\r")
        sys.stderr.flush()
        self.last_line_width = 0

    def line(self, value: str = "") -> None:
        self.clear_progress()
        print(value, file=sys.stderr, flush=True)

    def banner(self, target: Path) -> None:
        rule_char = "─" if self.unicode else "-"
        rule = rule_char * min(self.width(), 78)
        mark = "◆" if self.unicode else "*"
        self.line(self.c(rule, self.dim))
        self.line(
            f"{self.c(mark, self.cyan)} "
            f"{self.c('savant sdump', self.bold)}  "
            f"{self.c('portable source projection', self.dim)}"
        )
        self.line(f"  target  {target}")
        self.line(f"  output  gzip → s3://{s3_bucket}/ + github")
        self.line(self.c(rule, self.dim))

    def phase(self, name: str, detail: str = "") -> None:
        self.phase_started = time.monotonic()
        marker = "◇" if self.unicode else ">"
        suffix = f"  {self.c(detail, self.dim)}" if detail else ""
        self.line(f"{self.c(marker, self.blue)} {self.c(name, self.bold)}{suffix}")

    def note(self, label: str, value: str, tone: str = "normal") -> None:
        style = {
            "good": self.green,
            "warn": self.yellow,
            "bad": self.red,
        }.get(tone)
        rendered = self.c(value, style) if style else value
        self.line(f"  {self.c(label, self.dim):<18} {rendered}")

    def progress(
        self,
        *,
        label: str,
        current: int,
        total: int,
        bytes_done: int = 0,
        bytes_total: int = 0,
        force: bool = False,
    ) -> None:
        now = time.monotonic()
        if not force and now - self.last_render < 0.12:
            return
        self.last_render = now

        fraction = (current / total) if total else 1.0
        elapsed = max(now - self.phase_started, 0.001)
        rate = bytes_done / elapsed if bytes_done else 0.0
        remaining = max(bytes_total - bytes_done, 0)
        eta = remaining / rate if rate > 0 else 0.0
        percent = fraction * 100.0

        bar_width = 18 if self.width() < 76 else 24
        pieces = [
            f"{label}",
            f"[{self.bar(fraction, bar_width)}]",
            f"{percent:5.1f}%",
            f"{current:,}/{total:,}",
        ]
        if bytes_total:
            pieces.append(
                f"{self.human_bytes(bytes_done)}/{self.human_bytes(bytes_total)}"
            )
        if rate:
            pieces.append(f"{self.human_bytes(rate)}/s")
        if eta > 0.5 and current < total:
            pieces.append(f"eta {self.duration(eta)}")

        text = "  " + "  ".join(pieces)
        if self.tty:
            plain_width = len(re.sub(r"\x1b\[[0-9;]*m", "", text))
            padding = max(0, self.last_line_width - plain_width)
            sys.stderr.write("\r" + text + (" " * padding))
            sys.stderr.flush()
            self.last_line_width = plain_width
        elif force or current == total:
            self.line(text)

    def success(self, artifact_size: int, source_files: int, elapsed: float) -> None:
        marker = "✓" if self.unicode else "OK"
        self.line(
            f"{self.c(marker, self.green, self.bold)} "
            f"{self.c('sdump complete', self.green, self.bold)}"
        )
        self.note("source files", f"{source_files:,}")
        self.note("gzip", self.human_bytes(artifact_size))
        self.note("elapsed", self.duration(elapsed))
        self.note("local artifact", "deleted after verified publication", "good")

    def failure(self, message: str) -> None:
        marker = "✗" if self.unicode else "ERROR"
        self.line(
            f"{self.c(marker, self.red, self.bold)} "
            f"{self.c('sdump failed', self.red, self.bold)}"
        )
        self.line(f"  {message}")


ui = TerminalUI()


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


def is_structured_source(path: Path, relative: str) -> bool:
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    parent_parts = tuple(part.casefold() for part in Path(relative).parts[:-1])

    if name in structured_source_names or name in text_source_names:
        return True

    if suffix in {".json", ".jsonc", ".json5"}:
        return any(part in structured_source_dirs for part in parent_parts)

    if suffix == ".txt":
        return any(part in {"docs", "documentation"} for part in parent_parts)

    return False


def admitted(path: Path, root: Path, file_stat: os.stat_result) -> bool:
    relative = safe_relative(path, root)
    lowered_relative = relative.casefold()
    lowered_name = path.name.casefold()

    if relative in excluded_exact_relative_paths:
        return False

    parts = tuple(part.casefold() for part in Path(relative).parts[:-1])

    if path.suffix.casefold() in {".json", ".jsonc", ".json5"}:
        if "assets" in parts and file_stat.st_size > 8 * 1024 * 1024:
            return False
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

    if is_structured_source(path, relative):
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


def output_path(target: Path) -> Path:
    parent = Path(tempfile.mkdtemp(prefix="savant-sdump-"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S%f") + "z"
    return parent / f"sdump_{target.name}_{timestamp}.txt.gz"


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
    artifact_digest: Any,
) -> tuple[int, int, str]:
    try:
        before = candidate.absolute_path.stat()
    except OSError as error:
        raise StreamDumpError(f"unable to stat source {candidate.relative_path}: {error}") from error

    rendered = 0
    source_bytes = 0
    source_digest = hashlib.sha256()

    rendered += write_text(handle, "=== file ===\n", artifact_digest)
    rendered += write_json_line(handle, {
        "path": candidate.relative_path,
        "size": before.st_size,
        "mode": oct(stat.S_IMODE(before.st_mode)),
        "language": language(candidate.absolute_path),
    }, artifact_digest)
    rendered += write_text(handle, "=== content ===\n", artifact_digest)

    try:
        with candidate.absolute_path.open("rb") as source:
            decoder = __import__("codecs").getincrementaldecoder("utf-8")(errors="replace")
            while True:
                block = source.read(chunk_size)
                if not block:
                    break
                source_digest.update(block)
                source_bytes += len(block)
                text = decoder.decode(block, final=False)
                if text:
                    rendered += write_text(handle, text, artifact_digest)
            tail = decoder.decode(b"", final=True)
            if tail:
                rendered += write_text(handle, tail, artifact_digest)
        after = candidate.absolute_path.stat()
    except OSError as error:
        raise StreamDumpError(f"unable to read source {candidate.relative_path}: {error}") from error

    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or source_bytes != before.st_size
    ):
        raise StreamDumpError(f"source changed while dumping: {candidate.relative_path}")

    rendered += write_text(handle, "\n=== source sha256 ===\n", artifact_digest)
    rendered += write_text(handle, source_digest.hexdigest() + "\n", artifact_digest)
    rendered += write_text(handle, "=== /file ===\n\n", artifact_digest)
    return rendered, source_bytes, source_digest.hexdigest()

def stream_dump(target_raw: str) -> tuple[Path, list[Any], dict[str, Any]]:
    target = Path(target_raw).expanduser().resolve(strict=True)
    if not target.is_dir():
        raise StreamDumpError("sdump target must be a directory")

    ui.banner(target)
    ui.phase("discover", "pruning dependencies, generated state, recovery, and historical bulk")
    candidates, discovery = discover_source(target)
    if not candidates:
        raise StreamDumpError("no relevant Savant source admitted")

    ui.note("admitted", f"{len(candidates):,} files")
    ui.note("source", ui.human_bytes(discovery["candidate_bytes"]))
    ui.note("skipped", f"{discovery['skipped_count']:,} non-source entries")
    if discovery["candidate_bytes"] > 512 * 1024 * 1024:
        ui.note(
            "admission warning",
            "source corpus exceeds 512 MiB; generated material may still be admitted",
            "warn",
        )
    ui.phase("compress", "single-pass gzip stream")

    output = output_path(target)
    artifact_digest = hashlib.sha256()
    rendered_bytes = 0
    serialized_bytes = 0
    serialized_files = 0
    source_hashes: dict[str, str] = {}

    with gzip.open(output, "wt", encoding="utf-8", newline="\n", compresslevel=gzip_level) as handle:
        rendered_bytes += write_text(handle, "=== sdump manifest ===\n", artifact_digest)
        rendered_bytes += write_json_line(handle, {
            "schema": schema,
            "generated_at": now_iso(),
            "target_name": target.name,
            "purpose": "portable comprehensive current Savant source and architecture context",
            "source_admission": "current-source-positive-with-generated-dependency-history-exclusions",
            "source_files": len(candidates),
            "source_bytes": discovery["candidate_bytes"],
            "gzip_level": gzip_level,
            "authority_effect": "none",
            "filesystem_presence_establishes_authority": False,
        }, artifact_digest)
        rendered_bytes += write_text(handle, "=== /sdump manifest ===\n\n", artifact_digest)

        for index, candidate in enumerate(candidates, 1):
            rendered, source_bytes, source_sha = write_file_record(
                handle, candidate, artifact_digest
            )
            rendered_bytes += rendered
            serialized_bytes += source_bytes
            serialized_files += 1
            source_hashes[candidate.relative_path] = source_sha

            ui.progress(
                label="gzip",
                current=index,
                total=len(candidates),
                bytes_done=serialized_bytes,
                bytes_total=discovery["candidate_bytes"],
                force=index == len(candidates),
            )

        complete = (
            serialized_files == len(candidates)
            and serialized_bytes == discovery["candidate_bytes"]
        )
        rendered_bytes += write_text(handle, "\n=== sdump completeness ===\n", artifact_digest)
        rendered_bytes += write_json_line(handle, {
            "admitted_files": len(candidates),
            "serialized_files": serialized_files,
            "admitted_bytes": discovery["candidate_bytes"],
            "serialized_source_bytes": serialized_bytes,
            "complete": complete,
        }, artifact_digest)
        rendered_bytes += write_text(handle, "=== /sdump completeness ===\n", artifact_digest)

    ui.clear_progress()

    if not complete:
        raise StreamDumpError("strict source completeness invariant failed")

    return output, candidates, {
        "target": target,
        "discovery": discovery,
        "source_hashes": source_hashes,
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


def copy_authoritative_source(
    checkout: Path,
    candidates: Iterable[Any],
    source_hashes: dict[str, str],
) -> None:
    for index, candidate in enumerate(candidates, 1):
        destination = checkout / candidate.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with candidate.absolute_path.open("rb") as reader, destination.open("wb") as writer:
            while True:
                block = reader.read(chunk_size)
                if not block:
                    break
                writer.write(block)
                digest.update(block)
        expected = source_hashes.get(candidate.relative_path)
        if expected is None or digest.hexdigest() != expected:
            raise StreamDumpError(
                f"source changed after dump: {candidate.relative_path}"
            )
        shutil.copystat(candidate.absolute_path, destination, follow_symlinks=False)
        ui.progress(
            label="github",
            current=index,
            total=len(candidates) if hasattr(candidates, "__len__") else index,
            force=hasattr(candidates, "__len__") and index == len(candidates),
        )
    ui.clear_progress()

def push_source_to_github(
    candidates: list[Any],
    source_hashes: dict[str, str],
    environment: dict[str, str],
) -> dict[str, Any]:
    oversized = [
        candidate.relative_path
        for candidate in candidates
        if candidate.absolute_path.stat().st_size >= 100 * 1024 * 1024
    ]
    if oversized:
        raise StreamDumpError(
            "GitHub corpus contains file(s) at or above 100 MiB: "
            + ", ".join(oversized[:5])
        )

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

        copy_authoritative_source(checkout, candidates, source_hashes)

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
    candidates: list[Any],
    source_hashes: dict[str, str],
    environment: dict[str, str],
    artifact_sha256: str,
) -> dict[str, Any]:
    ui.phase("publish s3", f"s3://{s3_bucket}/{artifact.name}")
    s3_started = time.monotonic()
    s3_result = upload_to_s3(artifact, environment, artifact_sha256)
    ui.note(
        "s3 verified",
        f"{ui.human_bytes(s3_result['bytes'])}  sha256 {artifact_sha256[:12]}…  "
        f"{ui.duration(time.monotonic() - s3_started)}",
        "good",
    )

    ui.phase("publish github", f"{github_owner}/{github_repository}")
    github_started = time.monotonic()
    github_result = push_source_to_github(candidates, source_hashes, environment)
    ui.note(
        "github verified",
        f"{github_result['branch']} @ {github_result['commit'][:12]}  "
        f"{ui.duration(time.monotonic() - github_started)}",
        "good",
    )
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

    ui.phase("verify", "hashing completed gzip")
    artifact_sha256 = sha256_file(artifact)
    artifact_size = artifact.stat().st_size
    ui.note("gzip", ui.human_bytes(artifact_size))
    ui.note("sha256", artifact_sha256[:20] + "…")

    try:
        publication = publish(
            artifact,
            candidates,
            metadata["source_hashes"],
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
        "s3": publication["s3"],
        "github": publication["github"],
        "local_artifact_deleted": publication["local_artifact_deleted"],
        "authority_effect": "none",
    }

    ui.success(
        artifact_size=artifact_size,
        source_files=len(candidates),
        elapsed=time.monotonic() - ui.started,
    )
    if os.environ.get("SDUMP_JSON", "").casefold() in {"1", "true", "yes"}:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StreamDumpError as error:
        ui.failure(str(error))
        raise SystemExit(1)
