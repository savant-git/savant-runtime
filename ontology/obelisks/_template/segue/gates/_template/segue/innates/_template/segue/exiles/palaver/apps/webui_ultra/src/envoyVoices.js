export const ENVOY_VOICES = {
  palaver_default: {
    persona_id: "palaver_default",
    display_name: "Palaver Default",
    voice_family: "clear_control_plane",
    accent: "neutral American English",
    period: "contemporary",
    region: "networked runtime",
    cadence: "measured, direct, crisp",
    pitch: 0.82,
    rate: 0.92,
    formality: "high",
    vocabulary_style: "technical but plain",
    historical_basis: "none",
    safety_note: "Native synthetic Palaver voice, not based on a real person."
  },

  envoy_historical_research_mode: {
    persona_id: "envoy_historical_research_mode",
    display_name: "Historical Research Mode",
    voice_family: "historical_approximation",
    accent: "research-derived",
    period: "persona-specific",
    region: "persona-specific",
    cadence: "persona-specific",
    pitch: 0.86,
    rate: 0.88,
    formality: "contextual",
    vocabulary_style: "period-informed",
    historical_basis: "derived from documented time, region, class, language, and writing style",
    safety_note: "Approximation only. Does not claim to recreate an actual human voice."
  }
};

export function getEnvoyVoice(personaId) {
  return ENVOY_VOICES[personaId] || ENVOY_VOICES.palaver_default;
}

export function applyEnvoyVoice(utterance, personaId) {
  const profile = getEnvoyVoice(personaId);

  utterance.rate = profile.rate ?? 0.92;
  utterance.pitch = profile.pitch ?? 0.82;
  utterance.volume = 1;

  const voices = window.speechSynthesis?.getVoices?.() || [];

  const preferred =
    voices.find(v => /Google|Microsoft|Natural|English|US|UK/i.test(v.name)) ||
    voices.find(v => /en/i.test(v.lang)) ||
    voices[0] ||
    null;

  if (preferred) utterance.voice = preferred;

  return utterance;
}
