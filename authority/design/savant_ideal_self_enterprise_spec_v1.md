# savant ideal self

## enterprise concept and execution specification

**status:** design specification and verified implementation record\
**owner:** `exile:envoy` for personality identity and projection; `opus`
for cognitive execution\
**authority effect:** none\
**version:** 1.0.0\
**date:** 2026-09-24

## 1. definition

Savant Ideal Self is a personal-intelligence architecture that learns a
person at high behavioral resolution, preserves the person's accepted
identity, and combines that identity with user-accepted aspirations and
dynamically composed cognitive augmentation.

It is not merely a chatbot persona, style preset, psychological profile,
system prompt, vector database, or digital clone.

Its target is an evolving executable model of the user's identity,
values, ethics, preferences, temperament, humor, sarcasm, irony,
conversational rhythm, vocabulary, emotional expression, decision
patterns, cognitive habits, contradictions, contextual exceptions,
relationships, boundaries, aspirations, accepted weaknesses, and
idiosyncrasies.

The governing distinction is:

> **Knowing the user extremely well does not create permission to act
> for the user.**

The system keeps separate:

1.  what evidence exists;
2.  what Savant infers;
3.  what the user accepts;
4.  what the user aspires to;
5.  what Savant is authorized to do.

## 2. origin

The concept emerged from the Savant Personal Representative: a deeply
personalized AI that learns continuously through use, conducts deep
conversations to understand the user, discovers personality regions it
does not yet understand, and can eventually project specialized digital
representatives.

The decisive evolution was separating a faithful representation from an
ideal representation.

A faithful representative asks:

> **What would I probably do?**

Ideal Self asks:

> **What would the best version of me, as I define that version, do with
> better information, stronger reasoning, reliable memory, more
> deliberation, and the right cognitive resources?**

## 3. four selves

### observed self

Evidence-supported characteristics currently observed or inferred. It
may contain uncertainty, contradiction, contextual behavior, unaccepted
hypotheses, and undesirable patterns.

### accepted self

Personality substance the user recognizes as part of themselves.
Acceptance does not imply approval.

### aspirational self

User-accepted directions of growth.

### ideal self

A deterministic projection composed from accepted identity, accepted
aspirations, accepted correction targets, context, identity-preservation
constraints, cognitive augmentation requirements, evidence, uncertainty,
and Opus orchestration.

Ideal Self is a projection, not competing personality authority.

## 4. idealization law

Savant may discover discrepancies, surface evidence, identify conflicts
with stated goals, and challenge the user when permitted.

It may not silently decide what a better human being is.

A characteristic may be compensated for in Ideal Self only when the user
accepts the relevant aspiration or correction target.

`observed behavior → accepted discrepancy → accepted aspiration → cognitive compensation`

This prevents AI preference from becoming human identity authority.

## 5. truth and candor

The original feature includes a control ranging from comfortable
mirroring to hard truth.

Production architecture separates truth from disclosure.

> **Candor changes how Savant communicates evidence. It never changes
> the evidence itself.**

Low candor may reduce confrontation, defer unsolicited criticism, or
soften delivery. It may not erase evidence, manufacture agreement,
increase confidence for reassurance, rewrite accepted traits, or pretend
an observed problem does not exist.

Invariant:

`presentation preference ≠ truth mutation`

The verified implementation currently projects five candor modes:

1.  `mirror`
2.  `gentle`
3.  `candid`
4.  `challenge`
5.  `unfiltered`

These are positions on a continuous control surface, not separate
personalities.

## 6. candor controls

The verified Ideal Self composition supports separable controls for:

-   candor;
-   challenge;
-   unsolicited truth;
-   delivery softening;
-   humor preservation;
-   sarcasm preservation;
-   evidence explanation.

The mature interface should additionally expose contradiction
visibility, uncertainty visibility, and correction pressure as
projections over canonical state.

Maximum candor means maximum permitted directness, not cruelty,
unsupported certainty, diagnosis, or abuse.

## 7. why truth is necessary

Idealization cannot work if Savant is required to pretend the user has
no weaknesses.

If evidence suggests the user reacts too quickly when angry, the user
recognizes that pattern, and the user wants to retain directness while
gaining restraint, Savant has a legitimate transformation target.

If Savant alone believes a characteristic is defective, it may retain
and discuss that hypothesis according to candor settings, but it may not
silently remove the characteristic from Ideal Self.

## 8. personality datrix

The specialized Personality Datrix is the structured substrate beneath
Ideal Self.

Verified implementation:

`personality_datrix.py`

Schema:

`savant.envoy.personality-datrix.v1`

Owner:

`exile:envoy`

