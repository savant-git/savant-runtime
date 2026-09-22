# envoy migration

## status

ready

## owner

envoy

## target

savant-runtime

## purpose

this record establishes the migration boundary for the envoy exile and preserves the authority, identity, lineage, composition, runtime behavior, dependencies, dependents, routes, and ownership relationships established by the current implementation.

migration does not create a new envoy.

migration preserves the existing envoy instance and its relationships.

## identity

envoy remains:

- id: `envoy`
- graph id: `exile:envoy`
- type: `exile`
- composition level: `exile`

the existing envoy identity must survive migration unchanged.

## authority

the authoritative ownership boundaries are:

- conversation: palaver
- persona: envoy
- voice: envoy
- provider execution: opus

envoy owns:

- persona identity
- persona resolution
- persona selection
- voice identity
- voice resolution
- voice intent

palaver owns:

- conversation execution
- the conversation-facing http surface

opus owns:

- provider selection
- provider routing
- provider credentials
- provider execution
- provider retry policy
- provider fallback policy

migration must not transfer, duplicate, infer, or weaken these authorities.

## persona precedence

effective persona selection remains:

1. request
2. workspace
3. default

the default envoy persona remains:

`orobouros`

## runtime

the active envoy runtime components are:

- `runtime/persona_engine.py`
- `runtime/voice_engine.py`
- `runtime/opus_bridge.py`

persona resolution remains envoy-owned.

voice resolution remains envoy-owned.

external provider execution remains delegated to opus.

envoy must not directly access provider credentials or execute provider calls.

## text execution

envoy delegates text provider execution to opus through:

`text_inference_route`

opus remains execution owner.

delegation does not transfer provider authority to envoy.

## voice execution

the composed voice pipeline remains:

1. palaver establishes the effective conversation request.
2. envoy resolves the effective persona.
3. envoy resolves the persona voice profile.
4. envoy emits provider-neutral voice intent.
5. opus selects the provider.
6. opus executes the provider.
7. envoy projects provider output into the voice result.
8. palaver returns the result through its conversation-owned http surface.

the execution route is:

`voice_tts_route`

## composition

envoy depends on:

`exile:opus`

envoy is depended upon by:

`exile:palaver`

the primary composed relationships are:

`exile:palaver -> exile:envoy`

relation:

`delegates_persona_voice_resolution_to`

and:

`exile:envoy -> exile:opus`

relation:

`delegates_provider_execution_to`

neither relationship transfers authority.

## migration invariants

migration must preserve:

- envoy identity
- envoy graph address
- exile composition level
- persona identity
- persona resolution
- persona selection
- voice identity
- voice resolution
- voice intent
- request/workspace/default persona precedence
- orobouros as the default persona
- palaver conversation ownership
- opus provider execution ownership
- text inference delegation
- voice synthesis delegation
- dependencies
- dependents
- graph edges
- segue relationships
- contracts
- lineage
- provider-neutral envoy requests
- provider credential isolation
- authority boundaries
- authority non-transfer
- deterministic composition

migration must not:

- reconstruct envoy as a new identity
- duplicate envoy substance
- move provider authority into envoy
- move persona or voice authority into palaver
- move persona or voice authority into opus
- expose provider credentials to envoy
- permit envoy to execute provider calls directly
- collapse palaver, envoy, and opus into one authority
- reinterpret delegation as inheritance
- reinterpret composition as ownership

## established implementation evidence

the current implementation has demonstrated:

- default persona resolution
- non-default persona resolution
- persona-to-voice attachment
- voice registry resolution
- envoy-to-opus voice delegation
- opus provider execution
- provider authority preservation
- palaver-to-envoy voice integration
- palaver voice http synthesis
- provider result projection
- mime type projection
- audio format projection
- base64 audio projection
- successful synthesized audio response

the demonstrated ownership projection is:

- conversation owner: `palaver`
- persona owner: `envoy`
- voice owner: `envoy`
- provider owner: `opus`

## migration rule

the savant-runtime migration is a preservation operation.

existing authoritative primitives, identities, relationships, lineage, and runtime behavior survive migration.

derived structures remain projections of those primitives.

no authority is created merely because a component invokes, imports, exports, composes, projects, depends upon, or delegates execution to another component.

## readiness

envoy is ready to participate in the savant-runtime migration subject to the final migration operation preserving the invariants defined above.
