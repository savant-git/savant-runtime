#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

SCAFFOLD_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "scaffolds"
)

CONTENT_ROOT = (
    ROOT
    / "reports"
    / "identity_quality"
    / "promotion"
    / "content"
)

VOLATILE_FIELDS = {
    "generated_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}

CONTENT_ROLES = (
    "contracts",
    "runtime",
    "tests",
    "controller",
)

SUPPORTED_KINDS = {
    "exile",
    "prodigal",
    "quirk",
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        value,
        encoding="utf-8",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def safe_key(
    value: str,
) -> str:
    return re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    ).strip("_")


def safe_python_name(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^A-Za-z0-9_]+",
        "_",
        value,
    ).lower()

    normalized = re.sub(
        r"_+",
        "_",
        normalized,
    ).strip("_")

    if not normalized:
        raise ValueError(
            "Cannot derive Python identifier."
        )

    if normalized[0].isdigit():
        normalized = (
            "_"
            + normalized
        )

    return normalized


def class_name(
    value: str,
) -> str:
    return "".join(
        segment.capitalize()
        for segment in safe_python_name(
            value
        ).split("_")
    )


def latest_scaffold_paths() -> list[Path]:
    if not SCAFFOLD_ROOT.is_dir():
        return []

    return sorted(
        (
            path
            for path in SCAFFOLD_ROOT.glob(
                "*/latest.json"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.as_posix(),
        ),
        reverse=True,
    )


def latest_scaffold_path() -> Path:
    paths = latest_scaffold_paths()

    if not paths:
        raise FileNotFoundError(
            "No promotion scaffold exists."
        )

    return paths[0]


def resolve_scaffold_path(
    declared: Path | None,
) -> Path:
    if declared is None:
        return latest_scaffold_path()

    path = declared.expanduser()

    if not path.is_absolute():
        path = ROOT / path

    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def validate_scaffold(
    scaffold: dict[str, Any],
) -> None:
    subject = scaffold.get(
        "subject"
    )

    if not isinstance(subject, dict):
        raise ValueError(
            "Scaffold has no subject."
        )

    identifier = subject.get(
        "id"
    )

    if (
        not isinstance(identifier, str)
        or not identifier.strip()
    ):
        raise ValueError(
            "Subject identifier is missing."
        )

    kind = subject.get(
        "kind"
    )

    if kind not in SUPPORTED_KINDS:
        raise ValueError(
            f"Unsupported subject kind: {kind}"
        )

    target_layout = scaffold.get(
        "target_layout"
    )

    if not isinstance(
        target_layout,
        dict,
    ):
        raise ValueError(
            "Scaffold has no target layout."
        )

    for role in CONTENT_ROLES:
        path = target_layout.get(
            role
        )

        if (
            not isinstance(path, str)
            or not path.strip()
        ):
            raise ValueError(
                f"Target layout is missing: {role}"
            )


def subject_name(
    scaffold: dict[str, Any],
) -> str:
    subject = scaffold[
        "subject"
    ]

    for field in (
        "name",
        "python_name",
        "id",
    ):
        value = subject.get(
            field
        )

        if (
            isinstance(value, str)
            and value.strip()
        ):
            if field == "id":
                return value.rsplit(
                    ".",
                    1,
                )[-1]

            return value.strip()

    raise ValueError(
        "Cannot derive subject name."
    )


def source_authority(
    scaffold: dict[str, Any],
) -> dict[str, Any]:
    authority = scaffold.get(
        "authority"
    )

    if not isinstance(
        authority,
        dict,
    ):
        return {}

    primitives = authority.get(
        "primitives"
    )

    if isinstance(
        primitives,
        dict,
    ):
        return primitives

    return authority


def purpose_text(
    scaffold: dict[str, Any],
) -> str:
    authority = source_authority(
        scaffold
    )

    purpose = authority.get(
        "purpose"
    )

    if isinstance(purpose, str):
        return purpose.strip()

    if isinstance(purpose, dict):
        for field in (
            "summary",
            "statement",
            "description",
        ):
            value = purpose.get(
                field
            )

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

    return (
        "Execute only capabilities explicitly admitted "
        "by the authoritative identity definition."
    )


def capability_ids(
    scaffold: dict[str, Any],
) -> tuple[str, ...]:
    authority = source_authority(
        scaffold
    )

    capabilities = authority.get(
        "capabilities"
    )

    values: list[str] = []

    if isinstance(capabilities, list):
        for capability in capabilities:
            if isinstance(capability, str):
                values.append(
                    capability
                )

            elif isinstance(
                capability,
                dict,
            ):
                identifier = capability.get(
                    "id"
                )

                if isinstance(
                    identifier,
                    str,
                ):
                    values.append(
                        identifier
                    )

    return tuple(
        sorted(
            set(values)
        )
    )


def contract_content(
    scaffold: dict[str, Any],
) -> str:
    name = safe_python_name(
        subject_name(scaffold)
    )

    title = class_name(name)

    identifier = scaffold[
        "subject"
    ][
        "id"
    ]

    capabilities = capability_ids(
        scaffold
    )

    capability_literal = repr(
        capabilities
    )

    return f'''#!/usr/bin/env python3
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTRACT_VERSION = "1.0.0"
SUBJECT_ID = {identifier!r}
DECLARED_CAPABILITIES = {capability_literal}


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class AuthorityState(StrEnum):
    PROPOSED = "proposed"
    OBSERVED = "observed"
    ACCEPTED = "accepted"
    AUTHORITATIVE = "authoritative"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ExecutionMode(StrEnum):
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"


class SourceReference(StrictModel):
    source_id: str
    source_kind: str
    source_path: str | None = None
    source_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{{64}}$",
    )
    authority: AuthorityState = AuthorityState.UNKNOWN
    captured_at: str | None = None


class ProvenanceEnvelope(StrictModel):
    sources: tuple[SourceReference, ...] = ()
    transformations: tuple[str, ...] = ()
    generated_by: str
    generated_at: str
    contract_version: str = CONTRACT_VERSION


class {title}Policy(StrictModel):
    execution_mode: ExecutionMode = ExecutionMode.PLAN
    allowed_capabilities: tuple[str, ...] = ()
    fail_closed: bool = True
    deterministic: bool = True
    network_access: bool = False
    filesystem_read: bool = False
    filesystem_write: bool = False
    subprocess_access: bool = False
    secret_access: bool = False

    @model_validator(mode="after")
    def enforce_boundary(
        self,
    ) -> "{title}Policy":
        undeclared = [
            capability
            for capability in self.allowed_capabilities
            if capability not in DECLARED_CAPABILITIES
        ]

        if undeclared:
            raise ValueError(
                "Undeclared capabilities requested: "
                + ", ".join(
                    sorted(undeclared)
                )
            )

        if (
            self.network_access
            or self.filesystem_read
            or self.filesystem_write
            or self.subprocess_access
            or self.secret_access
        ):
            raise ValueError(
                "The baseline runtime grants no external authority."
            )

        return self


class {title}Request(StrictModel):
    request_id: str
    purpose: str
    operation: str
    payload: dict[str, Any] = Field(
        default_factory=dict
    )
    policy: {title}Policy
    authority: AuthorityState = AuthorityState.OBSERVED
    provenance: ProvenanceEnvelope


class FailureRecord(StrictModel):
    failure_id: str
    code: str
    message: str
    stage: str
    recoverable: bool
    details: dict[str, Any] = Field(
        default_factory=dict
    )
    provenance: ProvenanceEnvelope


class {title}Projection(StrictModel):
    projection_id: str
    subject_id: Literal[{identifier!r}]
    request_id: str
    operation: str
    purpose: str
    payload_digest: str = Field(
        pattern=r"^[0-9a-f]{{64}}$"
    )
    admitted_capabilities: tuple[str, ...]
    authority: AuthorityState = AuthorityState.PROPOSED
    deterministic: bool = True
    provenance: ProvenanceEnvelope


class {title}Result(StrictModel):
    operation: Literal["run", "validate"]
    passed: bool
    request_id: str
    projection: {title}Projection | None = None
    failure: FailureRecord | None = None
    result_digest: str = Field(
        pattern=r"^[0-9a-f]{{64}}$"
    )
    metrics: dict[str, int | float | str | bool] = Field(
        default_factory=dict
    )
    provenance: ProvenanceEnvelope
'''


def runtime_content(
    scaffold: dict[str, Any],
) -> str:
    name = safe_python_name(
        subject_name(scaffold)
    )

    title = class_name(name)

    identifier = scaffold[
        "subject"
    ][
        "id"
    ]

    purpose = purpose_text(
        scaffold
    )

    return f'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(__file__).resolve().parent
SUBJECT_ROOT = RUNTIME_ROOT.parent
CONTRACTS_ROOT = SUBJECT_ROOT / "contracts"

if str(CONTRACTS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(CONTRACTS_ROOT),
    )

from {name}_contracts import (  # noqa: E402
    AuthorityState,
    DECLARED_CAPABILITIES,
    FailureRecord,
    ProvenanceEnvelope,
    {title}Projection,
    {title}Request,
    {title}Result,
)


RUNTIME_ID = {identifier + ".runtime"!r}
RUNTIME_VERSION = "1.0.0"
AUTHORITATIVE_PURPOSE = {purpose!r}

VOLATILE_FIELDS = {{
    "duration_seconds",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "wall_clock_seconds",
    "timestamp",
}}


def canonical_bytes(
    value: Any,
) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json"
        )

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(value)
    ).hexdigest()


