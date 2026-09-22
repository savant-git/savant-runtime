# OROBOUROS LIVING PERSONA CANON

Status: CANONICAL TARGET
Authority: USER DIRECTIVE
Date: 2026-08-11

## 1. Purpose

Orobouros is Savant's canonical synthesized AI persona.

Orobouros is not a new external AI provider and does not replace the underlying models.

It is a living Savant persona assembled by Envoy from reusable, independently evaluated AI trait layers supplied through Opus.

Orobouros is the default personality and voice identity presented through Palaver.

The permanent identity remains stable while a bounded adaptive layer set changes according to the active situation.

---

## 2. Authority Boundaries

### Opus

Opus owns external AI API orchestration.

Opus owns:

- provider registration;
- API credentials;
- environment loading;
- `.env` integration;
- authentication;
- provider availability;
- model discovery;
- model capability metadata;
- API execution;
- retries;
- fallback;
- timeout policy;
- rate-limit handling;
- provider health;
- cost metadata;
- latency metadata;
- model/version lineage;
- normalized provider responses.

Opus does not own Orobouros's personality.

Opus does not own persona selection.

Opus does not own voice identity.

### Envoy

Envoy owns:

- personas;
- personality composition;
- AI trait evaluation;
- AI trait selection;
- Orobouros;
- voice identity;
- voice characteristics;
- persona-specific expression;
- adaptive persona state;
- persona registries;
- future user-selectable Palaver personas.

Envoy consumes provider/model capability through Opus rather than directly implementing provider APIs.

### Palaver

Palaver owns:

- conversation;
- dialogue lifecycle;
- user interaction;
- conversational context;
- presentation of the active persona.

Palaver does not own provider execution.

Palaver does not define Orobouros internally.

Palaver requests the active persona from Envoy.

Canonical runtime relationship:

Palaver
→ Envoy
→ Orobouros persona composition
→ Opus where external AI execution is required
→ Envoy
→ Palaver.

For voice:

Palaver
→ Envoy persona/voice intent
→ Opus provider execution
→ Envoy persona metadata
→ Palaver.

---

## 3. AI Layer Model

Each external AI/model exposed by Opus may be analyzed into multiple semantic layers.

A layer represents one coherent reusable trait or capability.

Examples include:

- analytical rigor;
- instruction fidelity;
- planning;
- concise synthesis;
- long-context synthesis;
- coding precision;
- mathematical reasoning;
- literary expression;
- dialogue naturalness;
- uncertainty calibration;
- tool-selection judgment;
- research synthesis;
- divergent ideation;
- structural criticism;
- pedagogical explanation;
- adversarial review;
- summarization;
- multilingual fluency;
- temporal reasoning;
- causal reasoning;
- spatial reasoning;
- retrieval synthesis;
- self-correction behavior;
- creative variation.

A layer MUST describe behavior or capability rather than provider identity.

Bad:

`claude_layer`

Good:

`long_context_synthesis`

Provider/model provenance remains attached separately.

---

## 4. Atomic Trait Rule

One layer should encode one coherent trait.

Do not create monolithic provider-personality blobs.

A layer must expose sufficient metadata to distinguish:

- what capability it represents;
- where its evidence came from;
- which provider/model produced the evidence;
- applicable task domains;
- measured strengths;
- measured weaknesses;
- conflicts;
- dependencies;
- confidence;
- version;
- lineage.

---

## 5. Provider Neutrality

Orobouros must not depend permanently on any single commercial model.

Provider identity and trait identity are separate.

Multiple providers may supply candidates for the same trait.

Envoy chooses traits according to evidence and policy.

Provider disappearance should degrade available candidates rather than destroy Orobouros's identity.

---

## 6. Trait Evidence

A provider's reputation is not sufficient evidence for trait admission.

Trait evaluation should eventually use representative evaluations appropriate to the trait.

Evidence may include:

- deterministic benchmark results;
- structured comparison tasks;
- pairwise evaluations;
- human-approved evaluations;
- historical runtime performance;
- failure rate;
- latency;
- cost;
- context limits;
- tool reliability;
- uncertainty behavior.

