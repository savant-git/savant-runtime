#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import litellm
except ImportError:
    litellm = None

try:
    from opentelemetry import trace
except ImportError:
    trace = None


runtime_root = Path("/root/savant-runtime")
chimera_root = runtime_root / "runtime" / "chimera"
database_path = chimera_root / "chimera.sqlite3"

schema_version = "savant.chimera.v1"
authority_effect = "none"
default_timeout_seconds = 180.0
default_parallelism = 4
default_max_calls = 16
default_max_tokens = 2400
default_conflict_threshold = 0.28
default_temperature = 0.35


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: Any, width: int = 24) -> str:
    return f"{prefix}_{fingerprint(value)[:width]}"


def now_ns() -> int:
    return time.time_ns()


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def normalize_text(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s\-./]", "", value)
    return value.strip()


def lexical_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_./-]{3,}", value.casefold())
        if token
    }


def jaccard(left: str, right: str) -> float:
    a = lexical_tokens(left)
    b = lexical_tokens(right)

    if not a and not b:
        return 1.0

    union = a | b
    if not union:
        return 0.0

    return len(a & b) / len(union)


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    raise ValueError("model response did not contain a valid JSON object")


def read_models() -> list[str]:
    raw = os.environ.get("SAVANT_CHIMERA_MODELS", "").strip()

    if not raw:
        return []

    models = []
    seen = set()

    for candidate in raw.split(","):
        model = candidate.strip()

        if not model or model in seen:
            continue

        seen.add(model)
        models.append(model)

    return models


@dataclass(frozen=True)
class Role:
    name: str
    mood: str
    representation: str
    objective: str


roles: tuple[Role, ...] = (
    Role(
        name="architect",
        mood="constructive",
        representation="systems_graph",
        objective=(
            "Construct the strongest coherent solution while preserving "
            "constraints, interfaces, authority boundaries, reversibility, "
            "and deterministic behavior."
        ),
    ),
    Role(
        name="skeptic",
        mood="adversarial",
        representation="falsification_tree",
        objective=(
            "Attack assumptions and proposed conclusions. Seek counterexamples, "
            "unsupported certainty, hidden coupling, and conditions under which "
            "the apparent solution fails."
        ),
    ),
    Role(
        name="constraint_analyst",
        mood="reductive",
        representation="constraint_system",
        objective=(
            "Reduce the problem to explicit invariants, hard constraints, "
            "dependencies, prohibited transitions, and unresolved unknowns."
        ),
    ),
    Role(
        name="forensic",
        mood="forensic",
        representation="evidence_graph",
        objective=(
            "Separate sourced fact, observed implementation, inference, "
            "speculation, and unknown. Trace provenance for every material claim."
        ),
    ),
    Role(
        name="counterfactual",
        mood="counterfactual",
        representation="worldline",
        objective=(
            "Develop a materially different solution worldline and determine "
            "what assumptions would have to be true for it to dominate."
        ),
    ),
    Role(
        name="novelty",
        mood="speculative",
        representation="representation_mutation",
        objective=(
            "Search uncommon but technically defensible solution families. "
            "Do not optimize for novelty alone and do not relax constraints."
        ),
    ),
    Role(
        name="implementation",
        mood="minimal",
        representation="executable_state_machine",
        objective=(
            "Translate the problem into the smallest executable implementation "
            "that preserves required behavior and exposes concrete failure modes."
        ),
    ),
    Role(
        name="verifier",
        mood="formal",
        representation="verification_lattice",
        objective=(
            "Identify deterministic tests, measurements, experiments, or "
            "external observations that can distinguish competing claims."
        ),
    ),
)


@dataclass
class Instance:
    instance_id: str
    model: str
    role: str
    mood: str
    representation: str
    objective: str
    generation: int = 0
    worldline: str = "primary"


@dataclass
class Claim:
    claim_id: str
    run_id: str
    instance_id: str
    model: str
    role: str
    mood: str
    text: str
    normalized: str
    polarity: str
    confidence: float
    evidence: list[str]
    assumptions: list[str]
    proposed_tests: list[str]
    status: str = "hypothesis"


@dataclass
class ModelResult:
    instance: Instance
    claims: list[Claim]
    summary: str
    unknowns: list[str]
    conflicts: list[str]
    raw_text: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    response_cost: float | None
    error: str | None = None


@dataclass
class RunBudget:
    max_calls: int
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    known_cost: float = 0.0

    def reserve_call(self) -> None:
        if self.calls >= self.max_calls:
            raise RuntimeError(
                f"chimera call budget exhausted: {self.calls}/{self.max_calls}"
            )

        self.calls += 1

    def account(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        response_cost: float | None,
    ) -> None:
        self.prompt_tokens += max(prompt_tokens, 0)
        self.completion_tokens += max(completion_tokens, 0)

        if response_cost is not None:
            self.known_cost += max(float(response_cost), 0.0)


class ChimeraStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row

        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")

        self._install_schema()

    def _install_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS chimera_runs (
                run_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                authority_effect TEXT NOT NULL,
                problem TEXT NOT NULL,
                created_ns INTEGER NOT NULL,
                completed_ns INTEGER,
                status TEXT NOT NULL,
                models_json TEXT NOT NULL,
                result_json TEXT
            );

            CREATE INDEX IF NOT EXISTS chimera_runs_fingerprint_idx
            ON chimera_runs(fingerprint);

            CREATE TABLE IF NOT EXISTS chimera_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                created_ns INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                segue_type TEXT NOT NULL,
                generation INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES chimera_runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS chimera_events_run_idx
            ON chimera_events(run_id, event_id);

            CREATE TABLE IF NOT EXISTS chimera_claims (
                claim_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                instance_id TEXT NOT NULL,
                model TEXT NOT NULL,
                role TEXT NOT NULL,
                mood TEXT NOT NULL,
                claim_text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                polarity TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                assumptions_json TEXT NOT NULL,
                proposed_tests_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_ns INTEGER NOT NULL,
                FOREIGN KEY(run_id) REFERENCES chimera_runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS chimera_claims_run_idx
            ON chimera_claims(run_id);

            CREATE TABLE IF NOT EXISTS chimera_claim_edges (
                run_id TEXT NOT NULL,
                source_claim_id TEXT NOT NULL,
                target_claim_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL NOT NULL,
                rationale TEXT NOT NULL,
                PRIMARY KEY(
                    run_id,
                    source_claim_id,
                    target_claim_id,
                    edge_type
                ),
                FOREIGN KEY(run_id) REFERENCES chimera_runs(run_id)
            );

            CREATE TABLE IF NOT EXISTS chimera_capability (
                capability_key TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                role TEXT NOT NULL,
                mood TEXT NOT NULL,
                representation TEXT NOT NULL,
                successes REAL NOT NULL,
                failures REAL NOT NULL,
                observations INTEGER NOT NULL,
                updated_ns INTEGER NOT NULL
            );
            """
        )
        self.connection.commit()

    def create_run(
        self,
        run_id: str,
        run_fingerprint: str,
        problem: str,
        models: Sequence[str],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO chimera_runs (
                run_id,
                fingerprint,
                schema_version,
                authority_effect,
                problem,
                created_ns,
                status,
                models_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                run_fingerprint,
                schema_version,
                authority_effect,
                problem,
                now_ns(),
                "running",
                canonical_json(list(models)),
            ),
        )
        self.connection.commit()

    def event(
        self,
        run_id: str,
        event_type: str,
        segue_type: str,
        payload: Any,
        generation: int = 0,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO chimera_events (
                run_id,
                created_ns,
                event_type,
                segue_type,
                generation,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                now_ns(),
                event_type,
                segue_type,
                generation,
                canonical_json(payload),
            ),
        )
        self.connection.commit()

    def save_claim(self, claim: Claim) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO chimera_claims (
                claim_id,
                run_id,
                instance_id,
                model,
                role,
                mood,
                claim_text,
                normalized_text,
                polarity,
                confidence,
                evidence_json,
                assumptions_json,
                proposed_tests_json,
                status,
                created_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.run_id,
                claim.instance_id,
                claim.model,
                claim.role,
                claim.mood,
                claim.text,
                claim.normalized,
                claim.polarity,
                claim.confidence,
                canonical_json(claim.evidence),
                canonical_json(claim.assumptions),
                canonical_json(claim.proposed_tests),
                claim.status,
                now_ns(),
            ),
        )
        self.connection.commit()

    def edge(
        self,
        run_id: str,
        source_claim_id: str,
        target_claim_id: str,
        edge_type: str,
        weight: float,
        rationale: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO chimera_claim_edges (
                run_id,
                source_claim_id,
                target_claim_id,
                edge_type,
                weight,
                rationale
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                source_claim_id,
                target_claim_id,
                edge_type,
                clamp(weight, 0.0, 1.0),
                rationale,
            ),
        )
        self.connection.commit()

    def update_claim_status(self, claim_id: str, status: str) -> None:
        self.connection.execute(
            """
            UPDATE chimera_claims
            SET status = ?
            WHERE claim_id = ?
            """,
            (status, claim_id),
        )
        self.connection.commit()

    def capability_score(self, instance: Instance) -> float:
        key = self._capability_key(instance)

        row = self.connection.execute(
            """
            SELECT successes, failures
            FROM chimera_capability
            WHERE capability_key = ?
            """,
            (key,),
        ).fetchone()

        if row is None:
            return 0.5

        successes = float(row["successes"])
        failures = float(row["failures"])

        return (successes + 1.0) / (successes + failures + 2.0)

    def observe_capability(
        self,
        instance: Instance,
        success_weight: float,
        failure_weight: float,
    ) -> None:
        key = self._capability_key(instance)

        row = self.connection.execute(
            """
            SELECT successes, failures, observations
            FROM chimera_capability
            WHERE capability_key = ?
            """,
            (key,),
        ).fetchone()

        if row is None:
            successes = max(success_weight, 0.0)
            failures = max(failure_weight, 0.0)
            observations = 1
        else:
            successes = float(row["successes"]) + max(success_weight, 0.0)
            failures = float(row["failures"]) + max(failure_weight, 0.0)
            observations = int(row["observations"]) + 1

        self.connection.execute(
            """
            INSERT OR REPLACE INTO chimera_capability (
                capability_key,
                model,
                role,
                mood,
                representation,
                successes,
                failures,
                observations,
                updated_ns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                instance.model,
                instance.role,
                instance.mood,
                instance.representation,
                successes,
                failures,
                observations,
                now_ns(),
            ),
        )
        self.connection.commit()

    def finish_run(self, run_id: str, result: dict[str, Any]) -> None:
        self.connection.execute(
            """
            UPDATE chimera_runs
            SET completed_ns = ?,
                status = ?,
                result_json = ?
            WHERE run_id = ?
            """,
            (
                now_ns(),
                "complete",
                canonical_json(result),
                run_id,
            ),
        )
        self.connection.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        self.connection.execute(
            """
            UPDATE chimera_runs
            SET completed_ns = ?,
                status = ?,
                result_json = ?
            WHERE run_id = ?
            """,
            (
                now_ns(),
                "failed",
                canonical_json({"error": error}),
                run_id,
            ),
        )
        self.connection.commit()

    def replay(self, run_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT *
            FROM chimera_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        if row is None:
            return None

        events = self.connection.execute(
            """
            SELECT *
            FROM chimera_events
            WHERE run_id = ?
            ORDER BY event_id
            """,
            (run_id,),
        ).fetchall()

        claims = self.connection.execute(
            """
            SELECT *
            FROM chimera_claims
            WHERE run_id = ?
            ORDER BY claim_id
            """,
            (run_id,),
        ).fetchall()

        return {
            "run": dict(row),
            "events": [dict(event) for event in events],
            "claims": [dict(claim) for claim in claims],
        }

    def capability_matrix(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM chimera_capability
            ORDER BY observations DESC, model, role, mood
            """
        ).fetchall()

        output = []

        for row in rows:
            item = dict(row)
            successes = float(item["successes"])
            failures = float(item["failures"])
            item["score"] = (successes + 1.0) / (
                successes + failures + 2.0
            )
            output.append(item)

        return output

    @staticmethod
    def _capability_key(instance: Instance) -> str:
        return stable_id(
            "capability",
            {
                "model": instance.model,
                "role": instance.role,
                "mood": instance.mood,
                "representation": instance.representation,
            },
        )


class TraceAdapter:
    def __init__(self) -> None:
        if trace is None:
            self.tracer = None
        else:
            self.tracer = trace.get_tracer("savant.chimera")

    @contextlib.contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None):
        if self.tracer is None:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                if value is None:
                    continue
                try:
                    span.set_attribute(key, value)
                except Exception:
                    pass

            yield span


class Gateway:
    def __init__(
        self,
        budget: RunBudget,
        timeout_seconds: float,
        max_tokens: int,
        temperature: float,
        traces: TraceAdapter,
    ) -> None:
        self.budget = budget
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.traces = traces
        self._budget_lock = asyncio.Lock()

    async def complete(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int, int, float | None]:
        if litellm is None:
            raise RuntimeError(
                "litellm is unavailable; run Chimera through its isolated venv"
            )

        async with self._budget_lock:
            self.budget.reserve_call()

        started = time.monotonic()

        def invoke() -> Any:
            return litellm.completion(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout_seconds,
            )

        with self.traces.span(
            "chimera.model",
            {
                "gen_ai.request.model": model,
                "savant.authority_effect": authority_effect,
            },
        ):
            response = await asyncio.wait_for(
                asyncio.to_thread(invoke),
                timeout=self.timeout_seconds + 5.0,
            )

        latency_ms = int((time.monotonic() - started) * 1000)

        content = response.choices[0].message.content or ""

        usage = getattr(response, "usage", None)

        prompt_tokens = int(
            getattr(usage, "prompt_tokens", 0) or 0
        )
        completion_tokens = int(
            getattr(usage, "completion_tokens", 0) or 0
        )

        response_cost = None

        hidden = getattr(response, "_hidden_params", None)
        if isinstance(hidden, dict):
            raw_cost = hidden.get("response_cost")
            if isinstance(raw_cost, (int, float)):
                response_cost = float(raw_cost)

        async with self._budget_lock:
            self.budget.account(
                prompt_tokens,
                completion_tokens,
                response_cost,
            )

        return (
            content,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            response_cost,
        )


class Chimera:
    def __init__(
        self,
        models: Sequence[str],
        *,
        max_parallel: int,
        max_calls: int,
        timeout_seconds: float,
        max_tokens: int,
        conflict_threshold: float,
        temperature: float,
    ) -> None:
        if not models:
            raise ValueError(
                "no models configured; set SAVANT_CHIMERA_MODELS"
            )

        self.models = list(models)
        self.max_parallel = max(1, max_parallel)
        self.max_calls = max(1, max_calls)
        self.timeout_seconds = max(10.0, timeout_seconds)
        self.max_tokens = max(256, max_tokens)
        self.conflict_threshold = clamp(conflict_threshold, 0.0, 1.0)
        self.temperature = clamp(temperature, 0.0, 1.5)

        self.store = ChimeraStore(database_path)
        self.traces = TraceAdapter()

    def _make_instances(self) -> list[Instance]:
        provisional = []

        for index, role in enumerate(roles):
            model = self.models[index % len(self.models)]

            instance = Instance(
                instance_id=stable_id(
                    "instance",
                    {
                        "model": model,
                        "role": role.name,
                        "mood": role.mood,
                        "representation": role.representation,
                        "generation": 0,
                    },
                ),
                model=model,
                role=role.name,
                mood=role.mood,
                representation=role.representation,
                objective=role.objective,
                generation=0,
            )

            provisional.append(instance)

        return sorted(
            provisional,
            key=lambda instance: (
                -self.store.capability_score(instance),
                instance.role,
                instance.model,
            ),
        )

    @staticmethod
    def _blind_system_prompt(instance: Instance) -> str:
        return f"""
You are a transient cognitive instance inside SAVANT Chimera.

You are not authority.
You may reason, hypothesize, detect conflicts, and propose tests.
You must distinguish evidence from inference and unknown.
Do not claim that another model agreed with you.
You cannot see any other cognitive instance's output.

instance role: {instance.role}
mood transformation: {instance.mood}
problem representation: {instance.representation}
objective: {instance.objective}

Return ONLY one JSON object with this exact top-level shape:

{{
  "summary": "short synthesis",
  "claims": [
    {{
      "claim": "one atomic material claim",
      "polarity": "positive|negative|conditional|unknown",
      "confidence": 0.0,
      "evidence": ["evidence or source reference actually available"],
      "assumptions": ["assumption"],
      "proposed_tests": ["specific discriminating test"]
    }}
  ],
  "unknowns": ["unresolved unknown"],
  "conflicts": ["possible internal tension or competing explanation"]
}}

Rules:
- each claim must be atomic;
- never fabricate evidence;
- confidence is epistemic confidence, not authority;
- unsupported statements belong in assumptions or unknowns;
- preserve meaningful disagreement;
- prefer discriminating tests over rhetorical confidence.
""".strip()

    @staticmethod
    def _blind_user_prompt(problem: str, instance: Instance) -> str:
        return f"""
problem:

{problem}

Transform this problem through the {instance.representation}
representation while operating in the {instance.mood} mood.

Produce an independent analysis now.
""".strip()

    async def _run_instance(
        self,
        run_id: str,
        problem: str,
        instance: Instance,
        gateway: Gateway,
        semaphore: asyncio.Semaphore,
    ) -> ModelResult:
        async with semaphore:
            try:
                (
                    raw,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    response_cost,
                ) = await gateway.complete(
                    instance.model,
                    self._blind_system_prompt(instance),
                    self._blind_user_prompt(problem, instance),
                )

                parsed = extract_json_object(raw)

                claims = []

                for index, item in enumerate(parsed.get("claims", [])):
                    if not isinstance(item, dict):
                        continue

                    text = str(item.get("claim", "")).strip()

                    if not text:
                        continue

                    normalized = normalize_text(text)

                    claim_id = stable_id(
                        "claim",
                        {
                            "run": run_id,
                            "instance": instance.instance_id,
                            "index": index,
                            "claim": normalized,
                        },
                    )

                    evidence = [
                        str(value).strip()
                        for value in item.get("evidence", [])
                        if str(value).strip()
                    ]

                    assumptions = [
                        str(value).strip()
                        for value in item.get("assumptions", [])
                        if str(value).strip()
                    ]

                    proposed_tests = [
                        str(value).strip()
                        for value in item.get("proposed_tests", [])
                        if str(value).strip()
                    ]

                    claim = Claim(
                        claim_id=claim_id,
                        run_id=run_id,
                        instance_id=instance.instance_id,
                        model=instance.model,
                        role=instance.role,
                        mood=instance.mood,
                        text=text,
                        normalized=normalized,
                        polarity=str(
                            item.get("polarity", "conditional")
                        ).strip(),
                        confidence=clamp(
                            float(item.get("confidence", 0.5) or 0.5),
                            0.0,
                            1.0,
                        ),
                        evidence=evidence,
                        assumptions=assumptions,
                        proposed_tests=proposed_tests,
                    )

                    self.store.save_claim(claim)
                    claims.append(claim)

                result = ModelResult(
                    instance=instance,
                    claims=claims,
                    summary=str(parsed.get("summary", "")).strip(),
                    unknowns=[
                        str(value).strip()
                        for value in parsed.get("unknowns", [])
                        if str(value).strip()
                    ],
                    conflicts=[
                        str(value).strip()
                        for value in parsed.get("conflicts", [])
                        if str(value).strip()
                    ],
                    raw_text=raw,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    response_cost=response_cost,
                )

                self.store.event(
                    run_id,
                    "cognition_complete",
                    "instance_to_claim_projection",
                    {
                        "instance": asdict(instance),
                        "claims": [claim.claim_id for claim in claims],
                        "latency_ms": latency_ms,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "known_response_cost": response_cost,
                    },
                    instance.generation,
                )

                return result

            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

                self.store.event(
                    run_id,
                    "cognition_failed",
                    "instance_failure_localization",
                    {
                        "instance": asdict(instance),
                        "error": error,
                    },
                    instance.generation,
                )

                return ModelResult(
                    instance=instance,
                    claims=[],
                    summary="",
                    unknowns=[],
                    conflicts=[],
                    raw_text="",
                    latency_ms=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    response_cost=None,
                    error=error,
                )

    def _derive_claim_edges(
        self,
        run_id: str,
        claims: Sequence[Claim],
    ) -> dict[str, Any]:
        contradictions = 0
        supports = 0
        duplicates = 0
        comparisons = 0

        ordered = sorted(claims, key=lambda claim: claim.claim_id)

        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                if left.instance_id == right.instance_id:
                    continue

                similarity = jaccard(left.text, right.text)

                if similarity < 0.28:
                    continue

                comparisons += 1

                opposing = {
                    left.polarity.casefold(),
                    right.polarity.casefold(),
                } == {"positive", "negative"}

                if similarity >= 0.88 and not opposing:
                    edge_type = "semantic_duplicate"
                    duplicates += 1
                    weight = similarity

                elif opposing:
                    edge_type = "contradicts"
                    contradictions += 1
                    weight = similarity

                elif similarity >= 0.52:
                    edge_type = "supports"
                    supports += 1
                    weight = similarity

                else:
                    continue

                self.store.edge(
                    run_id,
                    left.claim_id,
                    right.claim_id,
                    edge_type,
                    weight,
                    "deterministic lexical projection; not semantic authority",
                )

        denominator = max(
            contradictions + supports + duplicates,
            1,
        )

        return {
            "contradictions": contradictions,
            "supports": supports,
            "duplicates": duplicates,
            "comparisons": comparisons,
            "conflict_ratio": contradictions / denominator,
        }

    @staticmethod
    def _claims_for_prompt(claims: Sequence[Claim]) -> list[dict[str, Any]]:
        return [
            {
                "claim_id": claim.claim_id,
                "instance_id": claim.instance_id,
                "model": claim.model,
                "role": claim.role,
                "mood": claim.mood,
                "claim": claim.text,
                "polarity": claim.polarity,
                "confidence": claim.confidence,
                "evidence": claim.evidence,
                "assumptions": claim.assumptions,
                "proposed_tests": claim.proposed_tests,
            }
            for claim in sorted(claims, key=lambda value: value.claim_id)
        ]

    async def _tribunal(
        self,
        run_id: str,
        problem: str,
        claims: Sequence[Claim],
        gateway: Gateway,
        generation: int,
    ) -> dict[str, Any]:
        model = self.models[generation % len(self.models)]

        system_prompt = """
You are a SAVANT Chimera tribunal instance.

AI output is not authority.
Judge atomic claims against the supplied evidence, assumptions,
constraints, and competing claims.

Do not use majority vote.
Do not reward a claim because multiple models repeated it.
Unknown must remain unknown.
A claim with no adequate evidence may still be a useful hypothesis,
but it cannot be promoted to fact.

Return ONLY JSON:

{
  "verdicts": [
    {
      "claim_id": "claim id",
      "status": "supported|rejected|unresolved",
      "score": 0.0,
      "rationale": "brief reason",
      "required_test": "test needed, or empty string"
    }
  ],
  "cross_claim_conflicts": [
    {
      "left": "claim id",
      "right": "claim id",
      "rationale": "why they conflict",
      "discriminating_test": "minimum useful test"
    }
  ],
  "unknowns": ["unknown"],
  "tribunal_summary": "brief synthesis"
}
""".strip()

        user_prompt = canonical_json(
            {
                "problem": problem,
                "claims": self._claims_for_prompt(claims),
            }
        )

        (
            raw,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            response_cost,
        ) = await gateway.complete(
            model,
            system_prompt,
            user_prompt,
        )

        parsed = extract_json_object(raw)

        verdicts = []

        for verdict in parsed.get("verdicts", []):
            if not isinstance(verdict, dict):
                continue

            claim_id = str(verdict.get("claim_id", "")).strip()
            status = str(verdict.get("status", "unresolved")).strip()

            if status not in {"supported", "rejected", "unresolved"}:
                status = "unresolved"

            score = clamp(
                float(verdict.get("score", 0.5) or 0.5),
                0.0,
                1.0,
            )

            normalized = {
                "claim_id": claim_id,
                "status": status,
                "score": score,
                "rationale": str(
                    verdict.get("rationale", "")
                ).strip(),
                "required_test": str(
                    verdict.get("required_test", "")
                ).strip(),
            }

            verdicts.append(normalized)

            if claim_id:
                self.store.update_claim_status(claim_id, status)

        claim_index = {claim.claim_id: claim for claim in claims}

        for verdict in verdicts:
            claim = claim_index.get(verdict["claim_id"])

            if claim is None:
                continue

            if verdict["status"] == "supported":
                self.store.observe_capability(
                    Instance(
                        instance_id=claim.instance_id,
                        model=claim.model,
                        role=claim.role,
                        mood=claim.mood,
                        representation="observed",
                        objective="",
                    ),
                    success_weight=verdict["score"],
                    failure_weight=0.0,
                )

            elif verdict["status"] == "rejected":
                self.store.observe_capability(
                    Instance(
                        instance_id=claim.instance_id,
                        model=claim.model,
                        role=claim.role,
                        mood=claim.mood,
                        representation="observed",
                        objective="",
                    ),
                    success_weight=0.0,
                    failure_weight=max(verdict["score"], 0.25),
                )

        for conflict in parsed.get("cross_claim_conflicts", []):
            if not isinstance(conflict, dict):
                continue

            left = str(conflict.get("left", "")).strip()
            right = str(conflict.get("right", "")).strip()

            if left not in claim_index or right not in claim_index:
                continue

            self.store.edge(
                run_id,
                left,
                right,
                "tribunal_contradiction",
                1.0,
                str(conflict.get("rationale", "")).strip(),
            )

        tribunal = {
            "model": model,
            "generation": generation,
            "verdicts": verdicts,
            "cross_claim_conflicts": parsed.get(
                "cross_claim_conflicts",
                [],
            ),
            "unknowns": parsed.get("unknowns", []),
            "tribunal_summary": str(
                parsed.get("tribunal_summary", "")
            ).strip(),
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "known_response_cost": response_cost,
        }

        self.store.event(
            run_id,
            "tribunal_complete",
            "claims_to_verdicts",
            tribunal,
            generation,
        )

        return tribunal

    async def _synthesize(
        self,
        run_id: str,
        problem: str,
        claims: Sequence[Claim],
        tribunals: Sequence[dict[str, Any]],
        gateway: Gateway,
    ) -> dict[str, Any]:
        synthesis_model = self.models[-1]

        system_prompt = """
You are the final synthesis instance of SAVANT Chimera.

You receive a problem, atomic claims, and tribunal outputs.

You are not authority.
Do not conceal unresolved conflicts.
Do not convert model agreement into truth.
Prefer surviving evidence-backed claims.
Preserve rejected claims as negative knowledge.
Preserve unresolved claims as unresolved.
Do not fabricate citations or validation.

Return ONLY JSON:

{
  "answer": "best current synthesis",
  "supported_claim_ids": ["claim id"],
  "rejected_claim_ids": ["claim id"],
  "unresolved_claim_ids": ["claim id"],
  "unknowns": ["material unknown"],
  "next_tests": ["minimum discriminating test"],
  "confidence": 0.0,
  "authority_effect": "none"
}
""".strip()

        user_prompt = canonical_json(
            {
                "problem": problem,
                "claims": self._claims_for_prompt(claims),
                "tribunals": list(tribunals),
            }
        )

        (
            raw,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            response_cost,
        ) = await gateway.complete(
            synthesis_model,
            system_prompt,
            user_prompt,
        )

        parsed = extract_json_object(raw)
        parsed["authority_effect"] = "none"
        parsed["model"] = synthesis_model
        parsed["latency_ms"] = latency_ms
        parsed["prompt_tokens"] = prompt_tokens
        parsed["completion_tokens"] = completion_tokens
        parsed["known_response_cost"] = response_cost

        self.store.event(
            run_id,
            "synthesis_complete",
            "verdicts_to_projection",
            parsed,
            len(tribunals) + 1,
        )

        return parsed

    async def run(self, problem: str) -> dict[str, Any]:
        problem = problem.strip()

        if not problem:
            raise ValueError("problem cannot be empty")

        instances = self._make_instances()

        configuration = {
            "schema": schema_version,
            "problem": problem,
            "models": self.models,
            "roles": [asdict(instance) for instance in instances],
            "max_parallel": self.max_parallel,
            "max_calls": self.max_calls,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "conflict_threshold": self.conflict_threshold,
            "temperature": self.temperature,
        }

        run_fingerprint = fingerprint(configuration)
        run_id = f"chimera_{uuid.uuid4().hex}"

        self.store.create_run(
            run_id,
            run_fingerprint,
            problem,
            self.models,
        )

        self.store.event(
            run_id,
            "run_started",
            "problem_to_cognitive_topology",
            {
                "fingerprint": run_fingerprint,
                "instances": [asdict(instance) for instance in instances],
                "authority_effect": authority_effect,
            },
        )

        budget = RunBudget(max_calls=self.max_calls)

        gateway = Gateway(
            budget=budget,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            traces=self.traces,
        )

        semaphore = asyncio.Semaphore(self.max_parallel)

        try:
            with self.traces.span(
                "chimera.run",
                {
                    "savant.chimera.run_id": run_id,
                    "savant.authority_effect": authority_effect,
                },
            ):
                tasks = [
                    self._run_instance(
                        run_id,
                        problem,
                        instance,
                        gateway,
                        semaphore,
                    )
                    for instance in instances
                ]

                blind_results = await asyncio.gather(*tasks)

                successful = [
                    result
                    for result in blind_results
                    if result.error is None and result.claims
                ]

                if not successful:
                    raise RuntimeError(
                        "all blind cognitive instances failed or returned no claims"
                    )

                all_claims = [
                    claim
                    for result in successful
                    for claim in result.claims
                ]

                graph_metrics = self._derive_claim_edges(
                    run_id,
                    all_claims,
                )

                self.store.event(
                    run_id,
                    "claim_graph_projected",
                    "claims_to_conflict_topology",
                    graph_metrics,
                    1,
                )

                tribunals = []

                tribunal_one = await self._tribunal(
                    run_id,
                    problem,
                    all_claims,
                    gateway,
                    generation=1,
                )
                tribunals.append(tribunal_one)

                unresolved_count = sum(
                    1
                    for verdict in tribunal_one.get("verdicts", [])
                    if verdict.get("status") == "unresolved"
                )

                verdict_count = max(
                    len(tribunal_one.get("verdicts", [])),
                    1,
                )

                unresolved_ratio = unresolved_count / verdict_count

                escalation_required = (
                    graph_metrics["conflict_ratio"]
                    >= self.conflict_threshold
                    or unresolved_ratio >= 0.35
                )

                if (
                    escalation_required
                    and budget.calls < budget.max_calls
                    and len(self.models) > 1
                ):
                    self.store.event(
                        run_id,
                        "escalation_triggered",
                        "epistemic_pressure_to_new_generation",
                        {
                            "conflict_ratio": graph_metrics[
                                "conflict_ratio"
                            ],
                            "unresolved_ratio": unresolved_ratio,
                        },
                        2,
                    )

                    tribunal_two = await self._tribunal(
                        run_id,
                        problem,
                        all_claims,
                        gateway,
                        generation=2,
                    )
                    tribunals.append(tribunal_two)

                synthesis = await self._synthesize(
                    run_id,
                    problem,
                    all_claims,
                    tribunals,
                    gateway,
                )

                result = {
                    "schema": schema_version,
                    "run_id": run_id,
                    "fingerprint": run_fingerprint,
                    "authority_effect": authority_effect,
                    "answer": synthesis.get("answer", ""),
                    "confidence": synthesis.get("confidence"),
                    "supported_claim_ids": synthesis.get(
                        "supported_claim_ids",
                        [],
                    ),
                    "rejected_claim_ids": synthesis.get(
                        "rejected_claim_ids",
                        [],
                    ),
                    "unresolved_claim_ids": synthesis.get(
                        "unresolved_claim_ids",
                        [],
                    ),
                    "unknowns": synthesis.get("unknowns", []),
                    "next_tests": synthesis.get("next_tests", []),
                    "graph_metrics": graph_metrics,
                    "blind_instances": [
                        {
                            "instance": asdict(result.instance),
                            "claim_ids": [
                                claim.claim_id
                                for claim in result.claims
                            ],
                            "summary": result.summary,
                            "unknowns": result.unknowns,
                            "error": result.error,
                            "latency_ms": result.latency_ms,
                        }
                        for result in blind_results
                    ],
                    "tribunals": tribunals,
                    "budget": {
                        "calls": budget.calls,
                        "max_calls": budget.max_calls,
                        "prompt_tokens": budget.prompt_tokens,
                        "completion_tokens": budget.completion_tokens,
                        "known_cost": budget.known_cost,
                    },
                }

                self.store.finish_run(run_id, result)

                return result

        except Exception as exc:
            self.store.fail_run(
                run_id,
                f"{type(exc).__name__}: {exc}",
            )
            raise

    def dry_run(self, problem: str) -> dict[str, Any]:
        instances = self._make_instances()

        return {
            "schema": schema_version,
            "authority_effect": authority_effect,
            "problem": problem,
            "models": self.models,
            "instances": [
                {
                    **asdict(instance),
                    "capability_score": self.store.capability_score(
                        instance
                    ),
                }
                for instance in instances
            ],
            "enhancements": [
                "multi-provider normalized gateway",
                "blind independent cognition",
                "transient cognitive instances",
                "role specialization",
                "mood behavior transformations",
                "problem representation mutation",
                "counterfactual worldlines",
                "typed segue event ledger",
                "immutable event history",
                "atomic claim projection",
                "claim provenance",
                "explicit assumptions",
                "explicit unknown preservation",
                "proposed discriminating tests",
                "deterministic claim identifiers",
                "deterministic run fingerprints",
                "claim deduplication projection",
                "support-edge projection",
                "contradiction-edge projection",
                "non-voting tribunal",
                "conflict-driven escalation",
                "negative knowledge persistence",
                "microscopic capability reputation",
                "model-role-mood reputation",
                "Bayesian capability scoring",
                "parallel cognition",
                "bounded concurrency",
                "bounded API call budget",
                "bounded request timeout",
                "token accounting",
                "known-cost accounting",
                "provider failure localization",
                "persistent SQLite substrate",
                "WAL crash resilience",
                "replayable run history",
                "OpenTelemetry-compatible spans",
                "authority-effect isolation",
                "structured final synthesis",
                "unresolved-conflict preservation",
                "deterministic next-test projection",
            ],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chimera",
        description="SAVANT compound intelligence runtime",
    )

    parser.add_argument(
        "--models",
        default="",
        help=(
            "comma-separated LiteLLM model identifiers; "
            "defaults to SAVANT_CHIMERA_MODELS"
        ),
    )

    parser.add_argument(
        "--max-parallel",
        type=int,
        default=int(
            os.environ.get(
                "SAVANT_CHIMERA_MAX_PARALLEL",
                default_parallelism,
            )
        ),
    )

    parser.add_argument(
        "--max-calls",
        type=int,
        default=int(
            os.environ.get(
                "SAVANT_CHIMERA_MAX_CALLS",
                default_max_calls,
            )
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=float(
            os.environ.get(
                "SAVANT_CHIMERA_TIMEOUT",
                default_timeout_seconds,
            )
        ),
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(
            os.environ.get(
                "SAVANT_CHIMERA_MAX_TOKENS",
                default_max_tokens,
            )
        ),
    )

    parser.add_argument(
        "--conflict-threshold",
        type=float,
        default=float(
            os.environ.get(
                "SAVANT_CHIMERA_CONFLICT_THRESHOLD",
                default_conflict_threshold,
            )
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=float(
            os.environ.get(
                "SAVANT_CHIMERA_TEMPERATURE",
                default_temperature,
            )
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("problem")

    dry_parser = subparsers.add_parser("dry-run")
    dry_parser.add_argument("problem")

    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("run_id")

    subparsers.add_parser("capabilities")

    return parser


def selected_models(raw: str) -> list[str]:
    if raw.strip():
        return [
            value.strip()
            for value in raw.split(",")
            if value.strip()
        ]

    return read_models()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    models = selected_models(args.models)

    if args.command in {"run", "dry-run"} and not models:
        print(
            "no models configured; set SAVANT_CHIMERA_MODELS "
            "or pass --models",
            file=sys.stderr,
        )
        return 2

    if args.command == "replay":
        store = ChimeraStore(database_path)
        result = store.replay(args.run_id)

        if result is None:
            print(f"unknown run: {args.run_id}", file=sys.stderr)
            return 1

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.command == "capabilities":
        store = ChimeraStore(database_path)
        print(
            json.dumps(
                store.capability_matrix(),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    chimera = Chimera(
        models=models,
        max_parallel=args.max_parallel,
        max_calls=args.max_calls,
        timeout_seconds=args.timeout,
        max_tokens=args.max_tokens,
        conflict_threshold=args.conflict_threshold,
        temperature=args.temperature,
    )

    if args.command == "dry-run":
        print(
            json.dumps(
                chimera.dry_run(args.problem),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "run":
        result = asyncio.run(chimera.run(args.problem))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
