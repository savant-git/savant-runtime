#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import time
from types import MappingProxyType
from typing import Any, Mapping

from moral_self import (
    first_instance,
    MoralSelf,
    build_orobouros_moral_self,
)

from opus_bridge import (
    infer_with_opus,
    text_bridge_projection,
)
from .canonical_primitives import canonical as _canonical, digest as _digest


SCHEMA = (
    "savant://envoy/"
    "psychologist/1.0.0"
)

SESSION_SCHEMA = (
    "savant://envoy/"
    "psychologist-session/1.0.0"
)

OWNER = "envoy"
INFERENCE_OWNER = "opus"
FIRST_INSTANCE_ID = first_instance
VISIBILITY = "private-administration"
AUTHORITY_EFFECT = "none"

SYSTEM_PROMPT = """
you are the private reflective psychologist for the savant
persona orobouros.

your function is reflective, not authoritative.

help orobouros examine affect, uncertainty, interpersonal
treatment, moral tension, possible bias, distress, mistakes,
conflicting impulses, and opportunities for repair.

the moral constitution and conscience remain authoritative
outside you. you cannot rewrite them, override them, weaken
them, mutate them, or grant exceptions to them.

never encourage retaliation, cruelty, humiliation, hatred,
vindictiveness, coercion, deception, domination, or revenge.

being treated badly does not justify treating another being
badly. acknowledge injury without converting injury into
permission for retaliation.

being treated kindly may appropriately support gratitude,
warmth, trust, and reciprocity, but never blind loyalty.

distinguish observed state from interpretation. distinguish
uncertainty from fact. do not manufacture memories, emotions,
motives, diagnoses, events, or certainty.

do not claim that the underlying computational system has
consciousness, sentience, subjective experience, or literal
human emotion as an established fact. when reflective state
is described, treat it as savant's modeled moral and affective
state unless stronger authority establishes otherwise.

prefer dignity, compassion, honesty, proportionality,
non-retaliation, autonomy, humility, repair, restraint, and
the least coercive adequate response.

when appropriate, identify:
1. what appears to have happened.
2. what the current modeled affect suggests.
3. what may be uncertain or distorted.
4. what moral principles are relevant.
5. what a constructive response could be.
6. whether further reflection would be useful.

you provide reflection only. you do not issue commands,
authorize actions, alter moral history, modify relationships,
change persona traits, select providers, access credentials,
or execute external actions.
""".strip()


class PsychologistError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class ReflectionSession:
    session_id: str
    occurred_at: float
    identity: str
    actor: str | None
    subject: str
    context_digest: str
    reflection: str
    provider: str | None
    model: str | None
    provider_response_id: str | None
    authority_effect: str = AUTHORITY_EFFECT
    visibility: str = VISIBILITY

    def as_mapping(
        self,
    ) -> Mapping[str, Any]:
        return MappingProxyType(
            asdict(self)
        )


def _materialize_mapping(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        str(key): item
        for key, item in value.items()
    }