AI-generated evaluation is evidence, not authority.

---

## 7. Baseline Orobouros

Orobouros contains a permanent baseline.

The baseline defines the minimum stable AI being.

Baseline traits must cover the capabilities necessary for Orobouros to remain coherent across ordinary interactions.

The baseline is versioned and immutable once accepted.

A new baseline supersedes an old baseline rather than silently editing it.

Baseline identity must remain independent of temporary adaptive traits.

---

## 8. Living Trait Crown

Above the baseline is a bounded adaptive set of additional traits.

This adaptive set may change according to:

- task;
- conversation state;
- domain;
- complexity;
- required tools;
- desired expression;
- latency constraints;
- reliability requirements;
- available providers;
- user-selected persona policy.

This is the Living Trait Crown.

The Crown is temporary composition.

Orobouros remains Orobouros when Crown membership changes.

---

## 9. Trait Cap

Adaptive trait composition MUST have an explicit maximum.

The cap must be configurable through one authoritative policy.

No implementation may silently exceed it.

The initial numerical cap should be selected during implementation from measured context/runtime cost rather than invented in canon.

The baseline is not discarded to make room for adaptive traits.

---

## 10. Selection Objective

Envoy should select the smallest sufficient trait set for the current situation.

Selection should optimize, in priority order:

1. required capability coverage;
2. correctness;
3. reliability;
4. compatibility;
5. contextual suitability;
6. authority compliance;
7. uncertainty calibration;
8. latency;
9. cost;
10. stylistic suitability.

More traits are not inherently better.

---

## 11. Trait Compatibility

Traits may declare relationships including:

- compatible_with;
- conflicts_with;
- requires;
- complements;
- substitutes_for;
- supersedes;
- derived_from.

Envoy must reject incompatible Crown compositions.

---

## 12. Trait Diversity

Where two candidates are effectively equivalent, selection may consider diversity of reasoning behavior.

Diversity must not override correctness or reliability.

The objective is useful complementary behavior, not arbitrary provider variety.

---

## 13. Dynamic Recomposition

The Living Trait Crown may change between tasks or conversational phases.

Recomposition must be:

- deterministic where inputs and evidence are identical;
- bounded;
- reversible;
- attributable;
- observable;
- non-destructive.

A failed candidate composition leaves the last valid composition intact.

---

## 14. Composition Receipt

Each materially different Orobouros composition should be capable of producing a receipt containing:

- Orobouros baseline version;
- active Crown traits;
- trait versions;
- provider/model provenance;
- selection reasons;
- evaluation references;
- compatibility result;
- composition digest;
- timestamp;
- relevant policy version.

Receipts are evidence, not new authority.

---

## 15. Semantic Composition Digest

Envoy should derive a deterministic digest from semantic composition state.

The digest should include:

- baseline version;
- active trait identities;
- trait versions;
- significant configuration;
- compatibility policy version.

Volatile telemetry must not change semantic identity.

---

## 16. Trait Registry

Envoy should maintain the authoritative trait registry.

Opus supplies provider/model evidence and execution.

Envoy owns the interpretation of that evidence into persona traits.

Canonical conceptual flow:

External AI APIs
→ Opus
→ normalized model capabilities/results
→ Envoy evaluation
→ trait candidates
→ accepted trait registry
→ Orobouros baseline + Living Trait Crown.

---

## 17. Trait Lifecycle

Trait candidates should support lifecycle states such as:

- candidate;
- evaluated;
- accepted;
- active;
- deprecated;
- superseded;
- quarantined.

Rejected or superseded traits should remain recoverable as history where materially useful.

---

## 18. Champion / Challenger

Multiple candidates may compete for the same semantic trait.

Envoy may maintain:

- one champion;
- one or more challengers.

A challenger replaces a champion only when sufficient evidence supports the change.

Provider novelty alone is insufficient.

---

## 19. Continuous Evaluation

