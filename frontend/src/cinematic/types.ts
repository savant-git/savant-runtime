export type CinematicPhase =
  | "booting"
  | "capabilityCheck"
  | "loadingCritical"
  | "readyToPlay"
  | "playing"
  | "cinematicComplete"
  | "awaitingEntry"
  | "transitioning"
  | "entered"
  | "recoverableError";
export type QualityTier = "ultra" | "standard" | "mobile" | "essential";
export type ActName =
  "signal" | "fracture" | "awakening" | "forge" | "recognition";

export interface Capabilities {
  webgl2: boolean;
  webgpu: boolean;
  reducedMotion: boolean;
  hardwareConcurrency: number;
  deviceMemory: number | null;
  maxTextureSize: number;
  dpr: number;
  touch: boolean;
}

export interface CinematicState {
  phase: CinematicPhase;
  capabilities: Capabilities | null;
  quality: QualityTier;
  assetsReady: boolean;
  appReady: boolean;
  cinematicComplete: boolean;
  entryRequested: boolean;
  skipped: boolean;
  muted: boolean;
  progress: number;
  error: string | null;
}

export type CinematicEvent =
  | { type: "BOOT" }
  | { type: "CAPABILITIES"; capabilities: Capabilities; quality: QualityTier }
  | { type: "ASSETS_READY" }
  | { type: "APP_READY" }
  | { type: "PLAY" }
  | { type: "PROGRESS"; progress: number }
  | { type: "COMPLETE" }
  | { type: "SKIP" }
  | { type: "ENTER" }
  | { type: "ENTERED" }
  | { type: "TOGGLE_SOUND" }
  | { type: "DOWNGRADE_QUALITY"; quality: QualityTier }
  | { type: "FAIL"; error: string }
  | { type: "RETRY" }
  | { type: "DIRECT_ENTRY" };

export interface ShotConfig {
  id: string;
  act: ActName;
  start: number;
  end: number;
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
  impact?: number;
  mobilePosition?: [number, number, number];
  mobileFov?: number;
}