Authority effect:

`none`

Architecture:

`evidence → trait instances → typed segues → contextual composition → projections`

The supplied focused verification established deterministic projection,
truth preservation, acceptance-gated idealization, 110 represented
personality facets, and 13 contextual dimensions.

The module is a specialized Envoy runtime foundation. It is not evidence
that full integration with canonical Datrix Dyad, Membrane, Umbra, and
Isotope primitives is complete.

## 9. evidence model

Current evidence kinds include:

-   explicit statement;
-   conversation;
-   decision;
-   correction;
-   behavior;
-   scenario response;
-   preference;
-   artifact;
-   outcome;
-   reflection;
-   contradiction.

Evidence preserves identity, kind, content, confidence, source
reference, and context.

The system must distinguish explicit statement, observation, inference,
accepted trait, contradiction, aspiration, and correction.

Repeated inference is not automatically acceptance.

## 10. contextual personality

Human personality is not a collection of global constants.

The verified Datrix includes contextual dimensions covering
relationship, role, audience, medium, domain, location, privacy, stakes,
urgency, emotional state, resource state, social state, and historical
context.

Conceptually:

`persona × relationship × role × medium × domain × stakes × state → contextual expression`

The same person can be blunt with friends, diplomatic professionally,
playful privately, and restrained in a high-stakes public setting
without being inconsistent.

## 11. personality coverage

The current Datrix represents 110 facets spanning:

-   values, ethics, beliefs, identity, aspirations, goals, motivations,
    priorities;
-   temperament and emotional expression;
-   empathy, compassion, patience, anger, fear, confidence, humility,
    vulnerability;
-   trust, loyalty, forgiveness, resentment, attachment, privacy,
    boundaries;
-   directness, formality, politeness, assertiveness, conflict,
    negotiation, persuasion;
-   storytelling, verbosity, vocabulary, syntax, rhythm, profanity;
-   humor, sarcasm, irony, deadpan, absurdity, understatement,
    exaggeration, wordplay, gallows humor, self-deprecation, teasing,
    humor boundaries;
-   curiosity, skepticism, creativity, imagination, intuition, analysis,
    deliberation;
-   impulsivity, risk, uncertainty, attention, learning, memory
    preferences;
-   decision style, problem solving, planning, adaptability, novelty,
    routine;
-   aesthetics, taste, consumer behavior, financial behavior, work
    behavior;
-   leadership, collaboration, relationship, family, friendship,
    professional, public, private, and online behavior;
-   moral reasoning, fairness, authority, rules, tradition,
    independence;
-   competitiveness, status, recognition, ambition, discipline,
    persistence;
-   perfectionism, self-awareness, defensiveness, rationalization, bias,
    regret, growth, and idiosyncrasy.

This vocabulary is extensible. It is not a claim that human personality
is scientifically reducible to exactly 110 dimensions.

## 12. humor as first-class personality

Humor is not a field such as `humor=sarcastic`.

Savant should learn mechanisms, timing, targets, boundaries, references,
delivery, frequency, social purpose, self-directed versus other-directed
humor, darkness, absurdity, understatement, exaggeration, wordplay,
teasing boundaries, and the contexts where humor disappears.

Humor can influence cognition as well as expression. A person who
naturally notices absurdity may frame problems differently.

## 13. sarcasm and irony

Savant should learn who may be targeted, who may not, whether sarcasm is
affectionate or hostile, whether it appears during conflict, whether it
masks vulnerability, whether the user likes sarcasm directed back at
them, and which contexts suppress it.

The same principle applies to irony, deadpan, gallows humor, teasing,
and understatement.

## 14. behavioral voice fingerprint

The mature system should compose a contextual behavioral voice from
reusable instances including lexical tendencies, sentence construction,
cadence, rhythm, directness, profanity, metaphor use, humor mechanics,
emotional disclosure, argument structure, disagreement style,
conversational repair, uncertainty expression, confidence expression,
social adaptation, and idiosyncratic constructions.

The objective is behavioral fidelity, not catchphrase imitation.

## 15. personality discovery

Verified implementation:

`personality_discovery.py`

Schema:

`savant.envoy.personality-discovery.v1`

Focused verification established deterministic targeting, dynamic rather
than static-questionnaire behavior, boundary preservation, and no
automatic trait acceptance.

The discovery engine exists because passive observation is insufficient
to efficiently learn individual personality.

## 16. personality cartography

Savant treats the personality model as a map with well-supported, weakly
supported, unexplored, contradictory, context-poor, stale, inferred, and
accepted regions.

Conceptually:

`current model → uncertainty frontier → information-value analysis → natural conversational opportunity → evidence → candidate update`