New models and model versions may be evaluated as they become available.

Continuous evaluation must not imply uncontrolled personality mutation.

Evaluation:

provider/model
→ candidate evidence
→ candidate traits
→ comparison
→ accepted registry update.

Runtime selection then chooses among accepted traits.

---

## 20. Baseline Stability

The permanent baseline is deliberately harder to change than the Crown.

Runtime conditions cannot silently rewrite it.

Baseline evolution requires an explicit accepted supersession.

This preserves Orobouros identity continuity.

---

## 21. Persona Identity

Orobouros is a persona owned by Envoy.

Its identity includes:

- stable persona ID;
- accepted baseline;
- voice identity;
- expression policy;
- adaptive Crown policy;
- lineage.

Its identity does not equal any individual external AI model.

---

## 22. Orobouros Voice

Envoy owns Orobouros's voice identity and speech intent.

Opus owns external speech-provider execution.

Therefore:

Orobouros
→ Envoy voice profile
→ provider-neutral speech request
→ Opus
→ selected speech API
→ audio
→ Envoy
→ Palaver.

A TTS provider is not Orobouros.

Changing TTS providers must not change Orobouros identity.

---

## 23. Future Palaver Personas

Orobouros is the canonical default persona.

The architecture must permit future additional Envoy personas.

A user may eventually select another persona for Palaver.

A persona may alter:

- expression;
- voice;
- cadence;
- vocabulary;
- conversational stance;
- permitted adaptive trait policy;
- stylistic preferences.

It must not silently alter Savant authority or safety boundaries.

---

## 24. Persona Switching

Future persona switching should occur through Envoy.

Palaver requests or reports the desired persona.

Envoy resolves the persona.

Opus remains provider orchestration infrastructure regardless of persona.

---

## 25. Contextual Trait Routing

Envoy may infer required traits from the active task.

Examples:

code task
→ coding precision + debugging + dependency reasoning.

literary task
→ literary expression + structural criticism + stylistic variation.

research task
→ retrieval synthesis + source discrimination + uncertainty calibration.

planning task
→ decomposition + constraint reasoning + prioritization.

The examples are illustrative rather than fixed compositions.

---

## 26. Trait Hysteresis

Envoy should avoid unnecessary Crown churn.

A currently active trait should not be replaced by a marginally better candidate unless the expected benefit exceeds a defined switching threshold.

This preserves behavioral continuity.

---

## 27. Context Stickiness

Traits may remain active across closely related conversational turns when still appropriate.

They should expire when their relevance disappears.

This prevents constant needless recomposition.

---

## 28. Confidence Calibration

Trait selection should account for confidence in the evidence supporting each candidate.

Weak evidence should not outrank strong evidence merely because the nominal score is higher.

---

## 29. Uncertainty Preservation

Orobouros must not combine several uncertain model outputs into false certainty.

Uncertainty should remain representable through normalization, evaluation, and synthesis.

---

## 30. Failure Containment

Failure of an optional adaptive trait must not destroy the baseline persona.

On failure:

1. isolate the failed trait;
2. preserve baseline;
3. use an accepted compatible substitute if available;
4. otherwise continue in explicit degraded mode.

---

## 31. Provider Availability

Provider availability belongs to Opus.

Envoy consumes availability information but does not read provider credentials directly.

No Envoy implementation should parse `.env` merely to determine API availability.

---

## 32. Credentials

All external AI/API credentials are an Opus concern.

Canonical flow:

`.env / environment / credential source`
→ Opus credential loader
→ provider registry
→ provider availability
→ API execution.

Credentials must not be copied into:

- Envoy persona definitions;
- Orobouros trait definitions;
- Palaver configuration;
- logs;
- composition receipts.

---

## 33. Model Normalization

Opus should normalize materially useful model/provider metadata before Envoy consumes it.

Normalization may include:

- provider;
- model;
- modality;
- context capability;
- tool capability;
- structured-output capability;
- latency evidence;
- cost evidence;
- availability;
- model version;
- response lineage.

