#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

import yaml


schema = "savant.lexicon.semantic-identity.v2"
authority_effect = "none"

DEFAULT_REGISTRY = Path("/root/savant-runtime/lexicon/registry.yaml")

_RESERVED_BINDINGS: Mapping[str, str] = MappingProxyType(
    {
        "truth": "lex:core:truth",
        "determinism": "lex:core:determinism",
        "deterministic": "lex:core:determinism",
        "runtime": "lex:implementation:igneo",
        "relationship": "lex:core:kindred",
        "relationships": "lex:core:kindred",
        "kindred": "lex:core:kindred",
        "segue": "lex:core:segue",
        "provenance": "lex:core:provenance",
        "lineage": "lex:core:lineage",
        "authority": "lex:core:authority",
        "evidence": "lex:primitive:evidence",
        "canon": "lex:primitive:canon",
        "projection": "lex:core:wavre",
        "projections": "lex:core:wavre",
        "instance": "lex:core:shade",
        "instances": "lex:core:shade",
        "interface": "lex:implementation:inface",
        "graph": "lex:implementation:gridd",
        "graphs": "lex:implementation:gridd",
    }
)
_RESERVED_IDS = frozenset(_RESERVED_BINDINGS.values())
_PRIMARY_TOKEN_BY_ID: Mapping[str, str] = MappingProxyType(
    {
        lexeme_id: next(
            token for token, candidate in _RESERVED_BINDINGS.items() if candidate == lexeme_id
        )
        for lexeme_id in sorted(_RESERVED_IDS)
    }
)

_TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]*", re.IGNORECASE)

VERIFICATION_OWNER_REF = "exile:notary"

TRUTH_STATES = (
    "unknown",
    "claimed",
    "supported",
    "contested",
    "contradicted",
    "verified",
)

_TRUTH_MINIMUM_RANK: Mapping[str, int] = MappingProxyType(
    {
        "unknown": 0,
        "claimed": 1,
        "supported": 2,
        "verified": 3,
    }
)

_TRUTH_STATE_RANK: Mapping[str, int] = MappingProxyType(
    {
        "contradicted": -1,
        "contested": -1,
        "unknown": 0,
        "claimed": 1,
        "supported": 2,
        "verified": 3,
    }
)


class SemanticIdentityError(ValueError):
    pass


