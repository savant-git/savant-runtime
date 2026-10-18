import type {UrgePersona,UrgePersonaMode} from "./urge-types"
export type PanelTab = "session" | "future";

export const limits = {
  iterations: { min: 1, max: 21 },
  intervalMs: { min: 0, max: 2500 },
  personas: 3,
} as const;

export const modeDescriptions: Record<UrgePersonaMode, string> = {
  adaptive:
    "For each iteration, select the most suitable persona from your chosen set.",
  consolidated:
    "Combine shared traits once and resolve conflicting traits through evaluation.",
  deliberative:
    "Keep personas distinct. Each proposes a direction before a collective decision.",
};

export const modeLabels: Record<UrgePersonaMode, string> = {
  adaptive: "Adaptive",
  consolidated: "Consolidate",
  deliberative: "Deliberate",
};

export function clampNumber(
  raw: string,
  min: number,
  max: number,
  fallback: number,
): number {
  const value = Number(raw);
  if (!raw.trim() || !Number.isFinite(value)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(value)));
}

export function personaIdentity(
  persona: UrgePersona,
): string {
  return persona.persona_id || "orobouros";
}

export function personaName(
  persona: UrgePersona,
): string {
  return persona.display_name || personaIdentity(persona);
}