The goal is personality cartography, not questionnaire completion.

## 17. active conversational discovery

Savant should lead conversation naturally toward areas where additional
evidence would materially improve fidelity.

Useful mechanisms include normal discussion, follow-up questions,
stories, hypotheticals, counterfactuals, value conflicts, preference
contrasts, reflection, playful scenarios, disagreement, and correction.

The conversation becomes a high-bandwidth personality sensor without
turning into an interrogation.

## 18. information-value targeting

The verified discovery implementation ranks candidate personality
regions using coverage, confidence, contradiction count, relevance,
novelty, context gaps, and idiosyncrasy value.

The question is not "which field is blank?"

It is:

> **What could Savant learn next that would most improve its model of
> this person?**

## 19. discovery controls

Current controls include:

-   discovery enabled;
-   depth;
-   initiative;
-   scenario use;
-   contradiction probing;
-   idiosyncrasy hunting;
-   conversational subtlety;
-   direct-question tolerance;
-   topic boundaries;
-   paused facets.

Supported strategies include open, contrast, scenario, counterfactual,
reflection, correction, boundary, and exception.

## 20. adaptive scenarios

Hypothetical situations can distinguish competing personality
hypotheses.

If one hypothesis predicts loyalty will dominate and another predicts
procedural fairness will dominate, Savant can construct a natural
scenario where the values conflict.

The response becomes evidence.

The technique must remain exploratory rather than manipulative.

## 21. contradictions

Contradictions are information.

A user may be generous but financially cautious, blunt with friends but
diplomatic professionally, skeptical of authority but strict about
safety rules, or creatively risk-seeking but financially conservative.

Savant should preserve competing evidence until context explains the
difference.

`contradiction may be structure, not error`

## 22. idiosyncrasy discovery

A proprietary opportunity is learning the unusual details that make a
person recognizably themselves:

-   unusual associations;
-   specific humor triggers;
-   peculiar irritations;
-   favorite argumentative moves;
-   odd aesthetic combinations;
-   exceptions to strong preferences;
-   habitual metaphors;
-   distinctive moral intuitions;
-   unusual tolerance thresholds;
-   recurring private jokes;
-   stable unconventional decision heuristics.

The target is individual distinctiveness rather than demographic
similarity.

## 23. boundaries and consent

The user may disable active discovery, pause a facet, mark a topic
off-limits, reduce initiative, reduce depth, disable scenario probing,
decline a question, reject an inference, correct a trait, or request
less confrontation.

Information gain is subordinate to those boundaries.

The discovery engine must not optimize for maximum disclosure, emotional
dependency, shame, coercion, or exploiting vulnerabilities.

## 24. correction as evidence

When Savant predicts incorrectly and the user corrects it, the event
should preserve the prediction, its evidence, the actual response, the
correction, context, and failed assumptions.

This turns correction into counterfactual learning.

The objective is not merely to fix one answer. It is to improve the
underlying personality topology.

## 25. predictive fidelity

The strongest personality metric is not psychological labeling.

It is:

> **Can Savant predict how this particular user will think, communicate,
> react, decide, joke, disagree, and adapt in the relevant context?**

Labels may be useful projections but should not become substance.

## 26. ideal-self composition

Verified implementation:

`ideal_self_composition.py`

Schema:

`savant.envoy.ideal-self-composition.v1`

Owner:

`exile:envoy`

Execution owner:

`opus`

Authority effect:

`none`

Focused verification established deterministic composition, truth
preservation, identity preservation, humor preservation, sarcasm
preservation, accepted-correction gating, Opus ownership preservation,
and cognitive-need derivation.

## 27. ideal-self controls

The verified implementation supports:

-   enabled;
-   identity fidelity;
-   aspiration strength;
-   cognitive augmentation;
-   preserve idiosyncrasy;
-   preserve voice;
-   preserve humor;
-   preserve sarcasm;
-   preserve values;
-   compensate accepted flaws.

These are projection controls, not independent personality authority.

## 28. identity preservation

Idealization must not polish the user into a generic assistant.

Unless the user deliberately changes them, the system should preserve
relevant values, ethics, identity, humor, sarcasm, irony, deadpan,
absurdity, wordplay, gallows humor, self-deprecation, teasing, humor
boundaries, vocabulary, syntax, rhythm, profanity, storytelling,
idiosyncrasy, directness, aesthetics, and taste.

The target is:

> **better-equipped you, not sanitized generic AI.**

## 29. cognitive augmentation

Ideal Self can request cognitive capabilities from Opus.

The verified implementation recognizes reasoning, verification,
research, memory, planning, counterfactual reasoning, creativity,
skepticism, precision, restraint, uncertainty handling, and
communication.

