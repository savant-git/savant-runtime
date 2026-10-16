from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict


SAVANT_ROOT = Path(
    "/root/savant-runtime"
)

OPUS_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/opus"
)

OPUS_RUNTIME = (
    OPUS_ROOT
    / "runtime"
)

MAX_TOOL_ROUNDS = 16
MAX_IDENTICAL_TOOL_CALLS = 3

SYNTHESIS_INSTRUCTION = (
    "The bounded Palaver tool-execution budget has been exhausted. "
    "Do not request or call any additional tools. "
    "Using only the user request, supplied context, and evidence already "
    "obtained from completed tool calls, produce the best supported final "
    "answer now. Distinguish established evidence from inference and unknowns. "
    "Do not claim that unperformed investigation, validation, mutation, or "
    "execution occurred."
)


def prepare_opus_import() -> None:
    runtime_path = str(
        OPUS_RUNTIME
    )

    if runtime_path not in sys.path:
        sys.path.insert(
            0,
            runtime_path,
        )


def build_request(
    message: str,
    context: str = "",
    *,
    system: str = "",
    model: str | None = None,
    tools: list[
        Dict[str, Any]
    ] | None = None,
    tool_choice: Any = None,
    previous_response_id: str = "",
    continuation_input: list[
        Dict[str, Any]
    ] | None = None,
    provider_state: Any = None,
) -> Dict[str, Any]:
    text = str(
        message
        or ""
    ).strip()

    if (
        not text
        and continuation_input is None
    ):
        raise RuntimeError(
            "Palaver inference request "
            "missing message"
        )

    request: Dict[
        str,
        Any,
    ] = {
        "owner": "palaver",
        "message": text,
        "context": str(
            context
            or ""
        ),
        "system": str(
            system
            or ""
        ),
    }

    if model:
        request[
            "model"
        ] = str(
            model
        )

    if tools:
        request[
            "tools"
        ] = list(
            tools
        )

    if tool_choice is not None:
        request[
            "tool_choice"
        ] = tool_choice

    if previous_response_id:
        request[
            "previous_response_id"
        ] = str(
            previous_response_id
        )

    if continuation_input is not None:
        request[
            "continuation_input"
        ] = list(
            continuation_input
        )

    if provider_state is not None:
        request[
            "provider_state"
        ] = provider_state

    return request


def execute(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    prepare_opus_import()

    from router import (
        execute_text_request,
    )

    result = execute_text_request(
        request
    )

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "Opus returned invalid "
            "text inference result"
        )

    if not result.get(
        "ok"
    ):
        raise RuntimeError(
            str(
                result.get(
                    "error"
                )
                or (
                    "Opus text "
                    "inference failed"
                )
            )
        )

    return result


