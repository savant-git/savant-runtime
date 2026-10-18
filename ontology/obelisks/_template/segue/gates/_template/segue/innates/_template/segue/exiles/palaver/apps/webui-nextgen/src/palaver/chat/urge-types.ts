export type UrgePersona = {
  persona_id?: string;
  display_name?: string;
};

export type UrgeRequest = {
  messageId: string;
  iterations: number;
  intervalMs: number;
  personaId: string;
  selection: "final" | "auto";
  preserveLineage: boolean;
};

export type UrgePersonaMode =
  | "adaptive"
  | "consolidated"
  | "deliberative";

export type UrgeExtendedRequest = UrgeRequest & {
  personaIds: string[];
  personaMode: UrgePersonaMode;
};

export type UrgeControlProps = {
  messageId: string;
  personas: UrgePersona[];
  defaultPersonaId: string;
};