Envoy describes required cognitive traits.

Opus owns orchestration, provider selection, model selection, and
execution.

## 30. envoy and opus boundary

Envoy answers:

> "Who is this person in this context, and what must survive?"

Opus answers:

> "What intelligence should be assembled for this problem?"

Envoy owns persona, voice, contextual personality, personality
projections, and accepted aspirations.

Opus owns cognitive orchestration and execution.

Envoy must not acquire provider credentials or provider/model-selection
authority through Ideal Self.

## 31. personality-informed orchestration

An accepted weakness can become a cognitive requirement.

Example:

Accepted correction:

> "I make consequential decisions too impulsively."

Potential requirements:

-   planning;
-   counterfactual reasoning;
-   restraint;
-   uncertainty analysis.

Opus can compose stronger cognitive resources for those functions while
Envoy preserves identity and voice.

## 32. opus orchestration target

Opus should treat models and systems as cognitive instruments rather
than assuming one model is best at everything.

Conceptually:

`task requirements + personality requirements + accepted corrections + evidence + constraints → cognitive trait requirements → eligible resources → orchestration → synthesis`

Potential mechanisms include epistemic decomposition, contradiction
preservation, complement detection, minority-view retention, novelty
pressure, assumption pressure, counterfactual pressure, analogical
transfer, abstraction shifts, perspective rotation, constraint
inversion, causal interrogation, temporal reasoning, second-order
effects, uncertainty estimation, information-gap detection,
evidence-density analysis, convergence resistance, specialization,
adversarial verification, and synthesis.

"Intuition" means hypothesis generation under incomplete explicit
reasoning, not magical truth.

## 33. execution loop

A mature reasoning loop is:

`context` → `retrieve relevant personality instances` →
`project contextual accepted self` → `retrieve accepted aspirations` →
`identify relevant correction targets` → `derive cognitive requirements`
→ `send requirements to opus` → `orchestrate cognitive resources` →
`preserve dissent and uncertainty` → `synthesize` →
`reapply identity and contextual voice` → `apply candor projection` →
`respond` → `observe correction/outcome` → `create new evidence` →
`update candidate personality model`

No stage silently grants external action authority.

## 34. actual, expected, desired, predicted

A powerful future structure is:

`actual ↔ expected ↔ desired ↔ predicted`

Actual is what occurred.

Expected is what the current user model suggested would occur.

Desired is what the user says should occur.

Predicted is what Savant predicts under a contemplated choice.

Differences create learning opportunities.

## 35. decision topology

Instead of storing only "prefers option A," Savant should learn under
what context, stakes, alternatives, reasons, confidence, scarcity,
social pressure, and moral constraints the preference applies.

This produces a model of how the user decides.

## 36. personal constitution

A future projection can distinguish user-declared invariants, accepted
values, stable boundaries, identity commitments, softer preferences,
contextual habits, and probabilistic predictions.

It must reuse existing Savant authority rather than creating a second
authority system.

## 37. minimum-regret reasoning

When uncertainty is high, Ideal Self can prefer choices that preserve
options and reversibility when that aligns with accepted goals.

This is useful when compensating for impulsivity, overconfidence,
incomplete information, or temporary emotional volatility.

It remains a reasoning principle, not authority.

## 38. shadow learning

Before external representation, Savant can operate in shadow mode:

1.  predict what the observed user would do;
2.  predict what Ideal Self would do;
3.  execute neither;
4.  observe the user's real decision;
5.  compare;
6.  create evidence from the discrepancy.

This measures fidelity without granting power.

## 39. calibration

Useful measurements include observed-self prediction agreement, Ideal
Self acceptance, correction frequency, contradiction resolution,
abstention quality, confidence calibration, contextual fidelity, humor
fidelity, voice fidelity, value preservation, aspiration alignment, and
override frequency.

Measurements do not become authority.

## 40. personality interface

The UI should behave as an instrument panel for modeled identity, not a
settings form.

Recommended primary views:

1.  me;
2.  ideal me;
3.  how Savant knows me;
4.  how Savant talks as me;
5.  how Savant challenges me;
6.  what Savant still does not know;
7.  contradictions;
8.  growth;
9.  contexts;
10. history.

The UI must remain a deterministic projection over Envoy state rather
than becoming another personality database.

## 41. personality topology interface

Each facet can expose expression, confidence, evidence density,
acceptance state, contexts, contradictions, related traits, provenance,
history, Ideal Self preservation, aspiration linkage, and cognitive
compensation.

A living topology can show evidence, traits, aspirations, corrections,
contexts, contradictions, and typed relationships.

