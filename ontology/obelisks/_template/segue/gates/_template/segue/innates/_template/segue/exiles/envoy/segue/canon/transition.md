# envoy segue transition

## status

active

## owner

envoy

## purpose

the envoy segue projects envoy-owned capabilities and relationships across composed exile boundaries while preserving the authority, identity, lineage, and execution ownership of every participant.

segue composition does not transfer authority.

## palaver to envoy

palaver owns conversation execution and the conversation-facing http surface.

palaver delegates persona and voice resolution to envoy.

envoy owns:

- persona identity
- persona resolution
- persona projection
- voice identity
- voice resolution
- voice intent
- voice metadata projection

persona selection precedence is:

1. request
2. workspace
3. default

the default persona is `orobouros`.

palaver may invoke envoy-owned persona and voice capabilities, but invocation does not make palaver their owner.

envoy does not acquire conversation ownership by participating in a palaver conversation.

## envoy to opus

envoy delegates provider execution to opus.

the active execution routes are:

- `text_inference_route`
- `voice_tts_route`

opus owns:

- provider selection
- provider routing
- provider credentials
- provider execution
- provider retry policy
- provider fallback policy

envoy may emit semantic intent and execution requirements to opus.

envoy may not select the external provider, access provider credentials, execute provider calls directly, define provider retry policy, or define provider fallback policy.

delegation does not transfer any opus-owned provider authority to envoy.

## voice pipeline

the voice pipeline is composed as:

1. palaver establishes the effective conversation request.
2. persona precedence resolves request, workspace, or default persona selection.
3. envoy resolves the effective persona.
4. envoy resolves the persona's voice profile.
5. envoy emits voice intent.
6. opus selects the external provider.
7. opus routes and executes the provider request.
8. opus returns provider output.
9. envoy projects provider output into the envoy-owned voice result.
10. palaver returns that result through its conversation-owned http surface.

## text inference pipeline

the text inference boundary between envoy and opus uses `text_inference_route`.

envoy may project text inference intent across this boundary.

opus retains provider selection, routing, credentials, execution, retry, and fallback authority.

successful composition across this route does not make envoy an inference-provider execution owner.

## voice tts pipeline

the speech execution boundary between envoy and opus uses `voice_tts_route`.

envoy resolves persona and voice intent before delegation.

opus executes the external speech provider.

provider output may include:

- provider
- mime type
- audio format
- audio payload

envoy projects that provider output into its voice result without acquiring provider execution authority.

## ownership invariant

the composed system preserves these ownership boundaries:

- conversation: palaver
- persona: envoy
- voice: envoy
- provider selection: opus
- provider routing: opus
- provider credentials: opus
- provider execution: opus
- provider retry policy: opus
- provider fallback policy: opus

## lineage invariant

composition preserves lineage.

a result projected through another exile does not change the owner of the underlying capability.

palaver invocation of envoy does not make palaver the persona or voice owner.

envoy invocation of opus does not make envoy the provider execution owner.

provider output projected by envoy does not erase opus execution lineage.

## authority invariant

composition, projection, invocation, routing, and delegation do not imply authority inheritance or authority transfer.

ownership remains attached to the authoritative primitive that owns the capability.

the envoy segue exists to compose those primitives without duplicating or collapsing them.
