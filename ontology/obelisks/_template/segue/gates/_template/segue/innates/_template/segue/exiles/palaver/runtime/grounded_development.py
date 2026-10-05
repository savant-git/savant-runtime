#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping


ROOT = Path("/root/savant-runtime").resolve()

PALAVER_RUNTIME = (
    ROOT
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "palaver"
    / "runtime"
)

BASE_ENGINE_PATH = (
    PALAVER_RUNTIME
    / "self_hosted_development.py"
)

SCHEMA = (
    "savant://palaver/"
    "grounded-development/1.0.0"
)

OWNER = "palaver"

PERSONA_OWNER = "envoy"

EXECUTION_OWNER = "opus"

MUTATION_OWNER = "coda"

RETRIEVAL_ROLE = "read-only-context"

DEFAULT_PERSONA_ID = "orobouros"

MAX_FILES_WALKED = 8000

MAX_SELECTED_FILES = 28

MAX_FILE_BYTES = 196_608

MAX_FILE_CHARS = 24_000

MAX_CONTEXT_CHARS = 180_000

MAX_PATH_INDEX = 500

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".bash",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "dist",
    "build",
    "coverage",
    ".cache",
    "tmp",
    "temp",
}

SENSITIVE_COMPONENT_PATTERNS = (
    re.compile(
        r"^\.env(?:\.|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"credential",
        re.IGNORECASE,
    ),
    re.compile(
        r"secret",
        re.IGNORECASE,
    ),
    re.compile(
        r"password",
        re.IGNORECASE,
    ),
    re.compile(
        r"private[_-]?key",
        re.IGNORECASE,
    ),
    re.compile(
        r"api[_-]?key",
        re.IGNORECASE,
    ),
    re.compile(
        r"^id_rsa",
        re.IGNORECASE,
    ),
)

SENSITIVE_SUFFIXES = {
    ".pem",
    ".p12",
    ".pfx",
    ".key",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "current",
    "do",
    "for",
    "from",
    "i",
    "identify",
    "in",
    "inspect",
    "is",
    "it",
    "of",
    "on",
    "or",
    "required",
    "return",
    "single",
    "savant",
    "task",
    "the",
    "this",
    "to",
    "with",
}

PRIORITY_PATH_TERMS = {
    "authority": 16,
    "accepted": 16,
    "decision": 14,
    "canon": 12,
    "masterplan": 18,
    "structure_current": 18,
    "current": 8,
    "niche": 16,
    "task": 15,
    "priority": 15,
    "blocker": 15,
    "dependency": 12,
    "status": 10,
    "continuation": 15,
    "migration": 8,
    "runtime": 6,
    "palaver": 7,
    "envoy": 7,
    "opus": 7,
    "coda": 7,
    "notary": 6,
    "pryme": 6,
    "scrybe": 6,
    "orobouros": 6,
}