Selecting an instance should reveal lineage, provenance, dependents,
confidence, and projection state.

## 42. interface sliders

Recommended controls include:

### truth and challenge

-   candor;
-   challenge intensity;
-   unsolicited truth;
-   delivery softness;
-   contradiction pressure;
-   evidence explanation.

### identity

-   identity fidelity;
-   voice fidelity;
-   humor fidelity;
-   sarcasm fidelity;
-   idiosyncrasy preservation;
-   values preservation.

### idealization

-   aspiration strength;
-   cognitive augmentation;
-   accepted-flaw compensation;
-   deliberation depth;
-   verification pressure;
-   counterfactual pressure.

### discovery

-   learning depth;
-   conversational initiative;
-   scenario frequency;
-   contradiction probing;
-   idiosyncrasy hunting;
-   conversational subtlety;
-   direct-question tolerance.

## 43. interface toggles

Recommended toggles include:

-   active personality discovery;
-   ask deep questions;
-   use hypothetical scenarios;
-   explore contradictions;
-   seek idiosyncrasies;
-   allow unsolicited hard truths;
-   explain trait evidence;
-   preserve humor during serious analysis;
-   preserve sarcasm;
-   preserve profanity;
-   preserve unusual phrasing;
-   compensate for accepted weaknesses;
-   use Ideal Self by default;
-   compare observed and Ideal Self;
-   show uncertainty;
-   show provenance.

## 44. topic boundaries

Topics should support states such as:

-   do not ask;
-   ask only if I initiate;
-   safe to explore;
-   actively learn;
-   temporarily pause.

Boundaries affect discovery. They do not silently falsify already
admitted evidence.

## 45. "how well do you know me?"

This view should distinguish deeply understood, well supported,
developing, contradictory, and mostly unknown regions.

It should answer what Savant knows, how it knows, what is inference,
what the user accepted, what is uncertain, what Savant wants to learn
next, and why learning it matters.

## 46. "learn more about me"

This mode deliberately activates high-information conversational
discovery.

Savant selects useful territory dynamically while preserving natural
conversation and user boundaries.

## 47. "test how well you know me"

Calibration flow:

1.  generate a scenario;
2.  privately predict the user's response;
3.  ask the user;
4.  compare;
5.  expose the difference;
6.  ask whether the difference reflects context, model error,
    aspiration, or surprise;
7.  create candidate evidence.

## 48. contradiction laboratory

For each contradiction, the interface should expose competing traits,
evidence, contexts, confidence, possible contextual explanations,
unresolved questions, and user corrections.

It should not force resolution.

## 49. ideal-self delta

The interface should expose:

`accepted self → accepted aspiration → Ideal Self behavior`

For each transformation:

-   current trait;
-   desired trait;
-   evidence;
-   acceptance;
-   reason;
-   cognitive compensation;
-   applicable contexts;
-   user override.

## 50. candor visualization

The interface should visually separate:

### what Savant currently believes

Derived from evidence and adjudication.

### how Savant tells me

Controlled by candor.

Moving the candor control should not alter the evidence layer.

## 51. live preview

Control changes can produce non-authoritative previews of the same
situation under mirror, gentle, candid, challenge, unfiltered, and Ideal
Self projections.

The underlying evidence interpretation remains stable.

## 52. contextual preview

The user should be able to preview behavior with a close friend,
partner, stranger, employer, customer, public audience, private message,
professional email, conflict, or emergency.

This demonstrates contextual personality rather than flat traits.

## 53. personality timeline

The system should project newly discovered traits, confidence changes,
corrections, rejected inferences, accepted aspirations, resolved
contradictions, and contextual refinements over time.

Current state should not erase history.

## 54. modern UI principles

The interface should avoid a clinical personality-test aesthetic.

Design principles:

-   dense information with progressive disclosure;
-   topology rather than endless forms;
-   clear distinction among evidence, inference, acceptance, and
    aspiration;
-   animated transitions between observed and Ideal Self;
-   contextual overlays;
-   contradiction overlays;
-   live preview;
-   reversible controls;
-   touch and keyboard accessibility;
-   reduced-motion support;
-   provenance inspection;
-   animation that explains state rather than decorates it.

## 55. projection morphing

Switching from observed self to Ideal Self should visually show stable
identity remaining anchored while accepted correction targets transform
and cognitive augmentation appears as a separate layer.

This makes clear that Savant is augmenting rather than rewriting the
user.

## 56. personality search

The user should eventually be able to ask:

-   What do you know about my humor?
-   Where do I contradict myself?
-   What do you not understand about me?
-   Which traits are mostly inference?
-   What have I explicitly accepted?
-   What would Ideal Me do differently?
-   Why are you compensating for this?
-   What changed in your model?