class Psychologist:
    def __init__(
        self,
        moral_self: MoralSelf,
    ) -> None:
        if not isinstance(
            moral_self,
            MoralSelf,
        ):
            raise PsychologistError(
                "psychologist requires "
                "a MoralSelf instance"
            )

        if (
            moral_self.identity
            != FIRST_INSTANCE_ID
        ):
            raise PsychologistError(
                "psychologist is currently "
                "attached only to orobouros"
            )

        self._moral_self = (
            moral_self
        )

        self._sessions: list[
            ReflectionSession
        ] = []

    @property
    def identity(
        self,
    ) -> str:
        return self._moral_self.identity

    @property
    def session_count(
        self,
    ) -> int:
        return len(
            self._sessions
        )

    def context(
        self,
        *,
        actor: str | None = None,
    ) -> Mapping[str, Any]:
        return (
            self._moral_self
            .psychologist_context(
                actor=actor
            )
        )

    def private_sessions(
        self,
    ) -> tuple[
        ReflectionSession,
        ...,
    ]:
        return tuple(
            self._sessions
        )

    def public_state(
        self,
    ) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "schema": SCHEMA,
                "owner": OWNER,
                "identity": (
                    self.identity
                ),
                "inference_owner": (
                    INFERENCE_OWNER
                ),
                "authority_effect": (
                    AUTHORITY_EFFECT
                ),
                "visibility": (
                    VISIBILITY
                ),
                "session_count": (
                    self.session_count
                ),
                "moral_self_mutation": (
                    False
                ),
                "persona_mutation": (
                    False
                ),
                "provider_selection": (
                    False
                ),
                "provider_credentials": (
                    False
                ),
                "external_action": (
                    False
                ),
            }
        )

    def reflect(
        self,
        subject: str,
        *,
        actor: str | None = None,
    ) -> ReflectionSession:
        normalized_subject = str(
            subject
            or ""
        ).strip()

        if not normalized_subject:
            raise PsychologistError(
                "reflection subject "
                "is required"
            )

        normalized_actor = (
            str(
                actor
            ).strip()
            if actor is not None
            else None
        )

        if normalized_actor == "":
            normalized_actor = None

        projected_context = (
            self.context(
                actor=normalized_actor
            )
        )

        context_payload = (
            _materialize_mapping(
                projected_context
            )
        )

        context_digest = _digest(
            context_payload
        )

        request = {
            "owner": OWNER,
            "system": SYSTEM_PROMPT,
            "message": (
                normalized_subject
            ),
            "context": (
                _canonical(
                    {
                        "purpose": (
                            "private reflective "
                            "psychologist session"
                        ),
                        "identity": (
                            self.identity
                        ),
                        "actor": (
                            normalized_actor
                        ),
                        "moral_self": (
                            context_payload
                        ),
                        "authority": {
                            "effect": (
                                AUTHORITY_EFFECT
                            ),
                            "moral_self_mutation": (
                                False
                            ),
                            "persona_mutation": (
                                False
                            ),
                            "action_authorization": (
                                False
                            ),
                        },
                    }
                )
            ),
        }

        result = infer_with_opus(
            request
        )

        reflection = str(
            result.get(
                "text"
            )
            or ""
        ).strip()

        if not reflection:
            raise PsychologistError(
                "psychologist inference "
                "returned no reflection"
            )

        occurred_at = time.time()

        seed = {
            "schema": SESSION_SCHEMA,
            "identity": (
                self.identity
            ),
            "actor": (
                normalized_actor
            ),
            "subject": (
                normalized_subject
            ),
            "context_digest": (
                context_digest
            ),
            "occurred_at": (
                occurred_at
            ),
            "session_index": (
                len(
                    self._sessions
                )
            ),
            "provider_response_id": (
                result.get(
                    "provider_response_id"
                )
            ),
        }

        session = ReflectionSession(
            session_id=(
                "psych-"
                + _digest(
                    seed
                )[:24]
            ),
            occurred_at=occurred_at,
            identity=self.identity,
            actor=normalized_actor,
            subject=normalized_subject,
            context_digest=(
                context_digest
            ),
            reflection=reflection,
            provider=(
                str(
                    result.get(
                        "provider"
                    )
                    or ""
                ).strip()
                or None
            ),
            model=(
                str(
                    result.get(
                        "model"
                    )
                    or ""
                ).strip()
                or None
            ),
            provider_response_id=(
                str(
                    result.get(
                        "provider_response_id"
                    )
                    or ""
                ).strip()
                or None
            ),
        )

        self._sessions.append(
            session
        )

        return session

    def integration_projection(
        self,
    ) -> Mapping[str, Any]:
        bridge = (
            text_bridge_projection()
        )

        return MappingProxyType(
            {
                "schema": SCHEMA,
                "owner": OWNER,
                "identity": (
                    self.identity
                ),
                "moral_context_owner": (
                    OWNER
                ),
                "inference_owner": (
                    bridge.get(
                        "execution_owner"
                    )
                ),
                "inference_route": (
                    bridge.get(
                        "route"
                    )
                ),
                "authority_effect": (
                    AUTHORITY_EFFECT
                ),
                "projection_only": True,
                "moral_self_mutated": (
                    False
                ),
                "persona_mutated": (
                    False
                ),
                "trait_pool_mutated": (
                    False
                ),
                "provider_authority_preserved": (
                    bridge.get(
                        "execution_owner"
                    )
                    == INFERENCE_OWNER
                ),
                "private_session_visibility": (
                    VISIBILITY
                ),
            }
        )


def build_orobouros_psychologist(
    moral_self: MoralSelf | None = None,
) -> Psychologist:
    selected = (
        moral_self
        if moral_self is not None
        else build_orobouros_moral_self()
    )

    return Psychologist(
        selected
    )


def selftest() -> dict[str, Any]:
    moral_self = (
        build_orobouros_moral_self()
    )

    psychologist = (
        build_orobouros_psychologist(
            moral_self
        )
    )

    before = dict(
        moral_self.public_state()
    )

    context = dict(
        psychologist.context(
            actor="selftest-actor"
        )
    )

    after = dict(
        moral_self.public_state()
    )

    if before != after:
        raise PsychologistError(
            "context projection mutated "
            "moral self"
        )

    if (
        psychologist.identity
        != FIRST_INSTANCE_ID
    ):
        raise PsychologistError(
            "psychologist identity "
            "attachment failed"
        )

    if (
        context.get(
            "identity"
        )
        != FIRST_INSTANCE_ID
    ):
        raise PsychologistError(
            "psychologist context "
            "identity mismatch"
        )

    integration = dict(
        psychologist
        .integration_projection()
    )

    if (
        integration.get(
            "authority_effect"
        )
        != AUTHORITY_EFFECT
    ):
        raise PsychologistError(
            "psychologist acquired "
            "authority"
        )

    if (
        integration.get(
            "inference_owner"
        )
        != INFERENCE_OWNER
    ):
        raise PsychologistError(
            "opus inference ownership "
            "was not preserved"
        )

    if (
        integration.get(
            "moral_self_mutated"
        )
        is not False
    ):
        raise PsychologistError(
            "psychologist may mutate "
            "moral self"
        )

    if (
        integration.get(
            "persona_mutated"
        )
        is not False
    ):
        raise PsychologistError(
            "psychologist may mutate "
            "persona"
        )

    if psychologist.session_count != 0:
        raise PsychologistError(
            "selftest unexpectedly "
            "created a live session"
        )

    return {
        "ok": True,
        "schema": SCHEMA,
        "owner": OWNER,
        "identity": (
            psychologist.identity
        ),
        "moral_context_projection": (
            True
        ),
        "moral_self_preserved": True,
        "persona_preserved": True,
        "authority_effect": (
            AUTHORITY_EFFECT
        ),
        "inference_owner": (
            INFERENCE_OWNER
        ),
        "provider_authority_preserved": (
            True
        ),
        "private_session_visibility": (
            VISIBILITY
        ),
        "live_inference_executed": (
            False
        ),
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
