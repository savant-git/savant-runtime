from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


class GithubPushError(RuntimeError):
    pass


@dataclass(frozen=True)
class GithubPushResult:
    repository: str
    remote: str
    branch: str
    head: str
    pushed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "remote": self.remote,
            "branch": self.branch,
            "head": self.head,
            "pushed": self.pushed,
            "reason": self.reason,
        }


def _git() -> str:
    executable = shutil.which("git")

    if not executable:
        raise GithubPushError(
            "git executable was not found"
        )

    return executable


def _run(
    repository: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [
            _git(),
            "-C",
            str(repository),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    if check and process.returncode != 0:
        message = (
            process.stderr.strip()
            or process.stdout.strip()
            or "git command failed"
        )
        raise GithubPushError(message)

    return process


def _repository_root(path: Path) -> Path:
    resolved = path.resolve(strict=False)

    process = _run(
        resolved,
        "rev-parse",
        "--show-toplevel",
    )

    root = Path(process.stdout.strip()).resolve(
        strict=False
    )

    if not root.is_dir():
        raise GithubPushError(
            f"git repository root not found: {root}"
        )

    return root


def _branch(repository: Path) -> str:
    process = _run(
        repository,
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
        check=False,
    )

    branch = process.stdout.strip()

    if process.returncode != 0 or not branch:
        raise GithubPushError(
            "cannot push sdump source from a detached HEAD"
        )

    return branch


def _head(repository: Path) -> str:
    return _run(
        repository,
        "rev-parse",
        "HEAD",
    ).stdout.strip()


def _upstream(
    repository: Path,
    branch: str,
) -> tuple[str, str]:
    process = _run(
        repository,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )

    upstream = process.stdout.strip()

    if process.returncode == 0 and upstream:
        if "/" not in upstream:
            raise GithubPushError(
                f"invalid git upstream: {upstream}"
            )

        remote, remote_branch = upstream.split(
            "/",
            1,
        )
        return remote, remote_branch

    remotes = [
        line.strip()
        for line in _run(
            repository,
            "remote",
        ).stdout.splitlines()
        if line.strip()
    ]

    if "origin" in remotes:
        return "origin", branch

    if len(remotes) == 1:
        return remotes[0], branch

    raise GithubPushError(
        "no unambiguous git upstream is configured"
    )


def _remote_url(
    repository: Path,
    remote: str,
) -> str:
    return _run(
        repository,
        "remote",
        "get-url",
        remote,
    ).stdout.strip()


def _github_remote(url: str) -> bool:
    normalized = url.casefold()
    return (
        "github.com/" in normalized
        or "github.com:" in normalized
    )


def push_current_head(
    path: Path,
) -> GithubPushResult:
    repository = _repository_root(path)
    branch = _branch(repository)
    head = _head(repository)

    remote, remote_branch = _upstream(
        repository,
        branch,
    )

    remote_url = _remote_url(
        repository,
        remote,
    )

    if not _github_remote(remote_url):
        raise GithubPushError(
            "configured git remote is not GitHub; "
            "sdump will not push to an unverified provider"
        )

    push = _run(
        repository,
        "push",
        "--porcelain",
        remote,
        f"HEAD:{remote_branch}",
        check=False,
    )

    if push.returncode != 0:
        message = (
            push.stderr.strip()
            or push.stdout.strip()
            or "git push failed"
        )
        raise GithubPushError(message)

    verify = _run(
        repository,
        "ls-remote",
        "--heads",
        remote,
        f"refs/heads/{remote_branch}",
    )

    remote_head = ""

    for line in verify.stdout.splitlines():
        fields = line.split()

        if fields:
            remote_head = fields[0].strip()
            break

    if remote_head != head:
        raise GithubPushError(
            "GitHub verification failed: remote branch "
            "does not match local HEAD"
        )

    return GithubPushResult(
        repository=str(repository),
        remote=remote,
        branch=remote_branch,
        head=head,
        pushed=True,
        reason="GitHub branch verified at local HEAD",
    )
