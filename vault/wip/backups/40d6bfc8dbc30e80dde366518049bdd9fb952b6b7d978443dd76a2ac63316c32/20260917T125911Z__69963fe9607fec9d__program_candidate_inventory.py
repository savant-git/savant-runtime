from collections import defaultdict
from pathlib import Path


ROOT = Path("/root/savant-runtime")

EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".cs",
    ".rb",
    ".php",
    ".lua",
    ".pl",
    ".r",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".sql",
    ".graphql",
    ".gql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    ".xml",
    ".xsd",
    ".tf",
    ".tfvars",
    ".gradle",
    ".properties",
}

FILENAMES = {
    "dockerfile",
    "containerfile",
    "makefile",
    "procfile",
    "rakefile",
    "gemfile",
    "gemfile.lock",
    "pipfile",
    "pipfile.lock",
    "justfile",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
    "pyproject.toml",
    "requirements.txt",
    "constraints.txt",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lock",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "composer.json",
    "composer.lock",
    "deno.json",
    "deno.jsonc",
    "bunfig.toml",
}


def excluded(parts: tuple[str, ...]) -> bool:
    folded = [
        part.casefold()
        for part in parts
    ]

    for part in folded:
        if (
            part == "node_modules"
            or part == "site-packages"
            or part == "__pycache__"
            or part.startswith(".venv")
            or part == "venv"
            or part.startswith("venv-")
            or part
            in {
                ".git",
                ".hg",
                ".svn",
                ".pytest_cache",
                ".hypothesis",
                ".mypy_cache",
                ".ruff_cache",
                ".tox",
                ".nox",
                ".cache",
                ".next",
                ".nuxt",
                ".svelte-kit",
                ".turbo",
                ".vercel",
                ".parcel-cache",
                ".vite",
                "vendor",
                "dist",
                "build",
                "coverage",
                "target",
                "out",
                "obj",
                "tmp",
                "temp",
            }
        ):
            return True

    return False


def main() -> None:
    files: list[
        tuple[int, str]
    ] = []

    by_top: dict[
        str,
        list[int],
    ] = defaultdict(
        lambda: [0, 0]
    )

    for path in ROOT.rglob("*"):
        try:
            if (
                not path.is_file()
                or path.is_symlink()
            ):
                continue

            relative = path.relative_to(
                ROOT
            )

            if excluded(
                relative.parts
            ):
                continue

            name = (
                path.name.casefold()
            )

            suffix = (
                path.suffix.casefold()
            )

            if (
                name not in FILENAMES
                and suffix
                not in EXTENSIONS
            ):
                continue

            size = path.stat().st_size

            files.append(
                (
                    size,
                    relative.as_posix(),
                )
            )

            top = (
                relative.parts[0]
                if relative.parts
                else "."
            )

            by_top[top][0] += size
            by_top[top][1] += 1

        except (
            OSError,
            PermissionError,
        ):
            continue

    print(
        "\nTOP-LEVEL "
        "PROGRAM-CANDIDATE BULK\n"
    )

    ordered_top = sorted(
        by_top.items(),
        key=lambda item: (
            item[1][0]
        ),
        reverse=True,
    )

    for (
        name,
        (
            size,
            count,
        ),
    ) in ordered_top[:30]:
        print(
            f"{size / 1048576:10.2f} MiB  "
            f"{count:7d} files  "
            f"{name}"
        )

    print(
        "\n100 LARGEST "
        "PROGRAM CANDIDATES\n"
    )

    for (
        size,
        path,
    ) in sorted(
        files,
        reverse=True,
    )[:100]:
        print(
            f"{size / 1048576:10.2f} MiB  "
            f"{path}"
        )

    total_bytes = sum(
        size
        for size, _ in files
    )

    print("\nTOTAL\n")

    print(
        f"{total_bytes / 1048576:.2f} MiB"
    )

    print(
        f"{len(files)} files"
    )


if __name__ == "__main__":
    main()