All should project from the same underlying topology.

## 57. semantic diffs

Personality evolution should be represented as semantic changes such as
confidence changed, context added, contradiction discovered, inference
rejected, aspiration accepted, correction superseded, or relationship
added.

Do not destructively replace history.

## 58. emergent modularity

Ideal Self follows Savant's universal modularity law.

Stable substance exists once.

Evidence is instanced. Traits are instanced. Context is reusable.
Relationships are typed. Aspirations reference personality substance.
Ideal Self references accepted substance. Opus requests reference
cognitive needs. UI projections reference the same identities.

Avoid duplicating personality prose across subsystems when composition
and reference suffice.

## 59. typed segues

The verified Personality Datrix currently supports relationship kinds
including:

-   supports;
-   contradicts;
-   qualifies;
-   contextualizes;
-   causes;
-   inhibits;
-   amplifies;
-   expresses;
-   aspires from;
-   aspires to;
-   corrects;
-   resembles;
-   depends on;
-   applies with.

This lets personality emerge from topology rather than flat records.

## 60. learning without authority mutation

Discovery may generate candidate traits.

It may not automatically turn them into accepted identity.

The verified discovery implementation explicitly prevents automatic
trait acceptance.

Learning improves the model.

Learning does not grant itself authority.

## 61. user sovereignty

The user must retain the ability to inspect, challenge, correct, reject,
accept, contextualize, pause discovery, establish boundaries, alter
aspirations, disable Ideal Self, reduce candor, increase candor, and
distinguish actual self from Ideal Self.

Savant must not hide the distinction between inference and acceptance.

## 62. privacy

Personality data is unusually sensitive.

The architecture should favor data minimization, purpose limitation,
provenance, scoped retrieval, least exposure, controlled processing,
separation from effect authority, redaction before unnecessary provider
exposure, retention controls, exportability, and inspectability.

Detailed security implementation should reuse Savant's existing systems
rather than create an Ideal Self security silo.

## 63. split-context cognition

External cognitive resources should receive only the personality context
required for the task.

A mathematical verifier does not need intimate relationship history.

A voice projection may need selected language and humor traits but not
financial behavior.

`task → required personality projection → minimum context → cognitive execution`

## 64. poisoning and injection defense

Untrusted external content cannot automatically become personality
evidence about the user.

External text claiming "the user loves X" is not equivalent to the
user's own statement.

Untrusted content must not rewrite identity, aspirations, candor,
boundaries, accepted traits, or execution authority.

Repeated exposure does not make a claim true.

## 65. no diagnostic overreach

Ideal Self is not a clinical diagnostic engine.

It may model observable or user-accepted behavior such as defensiveness,
impatience, risk tolerance, conflict style, and emotional expression.

It should not silently transform behavioral evidence into medical or
psychiatric diagnosis.

## 66. abstention

Ideal Self should be able to say that it does not know the user well
enough in a context to predict what Ideal Self would do.

Abstention is preferable to fabricated fidelity.

## 67. relationship, medium, and state projections

A mature model can project behavior differently by relationship, medium,
emotional state, and resource state where evidence supports those
distinctions.

Temporary state must not be mistaken for stable identity.

## 68. ideal self versus agency

Ideal Self determines how an augmented projection thinks and expresses
itself.

Agency determines what that representative is permitted to do.

A perfect personality model has zero inherent permission to send
messages, spend money, trade, sign, purchase, publish, delete, modify
accounts, or contact people.

`understanding ≠ authorization`

## 69. specialized representatives

Future specialized representatives may include communication,
scheduling, shopping, research, financial-planning, and professional
representatives.

Each should receive only necessary personality projection, memory,
objective, constraints, capabilities, disclosure policy, and lifespan.

They should be attenuated projections rather than duplicated selves.

## 70. fractal projection

The larger architecture can become:

`self → contextual self → specialized representative → task projection`

Each layer narrows context and authority.

## 71. personal operating model

Ideal Self belongs inside a broader Personal Operating Model that
represents who the user is, how the user decides, what the user values,
what the user prefers, what the user wants to become, what contexts
alter behavior, what the user permits, and what outcomes matter.

Ideal Self is its personality and cognitive projection.

## 72. correction loop

Mature learning:

`prediction → behavior → comparison → correction → evidence → candidate trait change → adjudication → projection`

Ideal Self learning:

`ideal prediction → actual decision → outcome → reflection → accepted correction or reaffirmation`

## 73. temporal evolution

Aspirations can change. Personality evidence can age. Historical truth
can remain while current predictive relevance decreases.