def _call_fingerprint(
    name: str,
    arguments: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "name": name,
            "arguments": arguments,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def _synthesis_request(
    message: str,
    context: str,
    *,
    system: str,
    model: str | None,
    previous_response_id: str,
    continuation: list[
        Dict[str, Any]
    ],
    provider_state: Any,
) -> Dict[str, Any]:
    synthesis_context = "\n\n".join(
        part
        for part in (
            str(
                context
                or ""
            ).strip(),
            SYNTHESIS_INSTRUCTION,
        )
        if part
    )

    return build_request(
        message,
        synthesis_context,
        system=system,
        model=model,
        tools=None,
        tool_choice=None,
        previous_response_id=(
            previous_response_id
        ),
        continuation_input=(
            continuation
        ),
        provider_state=(
            provider_state
        ),
    )


def _finalize_synthesis(
    request: Dict[str, Any],
    history: list[
        dict[str, Any]
    ],
) -> str:
    result = execute(
        request
    )

    raw_calls = result.get(
        "tool_calls",
        [],
    )

    tool_calls = (
        raw_calls
        if isinstance(
            raw_calls,
            list,
        )
        else []
    )

    if tool_calls:
        raise RuntimeError(
            "Palaver synthesis round "
            "requested tools after tools "
            "were disabled; history="
            + json.dumps(
                history,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

    text = str(
        result.get(
            "text"
        )
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Palaver synthesis round "
            "returned no final text; "
            "history="
            + json.dumps(
                history,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

    return text


def infer(
    message: str,
    context: str = "",
    *,
    system: str = "",
    model: str | None = None,
) -> str:
    from tool_broker import (
        execute_bound,
        is_bound,
        tool_schemas,
    )

    tools = (
        tool_schemas()
        if is_bound()
        else []
    )

    request = build_request(
        message,
        context,
        system=system,
        model=model,
        tools=tools,
        tool_choice=(
            "auto"
            if tools
            else None
        ),
    )

    rounds = 0

    call_counts: dict[
        str,
        int,
    ] = {}

    history: list[
        dict[str, Any]
    ] = []

    while True:
        rounds += 1

        result = execute(
            request
        )

        raw_calls = result.get(
            "tool_calls",
            [],
        )

        tool_calls = (
            raw_calls
            if isinstance(
                raw_calls,
                list,
            )
            else []
        )

        if not tool_calls:
            text = str(
                result.get(
                    "text"
                )
                or ""
            ).strip()

            if not text:
                raise RuntimeError(
                    "Opus returned neither "
                    "text nor tool calls"
                )

            return text

        provider_response_id = str(
            result.get(
                "provider_response_id"
            )
            or ""
        ).strip()

        provider_state = result.get(
            "provider_state"
        )

        if (
            not provider_response_id
            and provider_state is None
        ):
            raise RuntimeError(
                "Opus tool response lacks "
                "continuation state"
            )

        continuation: list[
            Dict[str, Any]
        ] = []

        round_record: dict[
            str,
            Any,
        ] = {
            "round": rounds,
            "provider_response_id": (
                provider_response_id
            ),
            "provider_state_present": (
                provider_state is not None
            ),
            "calls": [],
        }

        for raw_call in tool_calls:
            if not isinstance(
                raw_call,
                dict,
            ):
                continue

            call_id = str(
                raw_call.get(
                    "call_id"
                )
                or ""
            ).strip()

            name = str(
                raw_call.get(
                    "name"
                )
                or ""
            ).strip()

            arguments = raw_call.get(
                "arguments"
            )

            if not isinstance(
                arguments,
                dict,
            ):
                arguments = {}

            if not call_id:
                raise RuntimeError(
                    "Opus tool call missing "
                    "call_id"
                )

            if not name:
                raise RuntimeError(
                    "Opus tool call missing "
                    "name"
                )

            fingerprint = (
                _call_fingerprint(
                    name,
                    arguments,
                )
            )

            call_counts[
                fingerprint
            ] = (
                call_counts.get(
                    fingerprint,
                    0,
                )
                + 1
            )

            receipt = execute_bound(
                name,
                arguments,
            )

            round_record[
                "calls"
            ].append(
                {
                    "call_id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "repeat_count": (
                        call_counts[
                            fingerprint
                        ]
                    ),
                    "receipt_ok": (
                        receipt.get(
                            "ok"
                        )
                        if isinstance(
                            receipt,
                            dict,
                        )
                        else None
                    ),
                    "receipt_error": (
                        receipt.get(
                            "error"
                        )
                        if isinstance(
                            receipt,
                            dict,
                        )
                        else None
                    ),
                }
            )

            if (
                call_counts[
                    fingerprint
                ]
                > MAX_IDENTICAL_TOOL_CALLS
            ):
                history.append(
                    round_record
                )

                raise RuntimeError(
                    "Palaver repeated identical "
                    "tool call more than "
                    f"{MAX_IDENTICAL_TOOL_CALLS} "
                    "times; call="
                    + fingerprint
                    + "; history="
                    + json.dumps(
                        history,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                )

            continuation.append(
                {
                    "type": (
                        "function_call_output"
                    ),
                    "call_id": call_id,
                    "output": json.dumps(
                        receipt,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    ),
                }
            )

        history.append(
            round_record
        )

        if not continuation:
            raise RuntimeError(
                "Opus requested tools but "
                "produced no executable calls"
            )

        if rounds >= MAX_TOOL_ROUNDS:
            synthesis_request = (
                _synthesis_request(
                    message,
                    context,
                    system=system,
                    model=model,
                    previous_response_id=(
                        provider_response_id
                    ),
                    continuation=(
                        continuation
                    ),
                    provider_state=(
                        provider_state
                    ),
                )
            )

            return _finalize_synthesis(
                synthesis_request,
                history,
            )

        request = build_request(
            message,
            context,
            system=system,
            model=model,
            tools=tools,
            tool_choice="auto",
            previous_response_id=(
                provider_response_id
            ),
            continuation_input=(
                continuation
            ),
            provider_state=(
                provider_state
            ),
        )


def integration_status() -> Dict[str, Any]:
    from tool_broker import (
        status as broker_status,
    )

    broker = broker_status()

    return {
        "owner": "palaver",
        "delegates_to": "opus",
        "route": "text_inference_route",
        "provider_specific_logic": False,
        "opus_runtime": str(
            OPUS_RUNTIME
        ),
        "opus_runtime_present": (
            OPUS_RUNTIME.is_dir()
        ),
        "tool_loop": True,
        "tool_loop_owner": "palaver",
        "tool_broker_bound": (
            broker.get(
                "bound"
            )
        ),
        "tool_count": (
            broker.get(
                "tool_count"
            )
        ),
        "max_tool_rounds": (
            MAX_TOOL_ROUNDS
        ),
        "max_identical_tool_calls": (
            MAX_IDENTICAL_TOOL_CALLS
        ),
        "cycle_detection": True,
        "provider_neutral_continuation": True,
        "provider_state_passthrough": True,
        "bounded_synthesis": True,
        "synthesis_after_tool_budget": True,
        "synthesis_tools_disabled": True,
        "unrestricted_shell": False,
        "mutation_owner": "coda",
        "retrieval_owner": "scrybe",
        "authority_effect": "none",
    }
