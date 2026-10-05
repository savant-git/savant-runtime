import type { CinematicEvent, CinematicState } from "../types";

export const initialState: CinematicState = {
  phase: "booting",
  capabilities: null,
  quality: "essential",
  assetsReady: false,
  appReady: false,
  cinematicComplete: false,
  entryRequested: false,
  skipped: false,
  muted: true,
  progress: 0,
  error: null,
};
export const canEnter = (state: CinematicState) =>
  state.appReady && state.cinematicComplete && !state.entryRequested;

const qualityRank: Record<CinematicState["quality"], number> = {
  essential: 0,
  mobile: 1,
  standard: 2,
  ultra: 3,
};

export function cinematicReducer(
  state: CinematicState,
  event: CinematicEvent,
): CinematicState {
  switch (event.type) {
    case "BOOT":
      return { ...initialState, phase: "capabilityCheck" };
    case "CAPABILITIES":
      return {
        ...state,
        capabilities: event.capabilities,
        quality: event.quality,
        phase: "loadingCritical",
      };
    case "ASSETS_READY": {
      const next = { ...state, assetsReady: true };
      return {
        ...next,
        phase: next.phase === "loadingCritical" ? "readyToPlay" : next.phase,
      };
    }
    case "APP_READY": {
      const next = { ...state, appReady: true };
      return {
        ...next,
        phase: next.cinematicComplete ? "awaitingEntry" : next.phase,
      };
    }
    case "PLAY":
      return state.assetsReady ? { ...state, phase: "playing" } : state;
    case "PROGRESS":
      return {
        ...state,
        progress: Math.min(1, Math.max(state.progress, event.progress)),
      };
    case "COMPLETE": {
      const next = { ...state, cinematicComplete: true, progress: 1 };
      return {
        ...next,
        phase: next.appReady ? "awaitingEntry" : "cinematicComplete",
      };
    }
    case "SKIP":
      return { ...state, skipped: true };
    case "ENTER":
      return canEnter(state)
        ? { ...state, entryRequested: true, phase: "transitioning" }
        : state;
    case "ENTERED":
      return state.phase === "transitioning"
        ? { ...state, phase: "entered" }
        : state;
    case "TOGGLE_SOUND":
      return { ...state, muted: !state.muted };
    case "DOWNGRADE_QUALITY":
      return qualityRank[event.quality] < qualityRank[state.quality]
        ? { ...state, quality: event.quality }
        : state;
    case "FAIL":
      return { ...state, phase: "recoverableError", error: event.error };
    case "RETRY":
      return {
        ...initialState,
        appReady: state.appReady,
        phase: "capabilityCheck",
      };
    case "DIRECT_ENTRY":
      return {
        ...state,
        appReady: true,
        cinematicComplete: true,
        entryRequested: true,
        phase: "transitioning",
      };
    default:
      return state;
  }
}