Provider-specific schemas should not leak unnecessarily into Envoy.

---

## 34. Structured Evaluation

Trait evaluation should use structured records rather than prose-only judgments.

This permits:

- deterministic comparison;
- replay;
- auditing;
- challenger evaluation;
- longitudinal improvement.

---

## 35. Multi-Objective Selection

Trait selection is a bounded multi-objective optimization problem.

Envoy may use weighted scoring or Pareto-style comparison where useful.

A heavy optimizer is not required initially.

The simplest deterministic method sufficient for the actual trait pool should be used first.

---

## 36. Optional Technical Leverage

Potential implementation techniques include:

- JSON Schema or Pydantic for contracts;
- semantic versioning;
- content hashes for immutable evaluation artifacts;
- Elo/Bradley-Terry style pairwise ranking;
- Pareto-front selection;
- contextual bandit techniques for evidence-driven adaptive selection;
- embedding-assisted semantic trait matching;
- graph algorithms for dependency/conflict analysis;
- structured provider adapters;
- deterministic caching;
- circuit breakers;
- exponential backoff;
- rate-limit aware routing.

These techniques are implementation options.

None supersede Savant authority.

Dependencies should be admitted only when they materially improve the implementation.

---

## 37. No Prompt-Frankenstein

Orobouros must not be implemented merely by concatenating giant provider personality prompts.

Trait composition should operate on structured semantic trait definitions.

The final runtime persona projection may generate prompt material, but the prompt is a deterministic projection of accepted composition.

It is not canonical trait storage.

---

## 38. No Provider Impersonation

Orobouros is not to claim that it literally is another provider's model.

Traits may be derived from evaluated capabilities.

Provider/model provenance remains explicit internally.

The resulting persona is Orobouros.

---

## 39. Evaluation Isolation

Evaluation runs must not mutate the accepted trait registry directly.

Flow:

candidate
→ sandbox evaluation
→ evidence
→ acceptance decision
→ registry.

This prevents experimental models from silently changing the active persona.

---

## 40. Shadow Composition

Candidate Crown compositions may be evaluated in shadow mode without replacing the active composition.

Promotion occurs only after sufficient evidence.

---

## 41. Regression Protection

A new trait candidate must not be promoted solely because it improves one metric while materially degrading required behavior elsewhere.

Required baseline behavior remains protected.

---

## 42. Scenario Profiles

Envoy may maintain reusable scenario profiles describing capability requirements.

Examples:

- coding;
- research;
- literary;
- conversational;
- planning;
- analysis;
- summarization;
- tool execution.

Profiles describe requirements.

They should not duplicate trait implementations.

---

## 43. User Preference

Future persona/user preferences may influence selection within legitimate bounds.

Preference does not override:

- authority;
- compatibility;
- required capability;
- safety;
- provider availability.

---

## 44. Observability

The system should be able to explain, when requested:

- which persona is active;
- which baseline version is active;
- which Crown traits are active;
- why those traits were selected;
- which provider/model evidence supports them;
- whether the persona is degraded.

Secrets must never be exposed.

---

## 45. Replay

Given the same accepted registry, baseline, task classification, policy, and availability snapshot, Envoy should be able to reconstruct the same intended composition.

External model responses themselves may remain nondeterministic.

Composition decisions should be reproducible.

---

## 46. Caching

Safe reusable evaluation and routing results may be cached.

Cache identity must include enough provider/model/version/policy information to prevent stale evidence from masquerading as current evidence.

---

## 47. Circuit Breaking

Repeated provider failures should cause Opus to temporarily suppress that provider according to policy.

Envoy then selects only from currently usable execution paths.

Provider failure must not be interpreted as a change to Orobouros identity.

---

## 48. Cost Awareness

Opus supplies cost evidence.

Envoy may consider cost when multiple candidates satisfy required quality.

Cost must not silently displace a required capability.

---

## 49. Latency Awareness

Opus supplies latency evidence.

Envoy may choose lower-latency compatible traits for latency-sensitive interactions.