def deterministic_projection(
    value: Any,
) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(
            mode="json"
        )

    if isinstance(value, dict):
        return {{
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }}

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def build_provenance(
    request: {title}Request,
    transformations: tuple[str, ...],
) -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        sources=request.provenance.sources,
        transformations=transformations,
        generated_by=f"{{RUNTIME_ID}}@{{RUNTIME_VERSION}}",
        generated_at=request.provenance.generated_at,
    )


def run(
    request: {title}Request,
) -> {title}Result:
    started = time.perf_counter()

    provenance = build_provenance(
        request,
        (
            "validate_request",
            "resolve_declared_capabilities",
            "project_authoritative_primitives",
            "emit_deterministic_result",
        ),
    )

    try:
        admitted = tuple(
            sorted(
                request.policy.allowed_capabilities
            )
        )

        projection_body = {{
            "subject_id": {identifier!r},
            "request_id": request.request_id,
            "operation": request.operation,
            "purpose": request.purpose,
            "payload_digest": digest(
                deterministic_projection(
                    request.payload
                )
            ),
            "admitted_capabilities": admitted,
            "authority": AuthorityState.PROPOSED.value,
        }}

        projection_digest = digest(
            projection_body
        )

        projection = {title}Projection(
            projection_id=(
                f"{name}-projection-"
                f"{{projection_digest[:20]}}"
            ),
            subject_id={identifier!r},
            request_id=request.request_id,
            operation=request.operation,
            purpose=request.purpose,
            payload_digest=projection_body[
                "payload_digest"
            ],
            admitted_capabilities=admitted,
            authority=AuthorityState.PROPOSED,
            deterministic=True,
            provenance=provenance,
        )

        result_body = {{
            "operation": "run",
            "passed": True,
            "request_id": request.request_id,
            "projection": deterministic_projection(
                projection
            ),
        }}

        return {title}Result(
            operation="run",
            passed=True,
            request_id=request.request_id,
            projection=projection,
            result_digest=digest(
                result_body
            ),
            metrics={{
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "declared_capability_count": len(
                    DECLARED_CAPABILITIES
                ),
                "admitted_capability_count": len(
                    admitted
                ),
                "passed": True,
            }},
            provenance=provenance,
        )

    except Exception as exc:
        failure_body = {{
            "request_id": request.request_id,
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }}

        failure = FailureRecord(
            failure_id=(
                f"{name}-failure-"
                f"{{digest(failure_body)[:20]}}"
            ),
            code={identifier + ".runtime.failure"!r},
            message=str(exc),
            stage="run",
            recoverable=True,
            details={{
                "exception_type": type(exc).__name__,
            }},
            provenance=provenance,
        )

        return {title}Result(
            operation="run",
            passed=False,
            request_id=request.request_id,
            failure=failure,
            result_digest=digest(
                {{
                    "operation": "run",
                    "passed": False,
                    "request_id": request.request_id,
                    "failure": deterministic_projection(
                        failure
                    ),
                }}
            ),
            metrics={{
                "duration_seconds": (
                    time.perf_counter()
                    - started
                ),
                "passed": False,
            }},
            provenance=provenance,
        )