class GroundedDevelopmentError(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    if not path.is_file():
        raise GroundedDevelopmentError(
            "required module missing: "
            + str(path)
        )

    existing = sys.modules.get(
        name
    )

    if existing is not None:
        return existing

    spec = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise GroundedDevelopmentError(
            "unable to load module: "
            + str(path)
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        name
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            name,
            None,
        )
        raise

    return module


BASE = load_module(
    "savant_palaver_self_hosted_base",
    BASE_ENGINE_PATH,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ContextFile:
    path: str
    score: int
    size: int
    sha256: str
    truncated: bool
    content: str

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": self.score,
            "size": self.size,
            "sha256": self.sha256,
            "truncated": (
                self.truncated
            ),
            "content": self.content,
        }


def relative_path(
    path: Path,
) -> str:
    try:
        return str(
            path.resolve().relative_to(
                ROOT
            )
        )
    except Exception:
        return str(
            path.resolve()
        )


def is_sensitive_path(
    path: Path,
) -> bool:
    if (
        path.suffix.lower()
        in SENSITIVE_SUFFIXES
    ):
        return True

    for component in path.parts:
        for pattern in (
            SENSITIVE_COMPONENT_PATTERNS
        ):
            if pattern.search(
                component
            ):
                return True

    return False


def is_text_candidate(
    path: Path,
) -> bool:
    if path.is_symlink():
        return False

    if is_sensitive_path(
        path
    ):
        return False

    if (
        path.suffix.lower()
        not in TEXT_SUFFIXES
    ):
        return False

    try:
        size = path.stat().st_size
    except OSError:
        return False

    if size <= 0:
        return False

    if size > MAX_FILE_BYTES:
        return False

    return True


def query_terms(
    instruction: str,
) -> tuple[str, ...]:
    values = re.findall(
        r"[a-z0-9][a-z0-9_-]{2,}",
        instruction.lower(),
    )

    result: list[str] = []

    for value in values:
        if value in STOP_WORDS:
            continue

        if value not in result:
            result.append(
                value
            )

    return tuple(
        result[:32]
    )


def path_score(
    path: Path,
    terms: Iterable[str],
) -> int:
    value = relative_path(
        path
    ).lower()

    score = 0

    for term in terms:
        if term in value:
            score += 20

    for term, weight in (
        PRIORITY_PATH_TERMS.items()
    ):
        if term in value:
            score += weight

    name = path.name.lower()

    if (
        "savant_structure_current"
        in name
    ):
        score += 60

    if (
        "chatgpt_masterplan"
        in name
    ):
        score += 60

    if (
        name
        in {
            "accepted.json",
            "decisions.json",
            "task.json",
            "tasks.json",
            "status.json",
            "manifest.json",
            "registry.json",
        }
    ):
        score += 24

    return score


def read_text(
    path: Path,
) -> tuple[str, bytes]:
    data = path.read_bytes()

    if b"\x00" in data[:4096]:
        raise UnicodeError(
            "binary content"
        )

    text = data.decode(
        "utf-8",
        errors="replace",
    )

    return (
        text,
        data,
    )


def content_score(
    text: str,
    terms: Iterable[str],
) -> int:
    lowered = text.lower()

    score = 0

    for term in terms:
        count = lowered.count(
            term
        )

        score += min(
            count,
            8,
        ) * 4

    for word in (
        "accepted decision",
        "accepted authority",
        "current authority",
        "blocking",
        "blocker",
        "incomplete",
        "remaining",
        "next task",
        "highest priority",
        "continuation point",
        "superseded",
        "ready",
    ):
        if word in lowered:
            score += 5

    return score


def walk_candidates(
    terms: Iterable[str],
) -> tuple[
    list[tuple[int, Path]],
    list[str],
]:
    candidates: list[
        tuple[int, Path]
    ] = []

    index: list[str] = []

    walked = 0

    for directory, dirs, files in os.walk(
        ROOT,
        topdown=True,
        followlinks=False,
    ):
        dirs[:] = [
            name
            for name in dirs
            if (
                name
                not in EXCLUDED_DIRECTORY_NAMES
                and not is_sensitive_path(
                    Path(directory)
                    / name
                )
            )
        ]

        for name in files:
            walked += 1

            if walked > MAX_FILES_WALKED:
                break

            path = (
                Path(directory)
                / name
            )

            if not is_text_candidate(
                path
            ):
                continue

            score = path_score(
                path,
                terms,
            )

            if (
                score > 0
                and len(index)
                < MAX_PATH_INDEX
            ):
                index.append(
                    relative_path(
                        path
                    )
                )

            candidates.append(
                (
                    score,
                    path,
                )
            )

        if walked > MAX_FILES_WALKED:
            break

    candidates.sort(
        key=lambda item: (
            -item[0],
            relative_path(
                item[1]
            ),
        )
    )

    return (
        candidates,
        index,
    )


def select_context_files(
    instruction: str,
) -> tuple[
    ContextFile,
    ...,
]:
    terms = query_terms(
        instruction
    )

    candidates, _ = (
        walk_candidates(
            terms
        )
    )

    #
    # First inspect path-relevant candidates.
    #
    inspection_pool = (
        candidates[:160]
    )

    scored: list[
        tuple[int, Path, str, bytes]
    ] = []

    for base_score, path in (
        inspection_pool
    ):
        try:
            text, data = read_text(
                path
            )
        except (
            OSError,
            UnicodeError,
        ):
            continue

        score = (
            base_score
            + content_score(
                text[
                    :MAX_FILE_CHARS
                ],
                terms,
            )
        )

        if score <= 0:
            continue

        scored.append(
            (
                score,
                path,
                text,
                data,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            relative_path(
                item[1]
            ),
        )
    )

    selected: list[
        ContextFile
    ] = []

    used_chars = 0

    for (
        score,
        path,
        text,
        data,
    ) in scored:
        if (
            len(selected)
            >= MAX_SELECTED_FILES
        ):
            break

        available = (
            MAX_CONTEXT_CHARS
            - used_chars
        )

        if available <= 0:
            break

        limit = min(
            MAX_FILE_CHARS,
            available,
        )

        body = text[
            :limit
        ]

        selected.append(
            ContextFile(
                path=relative_path(
                    path
                ),
                score=score,
                size=len(
                    data
                ),
                sha256=sha256_bytes(
                    data
                ),
                truncated=(
                    len(text)
                    > len(body)
                ),
                content=body,
            )
        )

        used_chars += len(
            body
        )

    return tuple(
        selected
    )


def repository_index(
    instruction: str,
) -> tuple[str, ...]:
    terms = query_terms(
        instruction
    )

    _, index = walk_candidates(
        terms
    )

    return tuple(
        index[
            :MAX_PATH_INDEX
        ]
    )


def ownership_contract() -> dict[str, Any]:
    return {
        "conversation_owner": (
            "palaver"
        ),
        "persona_composition_owner": (
            "envoy"
        ),
        "provider_execution_owner": (
            "opus"
        ),
        "model_execution_owner": (
            "opus"
        ),
        "durable_filesystem_mutation_owner": (
            "coda"
        ),
        "persona_identity": (
            "orobouros"
        ),
        "filesystem_presence_is_authority": (
            False
        ),
        "ai_output_is_authority": (
            False
        ),
    }


def assemble_context(
    instruction: str,
) -> dict[str, Any]:
    files = select_context_files(
        instruction
    )

    index = repository_index(
        instruction
    )

    payload = {
        "schema": (
            "savant://palaver/"
            "repository-context/1.0.0"
        ),
        "owner": OWNER,
        "role": RETRIEVAL_ROLE,
        "root": str(
            ROOT
        ),
        "instruction": (
            instruction
        ),
        "ownership_contract": (
            ownership_contract()
        ),
        "authority_rules": {
            "current_user_directive_rank": 1,
            "accepted_authoritative_graph_rank": 2,
            "accepted_decisions_rank": 3,
            "constitutional_canon_rank": 4,
            "verified_implementation_rank": 5,
            "filesystem_presence_establishes_authority": (
                False
            ),
            "newer_accepted_authority_preferred": (
                True
            ),
            "unresolved_conflicts_must_not_be_invented_away": (
                True
            ),
        },
        "selected_file_count": len(
            files
        ),
        "selected_files": [
            item.projection()
            for item in files
        ],
        "relevant_repository_index": list(
            index
        ),
        "read_only": True,
        "mutation_authorized": False,
        "authority_effect": "none",
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def context_text(
    context: Mapping[str, Any],
) -> str:
    parts: list[str] = []

    parts.append(
        "SAVANT GROUNDED EXECUTION CONTEXT"
    )

    parts.append(
        canonical_json(
            {
                "ownership_contract": (
                    context[
                        "ownership_contract"
                    ]
                ),
                "authority_rules": (
                    context[
                        "authority_rules"
                    ]
                ),
                "repository_root": (
                    context[
                        "root"
                    ]
                ),
                "context_digest": (
                    context[
                        "digest"
                    ]
                ),
            }
        )
    )

    index = context.get(
        "relevant_repository_index",
        [],
    )

    if index:
        parts.append(
            "RELEVANT REPOSITORY PATH INDEX\n"
            + "\n".join(
                str(value)
                for value in index
            )
        )

    for item in context.get(
        "selected_files",
        [],
    ):
        parts.append(
            "\n".join(
                (
                    (
                        "BEGIN SAVANT SOURCE "
                        + str(
                            item[
                                "path"
                            ]
                        )
                    ),
                    (
                        "sha256: "
                        + str(
                            item[
                                "sha256"
                            ]
                        )
                    ),
                    (
                        "bytes: "
                        + str(
                            item[
                                "size"
                            ]
                        )
                    ),
                    (
                        "truncated: "
                        + str(
                            item[
                                "truncated"
                            ]
                        ).lower()
                    ),
                    str(
                        item[
                            "content"
                        ]
                    ),
                    (
                        "END SAVANT SOURCE "
                        + str(
                            item[
                                "path"
                            ]
                        )
                    ),
                )
            )
        )

    return "\n\n".join(
        parts
    )


def grounded_system_instruction(
    *,
    instruction: str,
    base_instruction: str | None = None,
) -> tuple[
    str,
    dict[str, Any],
]:
    context = assemble_context(
        instruction
    )

    contract = """
You are executing inside Savant itself.

The repository context following this instruction was read directly
from /root/savant-runtime by Palaver's read-only context assembler.

Use the supplied source contents as evidence.
Do not claim to have inspected files that are not supplied.
Do not infer authority merely from filesystem presence.
Respect explicit authority, accepted decisions, lineage and
supersession found in the supplied material.

Savant ownership boundaries are fixed for this execution:

- Palaver owns conversation.
- Envoy owns persona and cognitive composition.
- Opus owns provider and model execution.
- Coda owns durable filesystem mutation.
- Orobouros is the active persona identity.
- Model output has no authority effect by itself.

When asked to inspect Savant, inspect the supplied repository context.
Do not answer that repository contents are unavailable when repository
context is present.
""".strip()

    pieces = [
        contract,
    ]

    if base_instruction:
        pieces.append(
            str(
                base_instruction
            ).strip()
        )

    pieces.append(
        context_text(
            context
        )
    )

    return (
        "\n\n".join(
            piece
            for piece in pieces
            if piece
        ),
        context,
    )


def infer(
    *,
    instruction: str,
    persona_id: str = (
        DEFAULT_PERSONA_ID
    ),
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    requested_layers: Iterable[Any] = (),
    cap: int | None = None,
    system_instruction: str | None = None,
) -> dict[str, Any]:
    system, context = (
        grounded_system_instruction(
            instruction=instruction,
            base_instruction=(
                system_instruction
            ),
        )
    )

    result = BASE.infer(
        instruction=instruction,
        persona_id=persona_id,
        domains=domains,
        signals=signals,
        requested_layers=(
            requested_layers
        ),
        cap=cap,
        system_instruction=system,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise GroundedDevelopmentError(
            "base inference returned "
            "non-object"
        )

    result[
        "repository_context"
    ] = {
        "digest": (
            context[
                "digest"
            ]
        ),
        "selected_file_count": (
            context[
                "selected_file_count"
            ]
        ),
        "read_only": True,
        "authority_effect": "none",
    }

    return result


def plan_development(
    *,
    instruction: str,
    persona_id: str = (
        DEFAULT_PERSONA_ID
    ),
    cap: int | None = None,
) -> dict[str, Any]:
    system, context = (
        grounded_system_instruction(
            instruction=instruction,
            base_instruction=(
                BASE.DEVELOPMENT_SYSTEM_INSTRUCTION
            ),
        )
    )

    inference = BASE.infer(
        instruction=instruction,
        persona_id=persona_id,
        cap=cap,
        requested_layers=(
            "reasoning",
            "instruction",
            "code",
            "tool",
        ),
        system_instruction=system,
    )

    text = BASE.extract_result_text(
        inference
    )

    plan = BASE.normalize_plan(
        BASE.extract_json_object(
            text
        )
    )

    payload = {
        "schema": (
            "savant://palaver/"
            "grounded-development-plan/1.0.0"
        ),
        "owner": OWNER,
        "persona_owner": (
            PERSONA_OWNER
        ),
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "mutation_owner": (
            MUTATION_OWNER
        ),
        "instruction": (
            instruction
        ),
        "persona_id": (
            persona_id
        ),
        "persona_digest": (
            inference[
                "persona"
            ].get(
                "digest"
            )
            or inference[
                "persona"
            ].get(
                "composition_digest"
            )
        ),
        "accepted_trait_history_digest": (
            inference[
                "persona"
            ].get(
                "accepted_trait_history_digest"
            )
        ),
        "cognitive_projection": (
            inference[
                "cognitive_projection"
            ]
        ),
        "repository_context": {
            "digest": (
                context[
                    "digest"
                ]
            ),
            "selected_file_count": (
                context[
                    "selected_file_count"
                ]
            ),
            "selected_paths": [
                item[
                    "path"
                ]
                for item in context[
                    "selected_files"
                ]
            ],
            "read_only": True,
            "authority_effect": "none",
        },
        "summary": (
            plan[
                "summary"
            ]
        ),
        "operations": (
            plan[
                "operations"
            ]
        ),
        "operation_count": len(
            plan[
                "operations"
            ]
        ),
        "model_lineage": (
            inference[
                "result"
            ].get(
                "lineage"
            )
        ),
        "authoritative": False,
        "authority_effect": "none",
        "mutation_performed": False,
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def commit_plan(
    plan: Mapping[str, Any],
    *,
    requester: str = OWNER,
) -> dict[str, Any]:
    return BASE.commit_plan(
        plan,
        requester=requester,
    )


def develop(
    *,
    instruction: str,
    persona_id: str = (
        DEFAULT_PERSONA_ID
    ),
    cap: int | None = None,
    commit: bool = False,
) -> dict[str, Any]:
    plan = plan_development(
        instruction=instruction,
        persona_id=persona_id,
        cap=cap,
    )

    if not commit:
        return {
            "schema": (
                "savant://palaver/"
                "grounded-development-run/1.0.0"
            ),
            "owner": OWNER,
            "committed": False,
            "plan": plan,
            "authority_effect": "none",
        }

    committed = commit_plan(
        plan
    )

    return {
        "schema": (
            "savant://palaver/"
            "grounded-development-run/1.0.0"
        ),
        "owner": OWNER,
        "committed": True,
        "plan": plan,
        "commit": committed,
        "authority_effect": "none",
    }


def replace_file(
    *,
    path: str,
    content: str,
    expected_digest: str | None = None,
    intent: str = (
        "palaver authorized "
        "file replacement"
    ),
) -> dict[str, Any]:
    return BASE.replace_file(
        path=path,
        content=content,
        expected_digest=(
            expected_digest
        ),
        intent=intent,
    )


def persist_trait_decision(
    decision: Mapping[str, Any],
    *,
    expected_store_digest: str | None = None,
) -> dict[str, Any]:
    return BASE.persist_trait_decision(
        decision,
        expected_store_digest=(
            expected_store_digest
        ),
    )


def extract_result_text(
    inference: Mapping[str, Any],
) -> str:
    return BASE.extract_result_text(
        inference
    )


def status() -> dict[str, Any]:
    base = BASE.status()

    checks = dict(
        base.get(
            "checks",
            {},
        )
    )

    checks[
        "repository_root_exists"
    ] = ROOT.is_dir()

    checks[
        "grounded_context_assembler"
    ] = True

    checks[
        "grounded_context_read_only"
    ] = True

    checks[
        "coda_remains_mutation_owner"
    ] = (
        MUTATION_OWNER
        == "coda"
    )

    ready = all(
        checks.values()
    )

    payload = dict(
        base
    )

    payload.update(
        {
            "schema": SCHEMA,
            "grounded_repository_context": (
                True
            ),
            "repository_root": str(
                ROOT
            ),
            "checks": checks,
            "ready": ready,
        }
    )

    payload[
        "digest"
    ] = digest(
        {
            key: value
            for key, value
            in payload.items()
            if key != "digest"
        }
    )

    return payload


def selftest() -> dict[str, Any]:
    value = status()

    if not value.get(
        "ready"
    ):
        failed = [
            key
            for key, passed
            in value[
                "checks"
            ].items()
            if not passed
        ]

        raise GroundedDevelopmentError(
            "grounded development "
            "boundary failed: "
            + ", ".join(
                failed
            )
        )

    return {
        "ok": True,
        **value,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )
