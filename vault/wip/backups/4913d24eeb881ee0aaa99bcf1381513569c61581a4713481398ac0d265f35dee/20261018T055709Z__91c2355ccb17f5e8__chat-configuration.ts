import type {ChatMode} from "./chat-types"
import type {PalaverCapabilities} from "./chat-tool-menu"
export const storageKey =
  "palaver.chat.v3";

export const draftKey =
  "palaver.chat.draft.v2";

export const modeKey =
  "palaver.chat.mode.v2";

export const recentKey =
  "palaver.chat.recent-attachments.v2";

export const recentToolKey =
  "palaver.chat.recent-tools.v1";

export const historyKey =
  "palaver.chat.prompt-history.v1";

export const longPasteThreshold =
  10000;


export const capabilities:
  PalaverCapabilities = {
    createImage: {
      state:
        "unavailable",

      detail:
        "No image-generation backend contract is currently established.",
    },

    plugins: {
      state:
        "unavailable",

      detail:
        "No Palaver plugin execution registry is currently established.",
    },

    web: {
      state:
        "unavailable",

      detail:
        "No Palaver web/research backend contract is currently established.",
    },

    voice: {
      state:
        "unavailable",

      detail:
        "No currently verified voice contract is connected to this surface.",
    },
  };


export const modeLabels:
  Record<
    ChatMode,
    string
  > = {
    standard:
      "standard",

    develop:
      "develop",

    inspect:
      "inspect",

    study:
      "study",

    minimum:
      "minimum",
  };


export const modeInstructions:
  Record<
    ChatMode,
    string
  > = {
    standard:
      "",

    develop:
      (
        "Working mode: develop. "
        + "Optimize for implementation "
        + "and preserve current authority."
      ),

    inspect:
      (
        "Working mode: inspect. "
        + "Distinguish observed facts, "
        + "authority, inference and unknowns."
      ),

    study:
      (
        "Working mode: study. "
        + "Teach interactively, check understanding, "
        + "and progress from fundamentals to depth."
      ),

    minimum:
      (
        "Working mode: minimum. "
        + "Return only the minimum sufficient next action."
      ),
  };
