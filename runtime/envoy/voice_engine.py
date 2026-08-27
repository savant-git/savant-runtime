from dataclasses import dataclass

@dataclass
class VoiceProfile:
    persona_id: str
    display_name: str
    provider: str
    model: str
    voice: str
    accent: str
    region: str
    era: str
    rate: float
    pitch: float
    temperature: float

VOICE_REGISTRY = {}

def register(profile: VoiceProfile):
    VOICE_REGISTRY[profile.persona_id] = profile

def get(persona_id):
    return VOICE_REGISTRY.get(persona_id)

register(
    VoiceProfile(
        persona_id="palaver_default",
        display_name="Palaver",
        provider="openai",
        model="gpt-4o-mini-tts",
        voice="alloy",
        accent="neutral",
        region="global",
        era="modern",
        rate=1.0,
        pitch=1.0,
        temperature=0.3,
    )
)