def example_request() -> {title}Request:
    generated_at = (
        "2026-08-01T00:00:00+00:00"
    )

    return {title}Request(
        request_id={name + "-example-request"!r},
        purpose=AUTHORITATIVE_PURPOSE,
        operation="project",
        payload={{
            "subject": {identifier!r},
        }},
        policy={{
            "execution_mode": "plan",
            "allowed_capabilities": [],
            "fail_closed": True,
            "deterministic": True,
            "network_access": False,
            "filesystem_read": False,
            "filesystem_write": False,
            "subprocess_access": False,
            "secret_access": False,
        }},
        authority=AuthorityState.OBSERVED,
        provenance={{
            "sources": [],
            "transformations": [],
            "generated_by": {name + "-example"!r},
            "generated_at": generated_at,
            "contract_version": "1.0.0",
        }},
    )


def load_request(
    path: Path | None,
) -> {title}Request:
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(
            encoding="utf-8"
        )

    return {title}Request.model_validate_json(
        raw
    )


def write_result(
    result: {title}Result,
    output: Path | None,
) -> None:
    rendered = json.dumps(
        result.model_dump(
            mode="json"
        ),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\\n"

    if output is None:
        print(
            rendered,
            end="",
        )
        return

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        rendered,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description={purpose!r}
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run"
    )

    run_parser.add_argument(
        "--input",
        type=Path,
    )

    run_parser.add_argument(
        "--output",
        type=Path,
    )

    example_parser = subparsers.add_parser(
        "example"
    )

    example_parser.add_argument(
        "--output",
        type=Path,
    )

    subparsers.add_parser(
        "schema"
    )

    args = parser.parse_args()

    if args.command == "run":
        result = run(
            load_request(
                args.input
            )
        )

        write_result(
            result,
            args.output,
        )

        return (
            0
            if result.passed
            else 1
        )

    if args.command == "example":
        request = example_request()

        rendered = json.dumps(
            request.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\\n"

        if args.output is None:
            print(
                rendered,
                end="",
            )
        else:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            args.output.write_text(
                rendered,
                encoding="utf-8",
            )

        return 0

    if args.command == "schema":
        print(
            json.dumps(
                {{
                    "request": (
                        {title}Request
                        .model_json_schema()
                    ),
                    "result": (
                        {title}Result
                        .model_json_schema()
                    ),
                }},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
'''


def tests_content(
    scaffold: dict[str, Any],
) -> str:
    name = safe_python_name(
        subject_name(scaffold)
    )

    title = class_name(name)

    identifier = scaffold[
        "subject"
    ][
        "id"
    ]

    return f'''#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypothesis import (
    given,
    strategies as st,
)


SUBJECT_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    SUBJECT_ROOT
    / "runtime"
)

CONTRACTS_ROOT = (
    SUBJECT_ROOT
    / "contracts"
)

for path in (
    RUNTIME_ROOT,
    CONTRACTS_ROOT,
):
    if str(path) not in sys.path:
        sys.path.insert(
            0,
            str(path),
        )


from {name}_contracts import (  # noqa: E402
    AuthorityState,
    {title}Request,
)
from {name}_runtime import (  # noqa: E402
    canonical_bytes,
    deterministic_projection,
    example_request,
    run,
)


def test_example_request_succeeds() -> None:
    result = run(
        example_request()
    )

    assert result.passed is True
    assert result.projection is not None
    assert (
        result.projection.subject_id
        == {identifier!r}
    )


def test_equal_requests_produce_equal_result_digests() -> None:
    request = example_request()

    first = run(request)
    second = run(request)

    assert (
        first.result_digest
        == second.result_digest
    )


def test_result_preserves_provenance() -> None:
    result = run(
        example_request()
    )

    assert result.provenance.generated_by
    assert result.provenance.generated_at
    assert result.provenance.transformations


def test_projection_remains_proposed() -> None:
    result = run(
        example_request()
    )

    assert result.projection is not None
    assert (
        result.projection.authority
        == AuthorityState.PROPOSED
    )


def test_runtime_rejects_undeclared_capability() -> None:
    value = example_request().model_dump(
        mode="json"
    )

    value["policy"][
        "allowed_capabilities"
    ] = [
        "undeclared.capability"
    ]

    try:
        {title}Request.model_validate(
            value
        )
    except ValueError:
        return

    raise AssertionError(
        "Runtime admitted an undeclared capability."
    )


def test_runtime_rejects_external_authority() -> None:
    value = example_request().model_dump(
        mode="json"
    )

    value["policy"][
        "network_access"
    ] = True

    try:
        {title}Request.model_validate(
            value
        )
    except ValueError:
        return

    raise AssertionError(
        "Runtime admitted undeclared network authority."
    )


def test_volatile_telemetry_does_not_change_identity() -> None:
    request = example_request()

    first = run(request)
    second = run(request)

    first_value = deterministic_projection(
        first
    )
    second_value = deterministic_projection(
        second
    )

    assert (
        canonical_bytes(first_value)
        == canonical_bytes(second_value)
    )


@given(
    value=st.text(
        alphabet=st.characters(
            blacklist_categories=(
                "Cs",
            )
        ),
        min_size=1,
        max_size=200,
    )
)
def test_canonical_serialization_is_stable(
    value: str,
) -> None:
    payload = {{
        "value": value,
    }}

    first = canonical_bytes(
        payload
    )

    second = canonical_bytes(
        json.loads(first)
    )

    assert first == second
'''


def controller_content(
    scaffold: dict[str, Any],
) -> str:
    name = safe_python_name(
        subject_name(scaffold)
    )

    target_layout = scaffold[
        "target_layout"
    ]

    runtime_path = target_layout[
        "runtime"
    ]

    tests_path = target_layout[
        "tests"
    ]

    reports_path = target_layout[
        "reports"
    ]

    return f'''#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path("/root/savant-runtime")

PYTHON = (
    ROOT
    / "bin"
    / "identity-quality-python"
)

RUNTIME = (
    ROOT
    / {runtime_path!r}
)

TESTS = (
    ROOT
    / {tests_path!r}
)

REPORT_ROOT = (
    ROOT
    / {reports_path!r}
)


def execute(
    command: list[str],
) -> int:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
    ).returncode


