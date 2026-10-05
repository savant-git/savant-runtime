#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path("/root/savant-runtime").resolve()

EXILES = (
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
)

PALAVER_RUNTIME = (
    EXILES
    / "palaver"
    / "runtime"
)

ENVOY_RUNTIME = (
    EXILES
    / "envoy"
    / "runtime"
)

OPUS_RUNTIME = (
    EXILES
    / "opus"
    / "runtime"
)

CODA_RUNTIME = (
    EXILES
    / "coda"
    / "runtime"
)

OWNER = "palaver"
PERSONA_OWNER = "envoy"
EXECUTION_OWNER = "opus"
MUTATION_OWNER = "coda"

DEFAULT_PERSONA_ID = "orobouros"

SCHEMA = (
    "savant://palaver/"
    "self-hosted-development/1.1.0"
)

SUPPORTED_COGNITIVE_LAYERS = (
    "general",
    "reasoning",
    "instruction",
    "writing",
    "code",
    "tool",
)

ALLOWED_OPERATIONS = {
    "replace_text",
    "create_text",
    "append_text",
    "delete_file",
    "copy_file",
    "move_file",
    "make_directory",
    "remove_directory",
}


class SelfHostedDevelopmentError(
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


def file_digest(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def normalize_terms(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []

    for raw in values:
        value = str(
            raw
            or ""
        ).strip().lower()

        if (
            value
            and value not in result
        ):
            result.append(
                value
            )

    return tuple(
        result
    )


def prepare_import_paths() -> None:
    paths = (
        CODA_RUNTIME,
        OPUS_RUNTIME,
        ENVOY_RUNTIME,
        PALAVER_RUNTIME,
    )

    for path in paths:
        text = str(
            path
        )

        while text in sys.path:
            sys.path.remove(
                text
            )

    for path in reversed(
        paths
    ):
        sys.path.insert(
            0,
            str(path),
        )


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    existing = sys.modules.get(
        name
    )

    if existing is not None:
        return existing

    if not path.is_file():
        raise SelfHostedDevelopmentError(
            "required runtime module missing: "
            + str(path)
        )

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
        raise SelfHostedDevelopmentError(
            "unable to load runtime module: "
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


def load_persona_engine() -> ModuleType:
    prepare_import_paths()

    module = load_module(
        "savant_selfhost_persona_engine",
        ENVOY_RUNTIME
        / "persona_engine.py",
    )

    for symbol in (
        "compose_persona",
        "load_persona",
        "select_living_traits",
    ):
        if not callable(
            getattr(
                module,
                symbol,
                None,
            )
        ):
            raise SelfHostedDevelopmentError(
                "envoy persona engine "
                "missing callable: "
                + symbol
            )

    return module


def load_envoy_opus_bridge() -> ModuleType:
    prepare_import_paths()

    module = load_module(
        "savant_selfhost_envoy_opus_bridge",
        ENVOY_RUNTIME
        / "opus_bridge.py",
    )

    for symbol in (
        "infer_with_opus",
        "infer_with_cognitive_projection",
        "project_cognitive_layers",
        "text_bridge_projection",
    ):
        if not callable(
            getattr(
                module,
                symbol,
                None,
            )
        ):
            raise SelfHostedDevelopmentError(
                "envoy opus bridge "
                "missing callable: "
                + symbol
            )

    return module


def load_coda_mutation() -> ModuleType:
    prepare_import_paths()

    module = load_module(
        "savant_selfhost_coda_mutation",
        CODA_RUNTIME
        / "mutation.py",
    )

    for symbol in (
        "execute_plan",
        "status",
    ):
        if not callable(
            getattr(
                module,
                symbol,
                None,
            )
        ):
            raise SelfHostedDevelopmentError(
                "coda mutation runtime "
                "missing callable: "
                + symbol
            )

    return module


def load_coda_palaver_bridge() -> ModuleType:
    prepare_import_paths()

    mutation = load_coda_mutation()

    previous = sys.modules.get(
        "mutation"
    )

    sys.modules[
        "mutation"
    ] = mutation

    try:
        module = load_module(
            "savant_selfhost_coda_palaver_bridge",
            CODA_RUNTIME
            / "palaver_bridge.py",
        )
    finally:
        if previous is None:
            sys.modules.pop(
                "mutation",
                None,
            )
        else:
            sys.modules[
                "mutation"
            ] = previous

    if not callable(
        getattr(
            module,
            "replace_file",
            None,
        )
    ):
        raise SelfHostedDevelopmentError(
            "coda palaver bridge "
            "missing replace_file()"
        )

    return module


def load_trait_history_store() -> ModuleType:
    prepare_import_paths()

    module = load_module(
        "savant_selfhost_trait_history_store",
        CODA_RUNTIME
        / "trait_history_store.py",
    )

    for symbol in (
        "append_decision",
        "accepted_trait_projection",
        "status",
    ):
        if not callable(
            getattr(
                module,
                symbol,
                None,
            )
        ):
            raise SelfHostedDevelopmentError(
                "coda trait history store "
                "missing callable: "
                + symbol
            )

    return module


def infer_domains(
    instruction: str,
) -> tuple[str, ...]:
    text = instruction.lower()

    result: list[str] = []

    if any(
        token in text
        for token in (
            "implement",
            "code",
            "python",
            "javascript",
            "runtime",
            "server",
            "file",
            "build",
            "fix",
            "repair",
            "refactor",
            "integrate",
        )
    ):
        result.append(
            "engineering"
        )

    if any(
        token in text
        for token in (
            "analyze",
            "analyse",
            "verify",
            "compare",
            "reason",
            "inspect",
        )
    ):
        result.append(
            "analysis"
        )

    if any(
        token in text
        for token in (
            "write",
            "rewrite",
            "compose",
            "prose",
        )
    ):
        result.append(
            "writing"
        )

    if not result:
        result.append(
            "conversation"
        )

    return tuple(
        result
    )


def infer_signals(
    instruction: str,
) -> tuple[str, ...]:
    text = instruction.lower()

    candidates = (
        "implement",
        "code",
        "debug",
        "refactor",
        "analyze",
        "verify",
        "compare",
        "infer",
        "write",
        "rewrite",
        "compose",
        "execute",
        "tool",
    )

    result = [
        item
        for item in candidates
        if item in text
    ]

    return tuple(
        result
    )


def compose_cognitive_persona(
    *,
    instruction: str,
    persona_id: str = DEFAULT_PERSONA_ID,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    cap: int | None = None,
) -> dict[str, Any]:
    persona_engine = (
        load_persona_engine()
    )

    selected_domains = (
        normalize_terms(
            domains
        )
        or infer_domains(
            instruction
        )
    )

    selected_signals = (
        normalize_terms(
            signals
        )
        or infer_signals(
            instruction
        )
    )

    projection = (
        persona_engine.compose_persona(
            persona_id=persona_id,
            domains=selected_domains,
            signals=selected_signals,
            cap=cap,
        )
    )

    if not isinstance(
        projection,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "envoy persona composition "
            "returned non-object"
        )

    if (
        projection.get(
            "owner"
        )
        != PERSONA_OWNER
    ):
        raise SelfHostedDevelopmentError(
            "envoy persona ownership "
            "boundary failed"
        )

    if (
        projection.get(
            "persona_id"
        )
        != persona_id
    ):
        raise SelfHostedDevelopmentError(
            "persona identity mismatch"
        )

    return projection


def cognitive_projection(
    *,
    persona: dict[str, Any],
    instruction: str,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    requested_layers: Iterable[Any] = (),
) -> dict[str, Any]:
    bridge = (
        load_envoy_opus_bridge()
    )

    selected_domains = (
        normalize_terms(
            domains
        )
        or infer_domains(
            instruction
        )
    )

    selected_signals = (
        normalize_terms(
            signals
        )
        or infer_signals(
            instruction
        )
    )

    selected_layers = (
        normalize_terms(
            requested_layers
        )
    )

    invalid = [
        layer
        for layer in selected_layers
        if (
            layer
            not in SUPPORTED_COGNITIVE_LAYERS
        )
    ]

    if invalid:
        raise SelfHostedDevelopmentError(
            "unsupported cognitive layer(s): "
            + ", ".join(
                invalid
            )
        )

    return bridge.project_cognitive_layers(
        persona,
        domains=selected_domains,
        signals=selected_signals,
        requested_layers=selected_layers,
    )


def build_inference_request(
    *,
    instruction: str,
    system_instruction: str | None = None,
    persona: Mapping[str, Any] | None = None,
    cognitive: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    text = str(
        instruction
        or ""
    ).strip()

    if not text:
        raise SelfHostedDevelopmentError(
            "development instruction "
            "is required"
        )

    request: dict[str, Any] = {
        "owner": OWNER,
        "prompt": text,
        "text": text,
    }

    if persona is not None:
        request[
            "persona_projection"
        ] = dict(
            persona
        )

    if cognitive is not None:
        request[
            "cognitive_projection"
        ] = dict(
            cognitive
        )

    if system_instruction:
        context = {
            "persona_id": (
                persona.get(
                    "persona_id"
                )
                if persona
                else None
            ),
            "persona_owner": (
                PERSONA_OWNER
            ),
            "cognitive_layers": (
                cognitive.get(
                    "layers",
                    [],
                )
                if cognitive
                else []
            ),
            "cognitive_owner": (
                cognitive.get(
                    "owner"
                )
                if cognitive
                else None
            ),
            "provider_execution_owner": (
                EXECUTION_OWNER
            ),
            "filesystem_mutation_owner": (
                MUTATION_OWNER
            ),
        }

        request[
            "system"
        ] = (
            system_instruction.strip()
            + "\n\nSavant execution context:\n"
            + canonical_json(
                context
            )
        )

    return request


def infer(
    *,
    instruction: str,
    persona_id: str = DEFAULT_PERSONA_ID,
    domains: Iterable[Any] = (),
    signals: Iterable[Any] = (),
    requested_layers: Iterable[Any] = (),
    cap: int | None = None,
    system_instruction: str | None = None,
) -> dict[str, Any]:
    persona = (
        compose_cognitive_persona(
            instruction=instruction,
            persona_id=persona_id,
            domains=domains,
            signals=signals,
            cap=cap,
        )
    )

    cognitive = cognitive_projection(
        persona=persona,
        instruction=instruction,
        domains=domains,
        signals=signals,
        requested_layers=(
            requested_layers
        ),
    )

    bridge = (
        load_envoy_opus_bridge()
    )

    request = (
        build_inference_request(
            instruction=instruction,
            system_instruction=(
                system_instruction
            ),
            persona=persona,
            cognitive=cognitive,
        )
    )

    #
    # Important:
    #
    # Envoy still creates the cognitive projection,
    # but we do not force those projection layers into
    # Opus provider eligibility here.
    #
    # Opus remains the sole provider/model selector.
    #
    result = bridge.infer_with_opus(
        request
    )

    if not isinstance(
        result,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "opus inference result "
            "must be an object"
        )

    lineage = result.get(
        "lineage"
    )

    if not isinstance(
        lineage,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "opus inference lineage missing"
        )

    if (
        lineage.get(
            "owner"
        )
        != EXECUTION_OWNER
    ):
        raise SelfHostedDevelopmentError(
            "opus execution ownership "
            "boundary failed"
        )

    result[
        "cognitive_projection"
    ] = cognitive

    return {
        "schema": SCHEMA,
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
        "persona": persona,
        "cognitive_projection": (
            cognitive
        ),
        "result": result,
        "authoritative": False,
        "authority_effect": "none",
    }


def extract_result_text(
    inference: Mapping[str, Any],
) -> str:
    result = inference.get(
        "result"
    )

    if not isinstance(
        result,
        Mapping,
    ):
        return ""

    for key in (
        "text",
        "output_text",
        "response",
        "content",
        "answer",
    ):
        value = result.get(
            key
        )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            return value.strip()

    output = result.get(
        "output"
    )

    if isinstance(
        output,
        str,
    ):
        return output.strip()

    if isinstance(
        output,
        list,
    ):
        pieces: list[str] = []

        for item in output:
            if isinstance(
                item,
                str,
            ):
                pieces.append(
                    item
                )

            elif isinstance(
                item,
                Mapping,
            ):
                for key in (
                    "text",
                    "content",
                    "output_text",
                ):
                    value = item.get(
                        key
                    )

                    if isinstance(
                        value,
                        str,
                    ):
                        pieces.append(
                            value
                        )

        return "\n".join(
            item
            for item in pieces
            if item.strip()
        ).strip()

    return ""


def extract_json_object(
    text: str,
) -> dict[str, Any]:
    value = str(
        text
        or ""
    ).strip()

    if not value:
        raise SelfHostedDevelopmentError(
            "model returned no plan text"
        )

    fenced = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```",
        value,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if fenced:
        value = fenced.group(
            1
        ).strip()

    try:
        parsed = json.loads(
            value
        )

    except json.JSONDecodeError:
        start = value.find(
            "{"
        )

        end = value.rfind(
            "}"
        )

        if (
            start < 0
            or end <= start
        ):
            raise SelfHostedDevelopmentError(
                "model response contains "
                "no JSON object"
            )

        try:
            parsed = json.loads(
                value[
                    start:
                    end + 1
                ]
            )
        except json.JSONDecodeError as exc:
            raise SelfHostedDevelopmentError(
                "model development plan "
                "is not valid JSON"
            ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "development plan root "
            "must be an object"
        )

    return parsed


def resolve_runtime_path(
    raw: Any,
) -> Path:
    value = str(
        raw
        or ""
    ).strip()

    if not value:
        raise SelfHostedDevelopmentError(
            "operation path is required"
        )

    path = Path(
        value
    )

    if not path.is_absolute():
        path = (
            ROOT
            / path
        )

    resolved = path.resolve(
        strict=False
    )

    if (
        resolved != ROOT
        and ROOT not in resolved.parents
    ):
        raise SelfHostedDevelopmentError(
            "operation escapes Savant root: "
            + str(
                resolved
            )
        )

    return resolved


def normalize_operation(
    raw: Mapping[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    operation = dict(
        raw
    )

    kind = str(
        operation.get(
            "operation"
        )
        or operation.get(
            "kind"
        )
        or ""
    ).strip()

    if (
        kind
        not in ALLOWED_OPERATIONS
    ):
        raise SelfHostedDevelopmentError(
            "unsupported Coda operation "
            f"at index {index}: "
            f"{kind!r}"
        )

    operation[
        "operation"
    ] = kind

    operation.pop(
        "kind",
        None,
    )

    if kind in {
        "replace_text",
        "create_text",
        "append_text",
        "delete_file",
        "make_directory",
        "remove_directory",
    }:
        operation[
            "path"
        ] = str(
            resolve_runtime_path(
                operation.get(
                    "path"
                )
            )
        )

    if kind in {
        "copy_file",
        "move_file",
    }:
        operation[
            "source"
        ] = str(
            resolve_runtime_path(
                operation.get(
                    "source"
                )
            )
        )

        operation[
            "destination"
        ] = str(
            resolve_runtime_path(
                operation.get(
                    "destination"
                )
            )
        )

    if kind in {
        "replace_text",
        "create_text",
        "append_text",
    }:
        if (
            "content"
            not in operation
        ):
            raise SelfHostedDevelopmentError(
                f"{kind} operation "
                "requires content"
            )

        if not isinstance(
            operation[
                "content"
            ],
            str,
        ):
            raise SelfHostedDevelopmentError(
                f"{kind} content "
                "must be text"
            )

    return operation


def normalize_plan(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    operations = value.get(
        "operations"
    )

    if not isinstance(
        operations,
        list,
    ):
        raise SelfHostedDevelopmentError(
            "development plan must contain "
            "operations list"
        )

    normalized = [
        normalize_operation(
            raw,
            index=index,
        )
        for index, raw
        in enumerate(
            operations
        )
        if isinstance(
            raw,
            Mapping,
        )
    ]

    if (
        len(normalized)
        != len(operations)
    ):
        raise SelfHostedDevelopmentError(
            "every operation must "
            "be an object"
        )

    return {
        "summary": str(
            value.get(
                "summary"
            )
            or ""
        ).strip(),
        "operations": normalized,
    }


def prepare_commit_operations(
    operations: Sequence[
        Mapping[str, Any]
    ],
) -> list[dict[str, Any]]:
    prepared: list[
        dict[str, Any]
    ] = []

    for raw in operations:
        operation = dict(
            raw
        )

        kind = operation[
            "operation"
        ]

        if kind in {
            "replace_text",
            "append_text",
            "delete_file",
        }:
            path = Path(
                operation[
                    "path"
                ]
            )

            if (
                kind == "replace_text"
                and not path.exists()
            ):
                operation[
                    "operation"
                ] = "create_text"

            elif (
                path.is_file()
                and not operation.get(
                    "expected_digest"
                )
            ):
                operation[
                    "expected_digest"
                ] = file_digest(
                    path
                )

        if kind in {
            "copy_file",
            "move_file",
        }:
            source = Path(
                operation[
                    "source"
                ]
            )

            if (
                source.is_file()
                and not operation.get(
                    "expected_source_digest"
                )
            ):
                operation[
                    "expected_source_digest"
                ] = file_digest(
                    source
                )

        prepared.append(
            operation
        )

    return prepared


DEVELOPMENT_SYSTEM_INSTRUCTION = """
You are the implementation reasoning component inside Savant's
self-hosted development loop.

Return exactly one JSON object.
Return no prose outside that object.
Do not use markdown fences.

Schema:

{
  "summary": "short description",
  "operations": [
    {
      "operation": "replace_text|create_text|append_text|delete_file|copy_file|move_file|make_directory|remove_directory"
    }
  ]
}

Operation contracts:

replace_text:
{
  "operation": "replace_text",
  "path": "/root/savant-runtime/...",
  "content": "COMPLETE replacement file contents"
}

create_text:
{
  "operation": "create_text",
  "path": "/root/savant-runtime/...",
  "content": "COMPLETE new file contents"
}

append_text:
{
  "operation": "append_text",
  "path": "/root/savant-runtime/...",
  "content": "text to append"
}

delete_file:
{
  "operation": "delete_file",
  "path": "/root/savant-runtime/..."
}

copy_file:
{
  "operation": "copy_file",
  "source": "/root/savant-runtime/...",
  "destination": "/root/savant-runtime/..."
}

move_file:
{
  "operation": "move_file",
  "source": "/root/savant-runtime/...",
  "destination": "/root/savant-runtime/..."
}

make_directory:
{
  "operation": "make_directory",
  "path": "/root/savant-runtime/..."
}

remove_directory:
{
  "operation": "remove_directory",
  "path": "/root/savant-runtime/..."
}

Rules:

- Work only beneath /root/savant-runtime.
- Preserve current implementation unless higher authority supersedes it.
- Make the smallest complete change that fulfills the instruction.
- For replacement or creation, emit the COMPLETE file.
- Never emit fragments or patches as replacement content.
- Never invent expected_digest values.
- Palaver owns conversation.
- Envoy owns persona/cognitive projection.
- Opus owns provider/model routing and external model execution.
- Coda owns durable filesystem mutation.
- AI output has no authority by itself.
- Do not mutate accepted authority merely because a model proposes it.
- Do not bypass Coda.
- Do not emit shell commands.
- Do not perform optional architectural expansion.
- An empty operations array is valid if no filesystem mutation is required.
""".strip()


def plan_development(
    *,
    instruction: str,
    persona_id: str = DEFAULT_PERSONA_ID,
    cap: int | None = None,
) -> dict[str, Any]:
    inference = infer(
        instruction=instruction,
        persona_id=persona_id,
        cap=cap,
        requested_layers=(
            "reasoning",
            "instruction",
            "code",
            "tool",
        ),
        system_instruction=(
            DEVELOPMENT_SYSTEM_INSTRUCTION
        ),
    )

    text = extract_result_text(
        inference
    )

    plan = normalize_plan(
        extract_json_object(
            text
        )
    )

    payload = {
        "schema": (
            "savant://palaver/"
            "development-plan/1.1.0"
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
        "instruction": instruction,
        "persona_id": persona_id,
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
    operations = plan.get(
        "operations"
    )

    if not isinstance(
        operations,
        Sequence,
    ) or isinstance(
        operations,
        (
            str,
            bytes,
        ),
    ):
        raise SelfHostedDevelopmentError(
            "plan operations are invalid"
        )

    prepared = (
        prepare_commit_operations(
            operations
        )
    )

    coda = (
        load_coda_mutation()
    )

    result = coda.execute_plan(
        prepared,
        requester=requester,
        intent=(
            "palaver self-hosted "
            "development commit; "
            "plan="
            + str(
                plan.get(
                    "digest"
                )
                or "unknown"
            )
        ),
    )

    if not isinstance(
        result,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "coda mutation result "
            "must be an object"
        )

    if (
        result.get(
            "owner"
        )
        != MUTATION_OWNER
    ):
        raise SelfHostedDevelopmentError(
            "coda mutation ownership "
            "boundary failed"
        )

    return {
        "schema": (
            "savant://palaver/"
            "development-commit/1.1.0"
        ),
        "owner": OWNER,
        "mutation_owner": (
            MUTATION_OWNER
        ),
        "plan_digest": (
            plan.get(
                "digest"
            )
        ),
        "operation_count": len(
            prepared
        ),
        "operations": prepared,
        "result": result,
        "authority_effect": "none",
    }


def develop(
    *,
    instruction: str,
    persona_id: str = DEFAULT_PERSONA_ID,
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
                "development-run/1.1.0"
            ),
            "owner": OWNER,
            "committed": False,
            "plan": plan,
            "authority_effect": "none",
        }

    committed = (
        commit_plan(
            plan
        )
    )

    return {
        "schema": (
            "savant://palaver/"
            "development-run/1.1.0"
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
    bridge = (
        load_coda_palaver_bridge()
    )

    resolved = (
        resolve_runtime_path(
            path
        )
    )

    request: dict[str, Any] = {
        "path": str(
            resolved
        ),
        "content": content,
        "intent": intent,
    }

    if expected_digest:
        request[
            "expected_digest"
        ] = expected_digest

    elif resolved.is_file():
        request[
            "expected_digest"
        ] = file_digest(
            resolved
        )

    return bridge.replace_file(
        request
    )


def persist_trait_decision(
    decision: Mapping[str, Any],
    *,
    expected_store_digest: str | None = None,
) -> dict[str, Any]:
    if not isinstance(
        decision,
        Mapping,
    ):
        raise SelfHostedDevelopmentError(
            "trait decision must "
            "be an object"
        )

    store = (
        load_trait_history_store()
    )

    result = store.append_decision(
        dict(
            decision
        ),
        expected_store_digest=(
            expected_store_digest
        ),
    )

    if not isinstance(
        result,
        dict,
    ):
        raise SelfHostedDevelopmentError(
            "trait history persistence "
            "returned non-object"
        )

    return result


def status() -> dict[str, Any]:
    persona_engine = (
        load_persona_engine()
    )

    envoy_bridge = (
        load_envoy_opus_bridge()
    )

    coda = (
        load_coda_mutation()
    )

    trait_store = (
        load_trait_history_store()
    )

    persona = (
        persona_engine.compose_persona(
            persona_id=(
                DEFAULT_PERSONA_ID
            ),
            domains=(
                "engineering",
            ),
            signals=(
                "implement",
                "verify",
            ),
            cap=4,
        )
    )

    cognitive = (
        envoy_bridge.project_cognitive_layers(
            persona,
            domains=(
                "engineering",
            ),
            signals=(
                "implement",
            ),
        )
    )

    opus_projection = (
        envoy_bridge.text_bridge_projection()
    )

    coda_status = (
        coda.status()
    )

    trait_status = (
        trait_store.status()
    )

    checks = {
        "palaver_conversation_owner": (
            OWNER
            == "palaver"
        ),
        "envoy_persona_owner": (
            persona.get(
                "owner"
            )
            == PERSONA_OWNER
        ),
        "orobouros_default_persona": (
            persona.get(
                "persona_id"
            )
            == DEFAULT_PERSONA_ID
        ),
        "envoy_cognitive_projection": (
            cognitive.get(
                "owner"
            )
            == PERSONA_OWNER
        ),
        "envoy_cognitive_execution_owner": (
            cognitive.get(
                "execution_owner"
            )
            == EXECUTION_OWNER
        ),
        "opus_execution_owner": (
            opus_projection.get(
                "execution_owner"
            )
            == EXECUTION_OWNER
        ),
        "envoy_cannot_select_provider": (
            opus_projection.get(
                "envoy_may_select_provider"
            )
            is False
        ),
        "envoy_cannot_select_model": (
            opus_projection.get(
                "envoy_may_select_model"
            )
            is False
        ),
        "coda_ready": (
            coda_status.get(
                "ready"
            )
            is True
        ),
        "coda_receipts": (
            coda_status.get(
                "receipts"
            )
            is True
        ),
        "coda_mutation_plans": (
            coda_status.get(
                "mutation_plans"
            )
            is True
        ),
        "trait_history_append_available": (
            callable(
                getattr(
                    trait_store,
                    "append_decision",
                    None,
                )
            )
        ),
        "trait_history_projection_available": (
            callable(
                getattr(
                    trait_store,
                    "accepted_trait_projection",
                    None,
                )
            )
        ),
        "trait_history_status_available": (
            isinstance(
                trait_status,
                dict,
            )
        ),
    }

    ready = all(
        checks.values()
    )

    payload = {
        "schema": SCHEMA,
        "owner": OWNER,
        "purpose": (
            "self-hosted savant "
            "development loop"
        ),
        "conversation_owner": OWNER,
        "persona_owner": (
            PERSONA_OWNER
        ),
        "execution_owner": (
            EXECUTION_OWNER
        ),
        "mutation_owner": (
            MUTATION_OWNER
        ),
        "default_persona": (
            DEFAULT_PERSONA_ID
        ),
        "persona_digest": (
            persona.get(
                "digest"
            )
            or persona.get(
                "composition_digest"
            )
        ),
        "accepted_trait_history_digest": (
            persona.get(
                "accepted_trait_history_digest"
            )
        ),
        "cognitive_layers": (
            cognitive.get(
                "layers",
                [],
            )
        ),
        "trait_history_status": (
            trait_status
        ),
        "coda_status": (
            coda_status
        ),
        "checks": checks,
        "ready": ready,
        "authoritative": False,
        "authority_effect": "none",
    }

    payload[
        "digest"
    ] = digest(
        payload
    )

    return payload


def selftest() -> dict[str, Any]:
    value = status()

    if not value[
        "ready"
    ]:
        failed = [
            name
            for name, passed
            in value[
                "checks"
            ].items()
            if not passed
        ]

        raise SelfHostedDevelopmentError(
            "self-hosted development "
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