class TruthError(SemanticIdentityError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SemanticIdentityError(f"value is not canonical-json compatible: {exc}") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_ref(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, slots=True)
class SemanticIdentity:
    token: str
    lexeme_id: str
    canonical: str
    concept: str
    status: str
    registry_digest: str

    def ref(self) -> str:
        return self.lexeme_id

    def as_dict(self) -> dict[str, str]:
        return {
            "token": self.token,
            "lexeme_id": self.lexeme_id,
            "canonical": self.canonical,
            "concept": self.concept,
            "status": self.status,
            "registry_digest": self.registry_digest,
        }


class SemanticIdentityRegistry:
    def __init__(self, registry_path: str | Path = DEFAULT_REGISTRY) -> None:
        self.registry_path = Path(registry_path).resolve()
        self._lock = threading.RLock()
        self._loaded_digest: str | None = None
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_canonical: dict[str, tuple[str, ...]] = {}
        self._instances: dict[str, SemanticIdentity] = {}

    @property
    def reserved_bindings(self) -> Mapping[str, str]:
        return _RESERVED_BINDINGS

    def _load(self) -> None:
        with self._lock:
            if not self.registry_path.is_file():
                raise SemanticIdentityError(f"missing lexicon registry: {self.registry_path}")
            source = self.registry_path.read_bytes()
            digest = _file_digest_bytes(source)
            if digest == self._loaded_digest:
                return
            try:
                raw = yaml.safe_load(source.decode("utf-8"))
            except (UnicodeDecodeError, yaml.YAMLError) as exc:
                raise SemanticIdentityError(f"invalid lexicon registry: {exc}") from exc
            if not isinstance(raw, Mapping):
                raise SemanticIdentityError("lexicon registry root must be a mapping")
            lexemes = raw.get("lexemes")
            if not isinstance(lexemes, list):
                raise SemanticIdentityError("lexicon registry lexemes must be a list")

            by_id: dict[str, dict[str, Any]] = {}
            by_canonical: dict[str, list[str]] = {}
            for record in lexemes:
                if not isinstance(record, Mapping):
                    continue
                lexeme_id = _clean_ref(record.get("id"))
                canonical = _clean_ref(record.get("canonical"))
                if not lexeme_id or not canonical:
                    continue
                if lexeme_id in by_id:
                    raise SemanticIdentityError(f"duplicate lexeme id: {lexeme_id}")
                by_id[lexeme_id] = dict(record)
                by_canonical.setdefault(canonical.casefold(), []).append(lexeme_id)

            missing = sorted(_RESERVED_IDS - set(by_id))
            if missing:
                raise SemanticIdentityError(
                    "semantic identity registry is missing required lexemes: "
                    + ", ".join(missing)
                )

            self._by_id = by_id
            self._by_canonical = {
                key: tuple(sorted(ids)) for key, ids in by_canonical.items()
            }
            self._instances.clear()
            self._loaded_digest = digest

    @property
    def registry_digest(self) -> str:
        self._load()
        assert self._loaded_digest is not None
        return self._loaded_digest

    def resolve(self, token_or_id: str) -> SemanticIdentity:
        self._load()
        raw = _clean_ref(token_or_id)
        if not raw:
            raise SemanticIdentityError("semantic token is required")
        normalized = raw.casefold()
        lexeme_id = _RESERVED_BINDINGS.get(normalized)
        if lexeme_id is None and raw in self._by_id:
            lexeme_id = raw
        if lexeme_id is None:
            candidates = self._by_canonical.get(normalized, ())
            if len(candidates) == 1:
                lexeme_id = candidates[0]
            elif len(candidates) > 1:
                preferred = [candidate for candidate in candidates if candidate in _RESERVED_IDS]
                if len(preferred) == 1:
                    lexeme_id = preferred[0]
                else:
                    active = [
                        candidate
                        for candidate in candidates
                        if str(self._by_id[candidate].get("status") or "").casefold()
                        == "active"
                    ]
                    if len(active) == 1:
                        lexeme_id = active[0]
                    else:
                        raise SemanticIdentityError(
                            f"ambiguous canonical semantic token {raw!r}: {list(candidates)!r}"
                        )
        if lexeme_id is None:
            raise SemanticIdentityError(f"unbound semantic token: {raw}")

        with self._lock:
            cached = self._instances.get(lexeme_id)
            if cached is not None:
                return cached
            record = self._by_id[lexeme_id]
            stable_token = _PRIMARY_TOKEN_BY_ID.get(
                lexeme_id,
                str(record.get("canonical") or lexeme_id).casefold(),
            )
            identity = SemanticIdentity(
                token=stable_token,
                lexeme_id=lexeme_id,
                canonical=str(record.get("canonical") or ""),
                concept=str(record.get("concept") or ""),
                status=str(record.get("status") or ""),
                registry_digest=self.registry_digest,
            )
            self._instances[lexeme_id] = identity
            return identity

    def ref(self, token_or_id: str) -> str:
        return self.resolve(token_or_id).lexeme_id

    def refs(self, *tokens: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for token in tokens:
            normalized = str(token).casefold()
            result[normalized] = self.ref(normalized)
        return dict(sorted(result.items()))

    def reserved_terms_in_text(self, text: str) -> tuple[str, ...]:
        found = {
            match.group(0).casefold()
            for match in _TOKEN_RE.finditer(str(text))
            if match.group(0).casefold() in _RESERVED_BINDINGS
        }
        return tuple(sorted(found))

    def refs_for_owned_strings(self, values: Iterable[str]) -> dict[str, str]:
        tokens: set[str] = set()
        for value in values:
            tokens.update(self.reserved_terms_in_text(value))
        return self.refs(*sorted(tokens)) if tokens else {}

    def validate_bindings(self, values: Iterable[str], bindings: Mapping[str, str]) -> None:
        required = self.refs_for_owned_strings(values)
        normalized = {str(key).casefold(): str(value) for key, value in bindings.items()}
        for token, lexeme_id in required.items():
            if normalized.get(token) != lexeme_id:
                raise SemanticIdentityError(
                    f"reserved term {token!r} must resolve to {lexeme_id!r}"
                )

    def manifest(self) -> dict[str, Any]:
        self._load()
        bindings = dict(sorted(_RESERVED_BINDINGS.items()))
        result = {
            "schema": schema,
            "registry": str(self.registry_path),
            "registry_digest": self.registry_digest,
            "reserved_bindings": bindings,
            "binding_digest": _digest(bindings),
            "singleton_count": len(_RESERVED_IDS),
            "authority_effect": authority_effect,
        }
        result["digest"] = _digest(result)
        return result


def normalize_truth_state(value: Any) -> str:
    state = str(value or "unknown").strip().casefold()
    if state not in TRUTH_STATES:
        raise TruthError(f"unsupported truth state: {state}")
    return state


def truth_envelope(
    *,
    state: str = "unknown",
    evidence_refs: Sequence[str] = (),
    source_ref: str | None = None,
    carried: bool = False,
    verifier_ref: str | None = None,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> dict[str, Any]:
    registry = semantic_registry or semantic_identity
    normalized = normalize_truth_state(state)
    if not isinstance(carried, bool):
        raise TruthError("carried must be boolean")
    if isinstance(evidence_refs, (str, bytes)):
        raise TruthError("evidence_refs must be a sequence of references, not text")
    if not carried and normalized not in {"unknown", "claimed"}:
        raise TruthError(
            "source-created truth state may only be unknown or claimed; "
            "stronger states must be carried from the accepted evidence/verification boundary"
        )
    refs = sorted({_clean_ref(ref) for ref in evidence_refs if _clean_ref(ref)})
    if normalized in {"supported", "contested", "contradicted", "verified"} and not refs:
        raise TruthError(f"{normalized} truth state requires evidence_refs")
    if normalized == "verified" and not _clean_ref(verifier_ref):
        raise TruthError("verified truth state requires verifier_ref")
    result = {
        "schema": "savant.truth-envelope.v1",
        "term_ref": registry.ref("truth"),
        "state": normalized,
        "evidence_refs": refs,
        "source_ref": _clean_ref(source_ref) or None,
        "verifier_ref": _clean_ref(verifier_ref) or None,
        "carried": bool(carried),
        "authority_effect": "none",
    }
    result["digest"] = _digest(result)
    return result


def validate_truth_envelope(
    value: Mapping[str, Any],
    *,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> dict[str, Any]:
    registry = semantic_registry or semantic_identity
    if str(value.get("schema") or "") != "savant.truth-envelope.v1":
        raise TruthError("unsupported truth envelope schema")
    if str(value.get("term_ref") or "") != registry.ref("truth"):
        raise TruthError("truth envelope term_ref does not resolve to canonical truth")
    state = normalize_truth_state(value.get("state"))
    refs_raw = value.get("evidence_refs")
    if not isinstance(refs_raw, list):
        raise TruthError("truth envelope evidence_refs must be a list")
    refs = sorted({_clean_ref(ref) for ref in refs_raw if _clean_ref(ref)})
    carried_raw = value.get("carried")
    if not isinstance(carried_raw, bool):
        raise TruthError("truth envelope carried must be boolean")
    carried = carried_raw
    if value.get("authority_effect") not in {None, "none"}:
        raise TruthError("truth envelope authority_effect must be none")
    verifier_ref = _clean_ref(value.get("verifier_ref")) or None
    if not carried and state not in {"unknown", "claimed"}:
        raise TruthError("uncarried truth envelope cannot contain promoted truth state")
    if state in {"supported", "contested", "contradicted", "verified"} and not refs:
        raise TruthError(f"{state} truth state requires evidence_refs")
    if state == "verified" and not verifier_ref:
        raise TruthError("verified truth state requires verifier_ref")
    if state == "verified" and verifier_ref != VERIFICATION_OWNER_REF:
        raise TruthError(
            f"verified truth state must be carried by {VERIFICATION_OWNER_REF!r}"
        )
    if state == "verified" and verifier_ref != VERIFICATION_OWNER_REF:
        raise TruthError(
            f"verified truth state must be carried by {VERIFICATION_OWNER_REF!r}"
        )
    normalized = {
        "schema": "savant.truth-envelope.v1",
        "term_ref": registry.ref("truth"),
        "state": state,
        "evidence_refs": refs,
        "source_ref": _clean_ref(value.get("source_ref")) or None,
        "verifier_ref": verifier_ref,
        "carried": carried,
        "authority_effect": "none",
    }
    normalized["digest"] = _digest(normalized)
    supplied_digest = _clean_ref(value.get("digest"))
    if supplied_digest and supplied_digest != normalized["digest"]:
        raise TruthError("truth envelope digest mismatch")
    return normalized


def _state_from_truth_mapping(
    value: Mapping[str, Any],
    *,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> str:
    registry = semantic_registry or semantic_identity
    artifact_schema = str(value.get("schema") or "")
    if artifact_schema == "savant.truth-envelope.v1":
        return validate_truth_envelope(
            value, semantic_registry=registry
        )["state"]
    if artifact_schema.startswith("savant.truth-summary."):
        return normalize_truth_state(value.get("state"))
    if artifact_schema.startswith("savant.truth-derivation."):
        return normalize_truth_state(value.get("state"))
    if artifact_schema.startswith("savant.truth-gate."):
        summary = value.get("summary")
        if isinstance(summary, Mapping):
            return _state_from_truth_mapping(
                summary, semantic_registry=registry
            )
    return "unknown"


def truth_state_from_value(
    value: Any,
    *,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> str:
    registry = semantic_registry or semantic_identity
    if isinstance(value, Mapping):
        direct_schema = str(value.get("schema") or "")
        if direct_schema.startswith("savant.truth-"):
            state = _state_from_truth_mapping(
                value, semantic_registry=registry
            )
            if state != "unknown" or direct_schema == "savant.truth-envelope.v1":
                return state
        direct = value.get("truth")
        if isinstance(direct, Mapping):
            state = _state_from_truth_mapping(
                direct, semantic_registry=registry
            )
            if state != "unknown":
                return state
        extensions = value.get("extensions")
        if isinstance(extensions, Mapping):
            truth = extensions.get("truth")
            if isinstance(truth, Mapping):
                return _state_from_truth_mapping(
                    truth, semantic_registry=registry
                )
    return "unknown"


def truth_join(states: Iterable[str]) -> str:
    normalized = [normalize_truth_state(state) for state in states]
    if not normalized:
        return "unknown"
    state_set = set(normalized)
    positive = state_set.intersection({"supported", "verified"})
    if "contested" in state_set:
        return "contested"
    if "contradicted" in state_set and positive:
        return "contested"
    if "contradicted" in state_set:
        return "contradicted"
    if "unknown" in state_set:
        return "unknown"
    if "claimed" in state_set:
        return "claimed"
    if state_set == {"verified"}:
        return "verified"
    return "supported"


def truth_summary(
    values: Iterable[Any],
    *,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> dict[str, Any]:
    registry = semantic_registry or semantic_identity
    states = [
        truth_state_from_value(value, semantic_registry=registry)
        for value in values
    ]
    counts_raw = Counter(states)
    counts = {state: counts_raw[state] for state in TRUTH_STATES if counts_raw[state]}
    result = {
        "schema": "savant.truth-summary.v1",
        "term_ref": registry.ref("truth"),
        "state": truth_join(states),
        "counts": counts,
        "count": len(states),
        "authority_effect": "none",
    }
    result["digest"] = _digest(result)
    return result


def truth_derive(
    values: Iterable[Any],
    *,
    source_ref: str | None = None,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> dict[str, Any]:
    """Classify a new derived claim without inheriting verification."""
    registry = semantic_registry or semantic_identity
    materialized = list(values)
    summary = truth_summary(materialized, semantic_registry=registry)
    state = summary["state"]
    if state == "verified":
        state = "supported"
    input_digests = sorted(_digest(value) for value in materialized)
    result = {
        "schema": "savant.truth-derivation.v2",
        "term_ref": registry.ref("truth"),
        "determinism_ref": registry.ref("determinism"),
        "state": state,
        "input_count": len(materialized),
        "input_truth_digest": summary["digest"],
        "input_digests": input_digests,
        "source_ref": _clean_ref(source_ref) or None,
        "verification_inherited": False,
        "derivation_rule": "truth-first-no-verification-inheritance-v1",
        "authority_effect": "none",
    }
    result["digest"] = _digest(result)
    return result


def truth_satisfies(state: str, minimum: str) -> bool:
    normalized = normalize_truth_state(state)
    minimum_state = str(minimum or "unknown").strip().casefold()
    if minimum_state not in _TRUTH_MINIMUM_RANK:
        raise TruthError(f"unsupported minimum truth state: {minimum_state}")
    if minimum_state == "unknown":
        return True
    return _TRUTH_STATE_RANK[normalized] >= _TRUTH_MINIMUM_RANK[minimum_state]


def require_truth(
    values: Iterable[Any],
    minimum: str,
    *,
    allow_empty: bool = False,
    semantic_registry: SemanticIdentityRegistry | None = None,
) -> dict[str, Any]:
    registry = semantic_registry or semantic_identity
    materialized = list(values)
    minimum_state = str(minimum or "unknown").strip().casefold()
    if minimum_state not in _TRUTH_MINIMUM_RANK:
        raise TruthError(f"unsupported minimum truth state: {minimum_state}")
    if not materialized and minimum_state != "unknown" and not allow_empty:
        raise TruthError(
            f"truth requirement {minimum_state!r} cannot be satisfied by an empty value set"
        )
    states = [
        truth_state_from_value(value, semantic_registry=registry)
        for value in materialized
    ]
    failures = [
        {"index": index, "state": state}
        for index, state in enumerate(states)
        if not truth_satisfies(state, minimum_state)
    ]
    if failures:
        raise TruthError(
            f"truth requirement {minimum_state!r} failed for {len(failures)} value(s): {failures}"
        )
    summary = truth_summary(materialized, semantic_registry=registry)
    result = {
        "schema": "savant.truth-gate.v2",
        "term_ref": registry.ref("truth"),
        "minimum": minimum_state,
        "passed": True,
        "count": len(materialized),
        "allow_empty": bool(allow_empty),
        "summary": summary,
        "authority_effect": "none",
    }
    result["digest"] = _digest(
        {
            "minimum": minimum_state,
            "allow_empty": bool(allow_empty),
            "states": states,
            "summary_digest": summary["digest"],
        }
    )
    return result


semantic_identity = SemanticIdentityRegistry()


def selftest(registry_path: str | Path) -> dict[str, Any]:
    registry = SemanticIdentityRegistry(registry_path)
    truth_a = registry.resolve("truth")
    truth_b = registry.resolve("lex:core:truth")
    runtime_a = registry.resolve("runtime")
    runtime_b = registry.resolve("Igneo")
    envelope = truth_envelope(
        state="claimed",
        evidence_refs=["e:2", "e:1", "e:1"],
        source_ref="selftest",
        semantic_registry=registry,
    )
    carried = truth_envelope(
        state="verified",
        evidence_refs=["e:verified"],
        source_ref="selftest",
        carried=True,
        verifier_ref="exile:notary",
        semantic_registry=registry,
    )
    checks = {
        "truth_singleton": truth_a is truth_b,
        "runtime_singleton": runtime_a is runtime_b,
        "stable_singleton_token": runtime_a.token == runtime_b.token == "runtime",
        "runtime_binding": runtime_a.lexeme_id == "lex:implementation:igneo",
        "relationship_binding": registry.ref("relationship") == "lex:core:kindred",
        "segue_binding": registry.ref("segue") == "lex:core:segue",
        "projection_binding": registry.ref("projection") == "lex:core:wavre",
        "instance_binding": registry.ref("instance") == "lex:core:shade",
        "truth_binding": truth_a.lexeme_id == "lex:core:truth",
        "determinism_binding": registry.ref("determinism") == "lex:core:determinism",
        "claimed_envelope": envelope["state"] == "claimed",
        "evidence_deduplicated": envelope["evidence_refs"] == ["e:1", "e:2"],
        "direct_envelope_recognized": (
            truth_state_from_value(
                carried, semantic_registry=registry
            ) == "verified"
        ),
        "envelope_validates": validate_truth_envelope(
            carried, semantic_registry=registry
        )["digest"] == carried["digest"],
        "join_verified": truth_join(["verified", "verified"]) == "verified",
        "join_unknown": truth_join(["verified", "unknown"]) == "unknown",
        "join_contested": truth_join(["verified", "contradicted"]) == "contested",
        "supported_gate": truth_satisfies("verified", "supported"),
        "contradicted_rejected": not truth_satisfies("contradicted", "claimed"),
        "derived_verified_capped": truth_derive(
            [carried, carried],
            source_ref="selftest",
            semantic_registry=registry,
        )["state"] == "supported",
    }
    try:
        truth_envelope(state="verified", semantic_registry=registry)
        checks["verified_self_promotion_rejected"] = False
    except TruthError:
        checks["verified_self_promotion_rejected"] = True
    try:
        require_truth([], "claimed", semantic_registry=registry)
        checks["empty_truth_gate_rejected"] = False
    except TruthError:
        checks["empty_truth_gate_rejected"] = True
    wrong_verifier = dict(carried)
    wrong_verifier["verifier_ref"] = "exile:other"
    wrong_verifier.pop("digest", None)
    try:
        validate_truth_envelope(wrong_verifier, semantic_registry=registry)
        checks["wrong_verifier_rejected"] = False
    except TruthError:
        checks["wrong_verifier_rejected"] = True
    forged_nested = {
        "extensions": {
            "truth": {"state": "verified"}
        }
    }
    checks["unstructured_verified_not_trusted"] = (
        truth_state_from_value(
            forged_nested, semantic_registry=registry
        ) == "unknown"
    )

    tampered = dict(carried)
    tampered["state"] = "supported"
    try:
        validate_truth_envelope(tampered, semantic_registry=registry)
        checks["tampered_envelope_rejected"] = False
    except TruthError:
        checks["tampered_envelope_rejected"] = True
    result = {
        "schema": "savant.lexicon.semantic-identity-selftest.v2",
        "ok": all(checks.values()),
        "checks": checks,
        "registry_digest": registry.registry_digest,
        "authority_effect": authority_effect,
    }
    result["digest"] = _digest(result)
    return result


__all__ = [
    "SemanticIdentity",
    "SemanticIdentityError",
    "SemanticIdentityRegistry",
    "TruthError",
    "TRUTH_STATES",
    "VERIFICATION_OWNER_REF",
    "normalize_truth_state",
    "truth_envelope",
    "validate_truth_envelope",
    "truth_join",
    "truth_state_from_value",
    "truth_summary",
    "truth_derive",
    "truth_satisfies",
    "require_truth",
    "semantic_identity",
    "selftest",
]
