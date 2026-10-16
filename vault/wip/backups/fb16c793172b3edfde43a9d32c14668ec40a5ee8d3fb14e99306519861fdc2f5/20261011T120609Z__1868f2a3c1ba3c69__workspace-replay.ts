import type {
  Density,
  PalaverModule,
  WorkspaceMode,
  WorkspacePreset
} from "./workspace-store"

export type ReplayState = Readonly<{
  active: PalaverModule
  density: Density
  workspaceMode: WorkspaceMode
  workspacePreset: WorkspacePreset
  focusMode: boolean
  leftPanelVisible: boolean
  rightPanelVisible: boolean
  statusbarVisible: boolean
}>

export type ReplayAction =
  | Readonly<{
      type: "activate"
      value: PalaverModule
    }>
  | Readonly<{
      type: "density"
      value: Density
    }>
  | Readonly<{
      type: "mode"
      value: WorkspaceMode
    }>
  | Readonly<{
      type: "preset"
      value: WorkspacePreset
    }>
  | Readonly<{
      type: "visibility"
      target:
        | "leftPanelVisible"
        | "rightPanelVisible"
        | "statusbarVisible"
      value: boolean
    }>
  | Readonly<{
      type: "focus"
      value: boolean
    }>

export type ReplayEntry = Readonly<{
  sequence: number
  action: ReplayAction
}>

export type ReplayJournal = Readonly<{
  initial: ReplayState
  entries: readonly ReplayEntry[]
}>

export function reduceReplay(
  state: ReplayState,
  action: ReplayAction
): ReplayState {
  switch (action.type) {
    case "activate":
      return {
        ...state,
        active: action.value,
        workspaceMode: "single"
      }

    case "density":
      return {
        ...state,
        density: action.value
      }

    case "mode":
      return {
        ...state,
        workspaceMode: action.value
      }

    case "preset":
      return {
        ...state,
        workspacePreset: action.value
      }

    case "visibility":
      return {
        ...state,
        [action.target]: action.value
      }

    case "focus":
      return {
        ...state,
        focusMode: action.value
      }
  }
}

export function appendReplay(
  journal: ReplayJournal,
  action: ReplayAction
): ReplayJournal {
  const last =
    journal.entries[journal.entries.length - 1]

  const sequence =
    last ? last.sequence + 1 : 1

  if (!Number.isSafeInteger(sequence)) {
    throw new RangeError(
      "Replay sequence exhausted"
    )
  }

  return {
    initial: journal.initial,
    entries: [
      ...journal.entries,
      {
        sequence,
        action
      }
    ]
  }
}

export function replayWorkspace(
  journal: ReplayJournal
): ReplayState {
  let state = { ...journal.initial }
  let previous = 0

  for (const entry of journal.entries) {
    if (
      !Number.isSafeInteger(entry.sequence)
      || entry.sequence <= previous
    ) {
      throw new Error(
        "Invalid replay sequence"
      )
    }

    previous = entry.sequence
    state = reduceReplay(state, entry.action)
  }

  return state
}