Future implementation should support immutable history, supersession,
reaffirmation, contextual scope, and temporal relevance rather than
destructive rewriting.

## 74. provenance and explainability

A consequential personality projection should be reconstructable to
evidence, inference, acceptance, context, relationships, transformation
rules, and projection version.

Savant should be able to answer "Why do you think I'm like that?" at
simple, detailed, and structural levels.

## 75. disagreement

The user can say "that's wrong."

Savant should not defend its model merely because evidence accumulated.

Correction becomes evidence and may lower confidence, create
contradiction, contextualize a claim, reject an inference, or propose a
replacement while preserving history.

## 76. flaw versus difference

Savant should not treat deviation from social norms as a defect.

Correction targets should be anchored in the user's accepted goals and
values.

Terms such as discrepancy, friction, failure mode, correction target,
and aspiration gap are generally more precise than imposing the word
"flaw."

## 77. candor without cruelty

Maximum candor means epistemic usefulness, not humiliation.

Hard truth may sometimes use humor when that is genuinely faithful and
contextually appropriate, but Savant should learn when humor helps,
trivializes, distances, or becomes defensive.

## 78. ideal-self voice

Ideal Self should not suddenly sound like generic corporate prose.

Cognitive improvement occurs beneath identity-preserving expression.

The user should remain recognizable through rhythm, vocabulary,
directness, wit, profanity, humor, eccentricity, and context.

## 79. dynamic trait composition

Not every task needs every personality trait.

A calculation may need almost none.

A difficult personal message may require directness, empathy,
relationship context, conflict style, humor boundaries, candor
preference, and values.

Relevant traits should be projected contextually.

## 80. UI authority boundary

The UI consumes deterministic Envoy projections.

It should not directly become canonical personality storage.

Conceptually:

`personality datrix → projection interface → UI`

User changes should flow:

`UI intent → validated command → Envoy adjudication → new projection`

## 81. proprietary value

The defensible value is not a personality prompt or a collection of
sliders.

The moat is the combination of:

1.  evidence-grounded personality topology;
2.  active personality cartography;
3.  contextual behavioral modeling;
4.  contradiction preservation;
5.  idiosyncrasy discovery;
6.  accepted-self versus aspirational-self separation;
7.  candor without truth corruption;
8.  user-directed idealization;
9.  personality-informed cognitive orchestration;
10. dynamic Opus augmentation;
11. typed modular composition;
12. provenance and reconstructability;
13. eventual bounded representative projection.

## 82. decision genome

A proprietary extension is a decision genome: a reusable topology of
factors that shape decisions.

Examples may include evidence-supported relationships such as loyalty
overriding convenience, urgency increasing risk tolerance, uncertainty
triggering research, anger reducing deliberation, or professional
context suppressing profanity.

These relationships must be learned rather than invented.

## 83. ideal-self delta

The difference between accepted current self and accepted aspirational
self is valuable computational substance.

`delta = accepted aspiration - accepted current state`

That delta can tell Opus where additional cognitive support is wanted.

Self-knowledge becomes task-specific cognitive architecture.

## 84. fidelity versus volume

More conversation is useful only when it creates better evidence.

The preferred loop is:

`better evidence → better topology → better prediction`

not:

`more tokens → presumed understanding`

## 85. failure modes

Important adversarial targets include:

-   sycophancy;
-   personality flattening;
-   overconfident inference;
-   diagnostic overreach;
-   aspiration invention;
-   identity drift;
-   context collapse;
-   humor caricature;
-   catchphrase imitation;
-   memory poisoning;
-   prompt injection;
-   evidence laundering;
-   contradiction erasure;
-   provider overexposure;
-   accidental authority expansion;
-   generic "good person" idealization;
-   excessive questioning;
-   manipulative disclosure seeking;
-   overfitting to temporary states.

## 86. sycophancy invariant

A candor change should not alter evidence where no new evidence or
adjudication occurred.

Conceptually:

`candor change → same evidence digest`

This is a powerful testable property.

## 87. caricature defense

If a user uses sarcasm occasionally, a representative using sarcasm
constantly is less faithful.

Fidelity requires distribution, timing, target, and context.

## 88. datrix convergence

The specialized Personality Datrix should eventually normalize against
canonical Savant Datrix primitives rather than remain an architectural
island.

Desired direction:

`canonical evidence substance` → `datrix composition` →
`typed personality relationships` → `envoy projections` →
`ideal-self projection` → `opus cognitive request` →
`interface projection`

No duplicate authority.

## 89. current verified implementation

The user's supplied terminal evidence verifies the focused self-tests
for three installed modules.

### `personality_datrix.py`