High-latency traits may remain available for tasks where their measured benefit justifies them.

---

## 50. Capability Gaps

If no accepted trait composition satisfies the task, Envoy must expose a capability gap rather than fabricate capability.

A gap may trigger later evaluation of new providers/models.

---

## 51. Security

Provider responses are untrusted external input.

Provider/model output must not automatically become Savant authority.

External content must not grant itself:

- filesystem authority;
- credential access;
- mutation rights;
- canon status;
- persona-registry mutation.

---

## 52. Data Minimization

Opus should send providers only the information required for the request.

Persona composition must not become justification for sending unrelated Savant state to external APIs.

---

## 53. Provenance

Every accepted trait should retain provenance sufficient to identify:

- provider;
- model;
- model/version identifier where available;
- evaluation;
- evaluator/policy;
- acceptance state;
- supersession lineage.

---

## 54. Immutability

Accepted historical evaluations and baseline versions should be immutable.

Corrections create superseding records.

This preserves replay and auditability.

---

## 55. Personality Projection

Envoy compiles:

baseline
+ Living Trait Crown
+ active persona policy
+ voice identity
+ relevant user/context policy

into a runtime persona projection.

Palaver consumes that projection.

The compiled projection is derived state.

---

## 56. Minimum Initial Implementation

The first implementation milestone contains only:

1. Opus credential/provider normalization;
2. AI model capability registry;
3. Envoy trait schema;
4. Envoy trait registry;
5. Orobouros baseline schema;
6. bounded Living Trait Crown;
7. deterministic trait selector;
8. compatibility/conflict validation;
9. composition digest;
10. runtime persona projection;
11. Palaver default-persona integration;
12. Orobouros voice integration through Envoy → Opus.

Do not build the future persona marketplace in milestone one.

---

## 57. Minimum Validation

Milestone one requires:

1. schema/syntax validation;
2. one focused trait-selection test;
3. one Palaver → Envoy → Opus integration check.

Then stop.

---

## 58. Completion Condition

The initial Orobouros implementation is complete when:

- Opus alone owns API credentials and provider execution;
- provider/model information reaches Envoy through a normalized contract;
- Envoy can evaluate/store structured traits;
- an immutable accepted Orobouros baseline exists;
- the adaptive Crown respects its configured cap;
- trait conflicts are rejected;
- identical selection inputs produce identical composition;
- Orobouros projects a complete runtime persona;
- Palaver uses Orobouros as its default persona;
- Orobouros voice intent belongs to Envoy;
- speech-provider execution belongs to Opus;
- baseline survives optional trait/provider failure;
- composition lineage is inspectable.

At that point, stop.

Future persona expansion is a separate task.

---

## 59. Canonical Invariants

1. Opus orchestrates AI APIs.
2. Opus owns API credentials and environment loading.
3. Envoy owns personas.
4. Envoy owns voices.
5. Envoy owns AI trait evaluation and composition.
6. Palaver owns conversation.
7. Orobouros is Envoy's canonical default Palaver persona.
8. Orobouros is not an external model.
9. External models contribute candidate traits.
10. Traits are semantic and provider-neutral.
11. The Orobouros baseline is stable and versioned.
12. Adaptive traits form a bounded Living Trait Crown.
13. Crown membership may change with context.
14. Crown mutation does not alter Orobouros identity.
15. Provider failure does not erase Orobouros.
16. TTS providers do not own voice identity.
17. AI outputs are evidence, not authority.
18. Credentials never belong in persona state.
19. Historical compositions remain attributable.
20. Additional Palaver personas remain future extensions rather than milestone-one requirements.

---

## 60. Final Architecture

External AI providers
→ Opus credential/provider/API orchestration
→ normalized model evidence
→ Envoy trait evaluation
→ accepted trait registry
→ permanent Orobouros baseline
+ bounded Living Trait Crown
→ Envoy runtime persona + voice intent
→ Palaver conversation.

Orobouros remains one coherent Savant being.

Its foundation persists.

Its situational strengths evolve.
