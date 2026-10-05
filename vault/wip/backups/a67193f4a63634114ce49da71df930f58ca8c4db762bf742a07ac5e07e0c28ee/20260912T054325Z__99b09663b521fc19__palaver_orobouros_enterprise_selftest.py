#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


from conversation_envelope import (
    project as project_envelope,
)

from orobouros_bridge import (
    project_for_message,
)

from persona_session_continuity import (
    previous_traits,
    record as record_persona_receipt,
)

from session_store import (
    session_store,
)


schema = (
    "savant://runtime/palaver/"
    "orobouros-enterprise-selftest/1.0.0"
)

owner = "exile:palaver"


class enterprise_selftest_error(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise enterprise_selftest_error(
            message
        )


def store_for(
    database: Path,
) -> Any:
    return session_store(
        database
    )


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="palaver-orobouros-"
    ) as directory:
        database = (
            Path(directory)
            / "sessions.sqlite3"
        )

        session_id = (
            "palses_"
            + "1" * 32
        )

        first_request_id = (
            "palreq_"
            + "2" * 32
        )

        second_request_id = (
            "palreq_"
            + "3" * 32
        )

        first_message = (
            "Analyze this architecture, "
            "verify authority boundaries, "
            "and implement the runtime safely."
        )

        second_message = (
            "Continue the implementation "
            "while preserving authority, "
            "context, and deterministic behavior."
        )

        store = store_for(
            database
        )

        session = store.ensure_session(
            session_id
        )

        require(
            isinstance(
                session,
                dict,
            ),
            "session was not created",
        )

        first_persona = (
            project_for_message(
                first_message,
                previous_traits=(),
                actor=session_id,
            )
        )

        require(
            first_persona.get(
                "owner"
            )
            == "envoy",
            "first persona owner is not Envoy",
        )

        require(
            first_persona.get(
                "persona_id"
            )
            == "orobouros",
            "first persona is not Orobouros",
        )

        first_receipt = (
            first_persona.get(
                "composition_receipt"
            )
        )

        require(
            isinstance(
                first_receipt,
                dict,
            ),
            "first composition receipt missing",
        )

        first_traits = tuple(
            first_receipt.get(
                "active_traits"
            )
            or ()
        )

        require(
            record_persona_receipt(
                store,
                session_id=
                    session_id,
                request_id=
                    first_request_id,
                receipt=
                    first_receipt,
            ),
            "first persona receipt was not persisted",
        )

        first_envelope = (
            project_envelope(
                session_id=
                    session_id,
                request_id=
                    first_request_id,
                message=
                    first_message,
                persona=
                    first_persona,
            )
        )

        require(
            first_envelope.get(
                "authority"
            )
            .get(
                "authority_effect"
            )
            == "none",
            "first envelope changed authority",
        )

        require(
            first_envelope.get(
                "ownership"
            )
            .get(
                "persona"
            )
            == "envoy",
            "first envelope changed persona ownership",
        )

        require(
            first_envelope.get(
                "ownership"
            )
            .get(
                "provider_execution"
            )
            == "opus",
            "first envelope changed provider ownership",
        )

        del store

        reopened = store_for(
            database
        )

        recovered_traits = (
            previous_traits(
                reopened,
                session_id,
            )
        )

        require(
            recovered_traits
            == tuple(
                sorted(
                    {
                        str(value)
                        .strip()
                        .lower()
                        for value
                        in first_traits
                        if str(
                            value
                            or ""
                        ).strip()
                    }
                )
            ),
            "trait continuity failed after restart",
        )

        second_persona = (
            project_for_message(
                second_message,
                previous_traits=
                    recovered_traits,
                actor=session_id,
            )
        )

        require(
            second_persona.get(
                "owner"
            )
            == "envoy",
            "second persona owner is not Envoy",
        )

        second_receipt = (
            second_persona.get(
                "composition_receipt"
            )
        )

        require(
            isinstance(
                second_receipt,
                dict,
            ),
            "second composition receipt missing",
        )

        require(
            record_persona_receipt(
                reopened,
                session_id=
                    session_id,
                request_id=
                    second_request_id,
                receipt=
                    second_receipt,
            ),
            "second persona receipt was not persisted",
        )

        second_envelope = (
            project_envelope(
                session_id=
                    session_id,
                request_id=
                    second_request_id,
                message=
                    second_message,
                persona=
                    second_persona,
                parent_request_id=
                    first_request_id,
            )
        )

        require(
            second_envelope.get(
                "parent_request_id"
            )
            == first_request_id,
            "request lineage was not preserved",
        )

        require(
            second_envelope.get(
                "persona"
            )
            .get(
                "composition_digest"
            )
            == second_persona.get(
                "composition_digest"
            ),
            "persona composition was not bound "
            "to conversation envelope",
        )

        replay_persona = (
            project_for_message(
                second_message,
                previous_traits=
                    recovered_traits,
                actor=session_id,
            )
        )

        require(
            replay_persona.get(
                "composition_digest"
            )
            == second_persona.get(
                "composition_digest"
            ),
            "Orobouros composition replay diverged",
        )

        require(
            replay_persona.get(
                "reflection_digest"
            )
            == second_persona.get(
                "reflection_digest"
            ),
            "Orobouros reflection replay diverged",
        )

        replay_envelope = (
            project_envelope(
                session_id=
                    session_id,
                request_id=
                    second_request_id,
                message=
                    second_message,
                persona=
                    replay_persona,
                parent_request_id=
                    first_request_id,
            )
        )

        require(
            replay_envelope.get(
                "envelope_digest"
            )
            == second_envelope.get(
                "envelope_digest"
            ),
            "conversation envelope replay diverged",
        )

        final_traits = (
            previous_traits(
                reopened,
                session_id,
            )
        )

        expected_final = tuple(
            sorted(
                {
                    str(value)
                    .strip()
                    .lower()
                    for value
                    in (
                        second_receipt.get(
                            "active_traits"
                        )
                        or ()
                    )
                    if str(
                        value
                        or ""
                    ).strip()
                }
            )
        )

        require(
            final_traits
            == expected_final,
            "latest persona receipt did not "
            "become continuity projection",
        )

        reflection = (
            second_persona.get(
                "reflection"
            )
        )

        require(
            isinstance(
                reflection,
                dict,
            ),
            "reflection projection missing",
        )

        require(
            reflection.get(
                "moral_self_mutated"
            )
            is False,
            "reflection mutated moral self",
        )

        require(
            reflection.get(
                "provider_executed"
            )
            is False,
            "reflection executed provider",
        )

        require(
            reflection.get(
                "conversation_mutated"
            )
            is False,
            "reflection mutated conversation",
        )

        require(
            second_persona.get(
                "provider_execution"
            )
            is False,
            "Orobouros crossed Opus boundary",
        )

        require(
            second_persona.get(
                "conversation_ownership"
            )
            is False,
            "Orobouros crossed Palaver boundary",
        )

        receipts = reopened.receipts(
            session_id
        )

        require(
            len(
                receipts
            )
            >= 2,
            "persona receipt history incomplete",
        )

        output = {
            "schema":
                schema,
            "owner":
                owner,
            "ok":
                True,
            "session_id":
                session_id,
            "restart_recovery":
                True,
            "multi_turn_continuity":
                True,
            "request_lineage":
                True,
            "deterministic_persona_replay":
                True,
            "deterministic_envelope_replay":
                True,
            "persona_owner":
                "envoy",
            "conversation_owner":
                "palaver",
            "provider_owner":
                "opus",
            "task_owner":
                "niche",
            "mutation_owner":
                "coda",
            "persistent_store_authoritative":
                False,
            "persona_receipt_count":
                len(
                    receipts
                ),
            "first_trait_count":
                len(
                    first_traits
                ),
            "second_trait_count":
                len(
                    expected_final
                ),
            "authority_effect":
                "none",
        }

        print(
            json.dumps(
                output,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