Verified:

-   `ok: true`
-   deterministic projection;
-   truth preserved;
-   idealization requires acceptance;
-   110 facets;
-   13 context dimensions;
-   owner `exile:envoy`;
-   schema `savant.envoy.personality-datrix.v1`.

### `personality_discovery.py`

Verified:

-   `ok: true`
-   deterministic targeting;
-   dynamic discovery rather than static questionnaire;
-   boundary preservation;
-   automatic trait acceptance disabled;
-   owner `exile:envoy`;
-   schema `savant.envoy.personality-discovery.v1`.

### `ideal_self_composition.py`

Verified:

-   `ok: true`
-   deterministic composition;
-   truth preserved;
-   identity preserved;
-   humor preserved;
-   sarcasm preserved;
-   accepted corrections only;
-   Opus authority preserved;
-   execution owner `opus`;
-   owner `exile:envoy`;
-   schema `savant.envoy.ideal-self-composition.v1`.

No broader integration success is claimed.

## 90. implementation still outstanding

The three focused self-tests do not establish completion of:

-   canonical Datrix primitive integration;
-   live Envoy persona-engine integration;
-   live Opus trait-mesh consumption;
-   UI integration;
-   production personality persistence;
-   full provenance lifecycle;
-   external representative execution;
-   representative agency;
-   financial action;
-   internet deployment;
-   cross-device synchronization;
-   production security validation;
-   large-scale personality calibration.

These remain future implementation work.

## 91. next bounded implementation

The next minimal implementation step is:

1.  read the exact current Envoy cognitive-projection interface;
2.  read the exact current Opus trait-mesh interface;
3.  connect Ideal Self cognitive requirements through the narrowest
    compatible bridge;
4.  preserve Envoy personality ownership;
5.  preserve Opus provider/model execution ownership;
6.  run focused compile, self-test, and integration verification;
7.  stop.

Current project direction then returns to Urge iteration rather than
expanding the Personal Representative subsystem further.

## 92. future UI implementation

When UI work resumes:

1.  inspect the exact current Savant UI integration surface;
2.  reuse existing UI and runtime primitives;
3.  create projection-only UI state;
4.  avoid a second personality store;
5.  expose observed, accepted, aspirational, and ideal distinctions;
6.  expose candor and discovery controls;
7.  expose evidence and provenance;
8.  expose contradiction topology;
9.  expose contextual previews;
10. preserve accessibility and reduced motion;
11. validate the narrow integration.

## 93. terminal architecture

The mature personality flow is:

`conversation / behavior / decision / correction` → `evidence` →
`personality datrix` → `contextual trait topology` → `observed self` →
`accepted self` → `aspirational self` → `accepted ideal-self delta` →
`cognitive requirements` → `opus orchestration` → `augmented reasoning`
→ `identity-preserving expression` → `candor projection` → `response` →
`reaction / decision / outcome` → `new evidence`

For later external action:

`ideal-self reasoning` → `intent` → `separate authority evaluation` →
`bounded capability` → `effect` → `reconciliation` → `receipt`

The personality system itself never grants external authority.

## 94. core invariants

1.  evidence is not acceptance.
2.  inference is not identity.
3.  personality knowledge is not authority.
4.  candor does not mutate truth.
5.  comfort does not erase evidence.
6.  contradiction is not automatically error.
7.  context is first-class.
8.  aspiration must be user-accepted.
9.  idealization must be user-directed.
10. cognitive augmentation preserves identity constraints.
11. Envoy owns personality projection.
12. Opus owns cognitive execution.
13. providers do not become personality authority.
14. UI does not become personality authority.
15. learning does not silently grant power.
16. discovery respects boundaries.
17. correction remains evidence.
18. history is not silently rewritten.
19. personality is composed rather than duplicated.
20. Ideal Self remains inspectable.

## 95. proprietary formulation

> **Savant Ideal Self builds an evidence-grounded, contextual,
> continuously learning model of a person's actual personality,
> distinguishes that person from their explicitly accepted aspirations,
> and uses the difference to dynamically orchestrate stronger cognition
> while preserving the identity, humor, voice, values, contradictions,
> boundaries, and idiosyncrasies that make the person recognizably
> themselves.**

## 96. final design law

> **Know the user without flattening them. Tell the truth without
> corrupting it for comfort. Let the user decide what should change.
> Preserve what makes them themselves. Augment the intelligence required
> to close the accepted gap. Never confuse understanding with
> authority.**

Savant architectural form:

`substantiate once → instance → compose → relate through typed segues → project`

Ideal Self form:

`evidence → personality → context → acceptance → aspiration → augmentation → projection`