def usage() -> int:
    print(
        """
{name}ctl example [--output PATH]
{name}ctl run --input PATH [--output PATH]
{name}ctl schema
{name}ctl test
{name}ctl verify
{name}ctl status
"""
    )

    return 0


def status() -> int:
    result = {{
        "runtime": str(RUNTIME),
        "runtime_exists": RUNTIME.is_file(),
        "tests": str(TESTS),
        "tests_exist": TESTS.is_file(),
        "report_root": str(REPORT_ROOT),
        "report_root_exists": REPORT_ROOT.is_dir(),
    }}

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


def main() -> int:
    arguments = sys.argv[1:]

    if not arguments:
        return usage()

    command = arguments[0]
    remaining = arguments[1:]

    if command in {{
        "help",
        "--help",
        "-h",
    }}:
        return usage()

    if command == "example":
        return execute(
            [
                str(PYTHON),
                str(RUNTIME),
                "example",
                *remaining,
            ]
        )

    if command == "run":
        return execute(
            [
                str(PYTHON),
                str(RUNTIME),
                "run",
                *remaining,
            ]
        )

    if command == "schema":
        return execute(
            [
                str(PYTHON),
                str(RUNTIME),
                "schema",
            ]
        )

    if command == "test":
        return execute(
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                str(TESTS),
            ]
        )

    if command == "verify":
        REPORT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        example = (
            REPORT_ROOT
            / "example_request.json"
        )

        result = (
            REPORT_ROOT
            / "example_result.json"
        )

        stages = [
            [
                str(PYTHON),
                "-m",
                "py_compile",
                str(RUNTIME),
                str(TESTS),
            ],
            [
                str(PYTHON),
                "-m",
                "pytest",
                "-q",
                str(TESTS),
            ],
            [
                str(PYTHON),
                str(RUNTIME),
                "example",
                "--output",
                str(example),
            ],
            [
                str(PYTHON),
                str(RUNTIME),
                "run",
                "--input",
                str(example),
                "--output",
                str(result),
            ],
        ]

        for stage in stages:
            returncode = execute(
                stage
            )

            if returncode:
                return returncode

        print(
            str(result)
        )

        return 0

    if command == "status":
        return status()

    print(
        f"ERROR: unknown command: {{command}}",
        file=sys.stderr,
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
'''


def build_file_record(
    role: str,
    path: str,
    content: str,
) -> dict[str, Any]:
    target = (
        ROOT
        / path
    ).resolve()

    existing_sha256 = (
        sha256_path(target)
        if target.is_file()
        else None
    )

    operation = (
        "extend"
        if target.is_file()
        else "create"
    )

    return {
        "role": role,
        "path": path,
        "absolute_path": str(target),
        "operation": operation,
        "existing": target.is_file(),
        "existing_sha256": existing_sha256,
        "content": content,
        "content_sha256": sha256_text(
            content
        ),
        "replace_existing": False,
        "requires_review": target.is_file(),
    }


def build_bundle(
    scaffold_path: Path,
) -> dict[str, Any]:
    scaffold = load_json(
        scaffold_path
    )

    validate_scaffold(
        scaffold
    )

    target_layout = scaffold[
        "target_layout"
    ]

    generated = {
        "contracts": contract_content(
            scaffold
        ),
        "runtime": runtime_content(
            scaffold
        ),
        "tests": tests_content(
            scaffold
        ),
        "controller": controller_content(
            scaffold
        ),
    }

    files = [
        build_file_record(
            role,
            target_layout[role],
            generated[role],
        )
        for role in CONTENT_ROLES
    ]

    bundle: dict[str, Any] = {
        "schema": (
            "savant://identity-quality/"
            "promotion-content-bundle/1.0.0"
        ),
        "operation": (
            "build_promotion_content_bundle"
        ),
        "generated_at": utc_now(),
        "scaffold": {
            "path": relative_path(
                scaffold_path
            ),
            "sha256": sha256_path(
                scaffold_path
            ),
            "digest": scaffold.get(
                "digest"
            ),
        },
        "subject": scaffold[
            "subject"
        ],
        "authority": scaffold.get(
            "authority",
            {}
        ),
        "files": files,
        "admission": {
            "ready": all(
                file_record[
                    "content_sha256"
                ]
                for file_record in files
            ),
            "existing_file_count": sum(
                file_record[
                    "existing"
                ]
                for file_record in files
            ),
            "review_required_count": sum(
                file_record[
                    "requires_review"
                ]
                for file_record in files
            ),
            "automatic_overwrite_allowed": False,
        },
        "constraints": [
            (
                "Existing files may only be extended after review."
            ),
            (
                "No existing authoritative file may be replaced."
            ),
            (
                "Generated content is provisional until admitted."
            ),
            (
                "Runtime behavior is limited to deterministic "
                "projection of authoritative primitives."
            ),
            (
                "No external authority is granted."
            ),
            (
                "All generated files expose provenance and "
                "deterministic identity."
            ),
        ],
    }

    bundle[
        "digest"
    ] = digest(
        deterministic_projection(
            bundle
        )
    )

    return bundle


def markdown(
    bundle: dict[str, Any],
) -> str:
    lines = [
        "# Identity Promotion Content Bundle",
        "",
        (
            f"- Generated: "
            f"`{bundle['generated_at']}`"
        ),
        (
            f"- Subject: "
            f"`{bundle['subject']['id']}`"
        ),
        (
            f"- Digest: "
            f"`{bundle['digest']}`"
        ),
        (
            f"- Ready: "
            f"**{bundle['admission']['ready']}**"
        ),
        (
            f"- Existing files: "
            f"**{bundle['admission']['existing_file_count']}**"
        ),
        (
            f"- Reviews required: "
            f"**{bundle['admission']['review_required_count']}**"
        ),
        "",
        "## Files",
        "",
    ]

    for record in bundle[
        "files"
    ]:
        lines.extend(
            [
                (
                    f"### `{record['role']}`"
                ),
                "",
                (
                    f"- Path: "
                    f"`{record['path']}`"
                ),
                (
                    f"- Operation: "
                    f"`{record['operation']}`"
                ),
                (
                    f"- Existing: "
                    f"`{record['existing']}`"
                ),
                (
                    f"- Review required: "
                    f"`{record['requires_review']}`"
                ),
                (
                    f"- Content SHA-256: "
                    f"`{record['content_sha256']}`"
                ),
                "",
            ]
        )

    return "\n".join(
        lines
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build provisional implementation content "
            "for the current identity promotion scaffold."
        )
    )

    parser.add_argument(
        "--scaffold",
        type=Path,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=CONTENT_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        scaffold_path = resolve_scaffold_path(
            arguments.scaffold
        )

        bundle = build_bundle(
            scaffold_path
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "build_promotion_content_bundle"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    subject_key = safe_key(
        bundle[
            "subject"
        ][
            "id"
        ]
    )

    output_root = (
        arguments.output_root
        .expanduser()
        .resolve()
        / subject_key
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    json_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-content-bundle.json"
        )
    )

    markdown_path = (
        output_root
        / (
            f"{run_id}__"
            "promotion-content-bundle.md"
        )
    )

    latest_json = (
        output_root
        / "latest.json"
    )

    latest_markdown = (
        output_root
        / "latest.md"
    )

    write_json(
        json_path,
        bundle,
    )

    write_json(
        latest_json,
        bundle,
    )

    rendered = markdown(
        bundle
    )

    write_text(
        markdown_path,
        rendered,
    )

    write_text(
        latest_markdown,
        rendered,
    )

    manifest = {
        "generated_at": (
            bundle[
                "generated_at"
            ]
        ),
        "subject": (
            bundle[
                "subject"
            ][
                "id"
            ]
        ),
        "bundle_digest": (
            bundle[
                "digest"
            ]
        ),
        "files": {
            json_path.name: (
                sha256_path(
                    json_path
                )
            ),
            markdown_path.name: (
                sha256_path(
                    markdown_path
                )
            ),
            latest_json.name: (
                sha256_path(
                    latest_json
                )
            ),
            latest_markdown.name: (
                sha256_path(
                    latest_markdown
                )
            ),
        },
    }

    manifest_path = (
        output_root
        / (
            f"{run_id}__manifest.json"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    passed = bool(
        bundle[
            "admission"
        ][
            "ready"
        ]
    )

    print(
        json.dumps(
            {
                "operation": (
                    "build_promotion_content_bundle"
                ),
                "passed": passed,
                "subject": bundle[
                    "subject"
                ],
                "digest": bundle[
                    "digest"
                ],
                "admission": bundle[
                    "admission"
                ],
                "reports": {
                    "json": str(
                        json_path
                    ),
                    "markdown": str(
                        markdown_path
                    ),
                    "latest_json": str(
                        latest_json
                    ),
                    "latest_markdown": str(
                        latest_markdown
                    ),
                    "manifest": str(
                        manifest_path
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not passed
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
