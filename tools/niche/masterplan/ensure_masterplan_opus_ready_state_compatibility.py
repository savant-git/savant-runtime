#!/usr/bin/env python3
"""
Ensure compatibility between READY_STATES and TERMINAL_READY_STATES.

READY_STATES remains the single substantiated mapping.
TERMINAL_READY_STATES is retained as an identity alias for existing tests and
dependents.

The repair is idempotent, preserves the complete baseline, validates syntax,
verifies identity at runtime, and restores the baseline on failure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import py_compile
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Final


ROOT: Final[Path] = Path(
    "/root/savant-runtime"
)

TARGET: Final[Path] = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
    / "inspect_masterplan_opus_binding_state.py"
)

REPORT_ROOT: Final[Path] = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "opus-ready-state-compatibility"
)

STATE_FIELDS_ANCHOR: Final[str] = """\
STATE_FIELDS: Final[
    dict[str, tuple[str, ...]]
] = {
"""

ALIAS_BLOCK: Final[str] = """\
# Historical public name retained as an identity projection.
# READY_STATES is the single substantiated mapping.
TERMINAL_READY_STATES: Final[
    dict[str, tuple[str, ...]]
] = READY_STATES


"""

READY_DECLARATION_MARKER: Final[str] = (
    "READY_STATES: Final["
)

TERMINAL_DECLARATION_MARKER: Final[str] = (
    "TERMINAL_READY_STATES: Final["
)

RECURSIVE_LOADER_MARKERS: Final[
    tuple[str, ...]
] = (
    "inspector = load_module()",
    "class MasterplanOpusBindingStateTests",
    "unittest.TestCase",
)


class CompatibilityError(RuntimeError):
    """Raised when compatibility cannot be established safely."""


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def pretty_json_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def atomic_write(
    path: Path,
    content: bytes,
    mode: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                content
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        temporary.chmod(
            mode
        )

        temporary.replace(
            path
        )

        directory_descriptor = os.open(
            path.parent,
            os.O_DIRECTORY,
        )

        try:
            os.fsync(
                directory_descriptor
            )
        finally:
            os.close(
                directory_descriptor
            )

    except BaseException:
        temporary.unlink(
            missing_ok=True
        )
        raise


def read_target() -> tuple[bytes, str]:
    if not TARGET.is_file():
        raise CompatibilityError(
            f"target missing: {TARGET}"
        )

    raw = TARGET.read_bytes()

    if not raw:
        raise CompatibilityError(
            f"target is empty: {TARGET}"
        )

    try:
        text = raw.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise CompatibilityError(
            f"target is not valid UTF-8: {TARGET}"
        ) from error

    return raw, text


def validate_implementation_shape(
    text: str,
) -> None:
    lines = text.splitlines()

    if not lines:
        raise CompatibilityError(
            "target has no lines"
        )

    if lines[0] != "#!/usr/bin/env python3":
        raise CompatibilityError(
            "target has invalid shebang: "
            f"{lines[0]!r}"
        )

    if READY_DECLARATION_MARKER not in text:
        raise CompatibilityError(
            "target lacks READY_STATES"
        )

    for marker in RECURSIVE_LOADER_MARKERS:
        if marker in text:
            raise CompatibilityError(
                "implementation contains test or recursive-loader code: "
                f"{marker}"
            )


def alias_state(
    text: str,
) -> str:
    ready_count = text.count(
        READY_DECLARATION_MARKER
    )

    terminal_count = text.count(
        TERMINAL_DECLARATION_MARKER
    )

    if ready_count != 1:
        raise CompatibilityError(
            "expected exactly one READY_STATES declaration; "
            f"found {ready_count}"
        )

    if terminal_count == 0:
        return "missing"

    if terminal_count > 1:
        raise CompatibilityError(
            "multiple TERMINAL_READY_STATES declarations found"
        )

    if ALIAS_BLOCK in text:
        return "correct"

    return "conflicting"


def build_candidate(
    text: str,
) -> tuple[str, bool]:
    state = alias_state(
        text
    )

    if state == "correct":
        return text, False

    if state == "conflicting":
        raise CompatibilityError(
            "TERMINAL_READY_STATES exists but is not the "
            "canonical READY_STATES identity alias"
        )

    anchor_count = text.count(
        STATE_FIELDS_ANCHOR
    )

    if anchor_count != 1:
        raise CompatibilityError(
            "expected exactly one STATE_FIELDS anchor; "
            f"found {anchor_count}"
        )

    candidate = text.replace(
        STATE_FIELDS_ANCHOR,
        ALIAS_BLOCK
        + STATE_FIELDS_ANCHOR,
        1,
    )

    if candidate.count(
        TERMINAL_DECLARATION_MARKER
    ) != 1:
        raise CompatibilityError(
            "candidate does not contain exactly one "
            "TERMINAL_READY_STATES declaration"
        )

    if candidate.replace(
        ALIAS_BLOCK,
        "",
        1,
    ) != text:
        raise CompatibilityError(
            "candidate changes content outside compatibility block"
        )

    return candidate, True


def compile_source(
    source: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="savant-opus-state-compatibility-"
    ) as raw_directory:
        candidate_path = (
            Path(
                raw_directory
            )
            / TARGET.name
        )

        candidate_path.write_text(
            source,
            encoding="utf-8",
        )

        try:
            py_compile.compile(
                str(
                    candidate_path
                ),
                doraise=True,
            )
        except py_compile.PyCompileError as error:
            raise CompatibilityError(
                f"candidate syntax validation failed: {error}"
            ) from error


def load_module(
    path: Path,
) -> ModuleType:
    module_name = (
        "inspect_masterplan_opus_binding_state_"
        + sha256_bytes(
            path.read_bytes()
        )[:16]
    )

    specification = (
        importlib.util.spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise CompatibilityError(
            f"unable to create module specification: {path}"
        )

    module = importlib.util.module_from_spec(
        specification
    )

    sys.modules[
        specification.name
    ] = module

    try:
        specification.loader.exec_module(
            module
        )
    except BaseException:
        sys.modules.pop(
            specification.name,
            None,
        )
        raise

    return module


def verify_runtime_identity(
    path: Path,
) -> None:
    module = load_module(
        path
    )

    try:
        ready_states = getattr(
            module,
            "READY_STATES",
        )

        terminal_ready_states = getattr(
            module,
            "TERMINAL_READY_STATES",
        )
    except AttributeError as error:
        raise CompatibilityError(
            f"required runtime symbol missing: {error}"
        ) from error

    if terminal_ready_states is not ready_states:
        raise CompatibilityError(
            "TERMINAL_READY_STATES is not the same mapping "
            "instance as READY_STATES"
        )

    stage_keys = getattr(
        module,
        "STAGE_KEYS",
        None,
    )

    if not isinstance(
        stage_keys,
        tuple,
    ) or len(
        stage_keys
    ) != 9:
        raise CompatibilityError(
            "STAGE_KEYS runtime contract is invalid"
        )

    for mapping_name in (
        "STAGE_POINTERS",
        "REQUIRED_REFERENCES",
        "READY_STATES",
        "TERMINAL_READY_STATES",
        "STATE_FIELDS",
    ):
        mapping = getattr(
            module,
            mapping_name,
            None,
        )

        if not isinstance(
            mapping,
            dict,
        ):
            raise CompatibilityError(
                f"{mapping_name} must be a mapping"
            )

        if set(
            mapping
        ) != set(
            stage_keys
        ):
            raise CompatibilityError(
                f"{mapping_name} keys differ from STAGE_KEYS"
            )


def write_receipt(
    *,
    changed: bool,
    before_digest: str,
    after_digest: str,
    baseline_path: Path,
) -> Path:
    timestamp = utc_timestamp()

    run_root = (
        REPORT_ROOT
        / timestamp
    )

    receipt_path = (
        run_root
        / "receipt.json"
    )

    latest_path = (
        REPORT_ROOT
        / "latest.json"
    )

    receipt = {
        "$schema": (
            "savant://niche/masterplan/"
            "opus-ready-state-compatibility/1.0.0"
        ),
        "operation": (
            "ensure_masterplan_opus_ready_state_compatibility"
        ),
        "passed": True,
        "changed": changed,
        "target": str(
            TARGET
        ),
        "baseline": str(
            baseline_path
        ),
        "before_sha256": before_digest,
        "after_sha256": after_digest,
        "canonical_primitive": (
            "READY_STATES"
        ),
        "compatibility_projection": (
            "TERMINAL_READY_STATES"
        ),
        "identity_verified": True,
        "duplicate_storage": False,
        "authority_effect": "none",
        "implementation_mutation_performed": changed,
        "timestamp": timestamp,
    }

    atomic_write(
        receipt_path,
        pretty_json_bytes(
            receipt
        ),
        0o644,
    )

    latest = {
        "operation": receipt[
            "operation"
        ],
        "passed": True,
        "changed": changed,
        "receipt": str(
            receipt_path
        ),
        "target": str(
            TARGET
        ),
        "baseline": str(
            baseline_path
        ),
        "before_sha256": before_digest,
        "after_sha256": after_digest,
        "identity_verified": True,
        "authority_effect": "none",
        "implementation_mutation_performed": changed,
        "timestamp": timestamp,
    }

    atomic_write(
        latest_path,
        pretty_json_bytes(
            latest
        ),
        0o644,
    )

    return latest_path


def main() -> int:
    before_bytes, before_text = read_target()

    validate_implementation_shape(
        before_text
    )

    candidate_text, changed = build_candidate(
        before_text
    )

    compile_source(
        candidate_text
    )

    target_mode = (
        TARGET.stat().st_mode
        & 0o777
    )

    timestamp = utc_timestamp()

    baseline_path = (
        REPORT_ROOT
        / timestamp
        / (
            TARGET.name
            + ".before"
        )
    )

    atomic_write(
        baseline_path,
        before_bytes,
        target_mode,
    )

    before_digest = sha256_bytes(
        before_bytes
    )

    if sha256_bytes(
        baseline_path.read_bytes()
    ) != before_digest:
        raise CompatibilityError(
            "baseline digest verification failed"
        )

    candidate_bytes = candidate_text.encode(
        "utf-8"
    )

    if changed:
        atomic_write(
            TARGET,
            candidate_bytes,
            target_mode,
        )

    try:
        py_compile.compile(
            str(
                TARGET
            ),
            doraise=True,
        )

        verify_runtime_identity(
            TARGET
        )

    except BaseException as error:
        if changed:
            atomic_write(
                TARGET,
                before_bytes,
                target_mode,
            )

        raise CompatibilityError(
            "live validation failed"
            + (
                "; baseline restored"
                if changed
                else ""
            )
            + f": {error}"
        ) from error

    after_digest = sha256_bytes(
        TARGET.read_bytes()
    )

    expected_digest = sha256_bytes(
        candidate_bytes
    )

    if after_digest != expected_digest:
        if changed:
            atomic_write(
                TARGET,
                before_bytes,
                target_mode,
            )

        raise CompatibilityError(
            "live target digest mismatch"
            + (
                "; baseline restored"
                if changed
                else ""
            )
        )

    latest_path = write_receipt(
        changed=changed,
        before_digest=before_digest,
        after_digest=after_digest,
        baseline_path=baseline_path,
    )

    print(
        json.dumps(
            {
                "operation": (
                    "ensure_masterplan_opus_ready_state_compatibility"
                ),
                "passed": True,
                "changed": changed,
                "canonical_primitive": (
                    "READY_STATES"
                ),
                "compatibility_projection": (
                    "TERMINAL_READY_STATES"
                ),
                "identity_verified": True,
                "duplicate_storage": False,
                "before_sha256": before_digest,
                "after_sha256": after_digest,
                "latest": str(
                    latest_path
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )
    except CompatibilityError as error:
        print(
            json.dumps(
                {
                    "operation": (
                        "ensure_masterplan_opus_ready_state_compatibility"
                    ),
                    "passed": False,
                    "authority_effect": "none",
                    "implementation_mutation_performed": False,
                    "error": str(
                        error
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        raise SystemExit(
            1
        )
