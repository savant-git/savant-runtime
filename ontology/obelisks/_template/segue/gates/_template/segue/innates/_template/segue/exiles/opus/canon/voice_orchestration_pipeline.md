# OPUS VOICE ORCHESTRATION PIPELINE
# STATUS: CANON
# AUTHORITY: USER DIRECTIVE
# OWNER: OPUS
# CONSUMER: ENVOY
# CALLER: PALAVER

Opus owns API orchestration.

Envoy owns persona identity, voice characteristics, accent, language,
pronunciation, speaking style, and presentation intent.

Palaver owns conversation and dialogue.

Runtime flow:

Palaver
  -> Envoy
  -> Opus
  -> External API Provider
  -> Opus
  -> Envoy
  -> Palaver

Rules:

- Envoy must not hardcode provider execution.
- Envoy emits provider-agnostic voice requests.
- Opus resolves credentials, provider, model, cost policy, latency policy,
  retry policy, and fallback policy.
- Opus returns audio plus provider lineage.
- Envoy attaches persona and voice metadata.
- Palaver consumes final response/audio.
