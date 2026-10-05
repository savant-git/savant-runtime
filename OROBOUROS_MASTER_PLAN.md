# OROBOUROS MASTER PLAN

Status: ACCEPTED IMPLEMENTATION PLAN
Authority: USER DIRECTIVE
Date: 2026-08-11
Canonical contract: `/root/savant-runtime/OROBOUROS_LIVING_PERSONA_CANON.md`

## Objective

Implement Orobouros as the permanent default Palaver persona without replacing the accepted responsibilities of Opus, Envoy, or Palaver.

Authority split:

- Opus: AI APIs, credentials, providers, models, execution.
- Envoy: personas, voices, trait evaluation, Orobouros composition.
- Palaver: conversation.

The current source already establishes Opus API orchestration, Envoy persona/voice ownership, and Palaver conversation ownership. The implementation must extend those primitives rather than duplicate them.

---

# Phase 1 — Opus Provider Foundation

Extend the existing Opus provider architecture.

Required:

- centralized `.env`/environment credential loading;
- provider registry;
- model registry;
- provider health;
- capability metadata;
- normalized execution request/response;
- provider/model lineage;
- retry/fallback;
- rate-limit handling;
- timeout policy;
- cost/latency metadata where available.

Credentials remain exclusively Opus-owned.

Completion:

Envoy and Palaver require no provider credentials and make no direct external AI API calls.

---

# Phase 2 — AI Trait Representation

Create one structured Envoy-owned trait contract.

Required fields:

- trait ID;
- semantic capability;
- version;
- status;
- provenance;
- provider/model evidence;
- domains;
- strengths;
- weaknesses;
- confidence;
- compatibility;
- conflicts;
- dependencies;
- evaluation references.

Traits must remain provider-neutral.

Completion:

At least two different model/provider candidates can be represented as candidates for the same semantic trait without duplicating the trait definition.

---

# Phase 3 — Evaluation

Implement bounded evaluation sufficient to compare trait candidates.

Required:

- structured evaluation records;
- deterministic scoring inputs;
- confidence;
- failure recording;
- candidate lifecycle;
- champion/challenger comparison;
- immutable accepted evidence.

Do not attempt exhaustive universal AI benchmarking.

Completion:

One representative trait can be evaluated across multiple model candidates and an accepted champion can be selected with inspectable evidence.

---

# Phase 4 — Orobouros Baseline

Define the first accepted Orobouros baseline.

Requirements:

- stable persona ID;
- explicit baseline version;
- required traits;
- voice identity reference;
- expression policy;
- immutable accepted baseline record.

Do not infer the baseline merely from provider popularity.

Completion:

Orobouros remains a complete valid persona with no adaptive Crown traits active.

---

# Phase 5 — Living Trait Crown

Implement the adaptive bounded trait layer.

Required:

- one authoritative cap;
- task/scenario requirements;
- deterministic candidate ranking;
- compatibility validation;
- smallest-sufficient selection;
- hysteresis;
- context stickiness;
- graceful expiration;
- composition digest;
- composition receipt.

Completion:

Two materially different scenarios produce appropriate bounded Crown compositions while retaining the same baseline Orobouros identity.

---

# Phase 6 — Runtime Projection

Envoy compiles:

Orobouros baseline
+ Crown
+ persona policy
+ voice identity
+ relevant runtime context

into the active persona projection.

The projection must remain derived state.

Completion:

Palaver can request the active Orobouros projection without knowing provider-specific implementation.

---

# Phase 7 — Voice

Preserve the accepted voice boundary:

Palaver
→ Envoy
→ Opus
→ TTS provider
→ Envoy
→ Palaver.

Required:

- Orobouros voice profile belongs to Envoy;
- provider-neutral speech intent;
- Opus provider execution;
- provider lineage;
- no credentials in Envoy.

Completion:

Changing the TTS provider does not change Orobouros persona identity.

---

# Phase 8 — Palaver Default

Make Orobouros the canonical default Palaver persona.

Palaver should retain conversation ownership.

Palaver should not absorb:

- trait evaluation;
- provider routing;
- credentials;
- voice definitions.

Completion:

Ordinary Palaver conversation uses Orobouros through Envoy.

---

# Phase 9 — Reliability Enhancements

Implement only where required by observed runtime needs:

1. provider circuit breakers;
2. exponential backoff;
3. rate-limit-aware routing;
4. deterministic provider normalization;
5. structured output validation;
6. semantic trait compatibility graph;
7. trait conflict detection;
8. trait dependency validation;
9. champion/challenger evaluation;
10. confidence-weighted scoring;
11. Pareto-aware candidate comparison;
12. selection hysteresis;
13. context stickiness;
14. composition digests;
15. composition receipts;
16. shadow composition;
17. regression protection;
18. graceful degradation;
19. provider-independent baseline survival;
20. capability-gap detection;
21. immutable evaluation history;
22. model-version provenance;
23. semantic caching;
24. data-minimized provider requests;
25. runtime composition explanation;
26. trait quarantine;
27. scenario profiles;
28. atomic Crown recomposition;
29. last-valid-composition recovery;
30. replayable selection decisions.

These are implementation targets, not authorization to create thirty separate frameworks or files.

Reuse existing Savant primitives first.

---

# Phase 10 — Optional Technical Dependencies

Evaluate before adding.

Potentially useful:

- Pydantic or JSON Schema — structured contracts;
- NetworkX — only if existing graph tooling cannot efficiently perform required compatibility analysis;
- SciPy — only if actual ranking/evaluation math requires it;
- OR-Tools or Z3 — only if deterministic bounded selection becomes too complex for the simple selector;
- provider SDKs — only where they materially outperform the existing HTTP/provider adapters.

Do not install a dependency merely because it appears on this list.

No public repository becomes Savant authority.

Vendoring third-party snippets without a material need is prohibited.

---

# Deferred Phase — Additional Personas

Do not implement during initial Orobouros work.

Future Envoy personas may provide:

- alternative voices;
- alternative expression;
- alternative conversational stance;
- specialized domain behavior;
- user-selectable Palaver identities.

They must reuse the same underlying Opus and Envoy infrastructure.

Orobouros remains the canonical default unless later authority supersedes that decision.

---

# Finite Completion Point

This task is complete when Phases 1–8 pass the minimum validation defined by the canon.

Do not continue automatically into:

- persona marketplaces;
- persona authoring UIs;
- exhaustive provider benchmarking;
- autonomous personality evolution;
- additional documentation;
- speculative frameworks;
- unrelated Savant redesign.

Once Orobouros is the stable default Palaver persona with the accepted living bounded trait system, stop and move to the next task.
